"""
Service de gestion des documents (VERSION AMÉLIORÉE - Extraction Hybride).

Gère l'upload, le traitement et la gestion du cycle de vie des documents.
Inclut les nouvelles métadonnées d'extraction hybride (OCR images).
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.document import Document, DocumentStatus, ProcessingStage
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentListItem
)
from app.utils.file_upload import (
    validate_and_prepare_file,
    save_uploaded_file,
    delete_file,
    UPLOAD_MAX_SIZE
)

from app.models.audit_log import AuditLog
from app.workers.processing_tasks import extract_document_text

logger = logging.getLogger(__name__)


class DocumentService:
    """Service de gestion des documents."""
    
    @staticmethod
    async def upload_documents(
        db: Session,
        files: List[UploadFile],
        category_id: UUID,
        current_user: User,
        max_files: int = 10
    ) -> Dict[str, Any]:
        """
        Uploader plusieurs documents.
        
        Args:
            db: Session database
            files: Liste des fichiers uploadés
            category_id: ID de la catégorie
            current_user: Utilisateur courant
            max_files: Nombre maximum de fichiers
            
        Returns:
            Dict avec documents créés et erreurs éventuelles
        """
        # Valider nombre de fichiers
        if len(files) > max_files:
            raise HTTPException(
                status_code=400,
                detail=f"Nombre maximum de fichiers dépassé: {len(files)} > {max_files}"
            )
        
        uploaded_documents = []
        errors = []
        
        for file in files:
            try:
                # Valider et préparer le fichier
                file_meta = await validate_and_prepare_file(file)
                
                # Vérifier si le fichier existe déjà (par hash)
                existing_doc = db.query(Document).filter(
                    Document.file_hash == file_meta["file_hash"]
                ).first()
                
                if existing_doc:
                    errors.append({
                        "filename": file.filename,
                        "error": "Ce fichier existe déjà dans le système",
                        "existing_document_id": str(existing_doc.id)
                    })
                    continue
                
                # Sauvegarder le fichier
                original_filename, file_path = await save_uploaded_file(file)
                
                # Créer l'enregistrement en base
                document = Document(
                    original_filename=file_meta["original_filename"],
                    file_hash=file_meta["file_hash"],
                    file_extension=file_meta["file_extension"],
                    file_size_bytes=file_meta["file_size_bytes"],
                    file_path=file_path,
                    mime_type=file_meta["mime_type"],
                    category_id=category_id,
                    uploaded_by=current_user.id,
                    status=DocumentStatus.PENDING,
                    processing_stage=ProcessingStage.VALIDATION,
                    # Initialiser les métadonnées vides (seront remplies par le worker)
                    document_metadata={}
                )
                
                db.add(document)
                db.flush()  # Pour obtenir l'ID
                
                # Lancer le traitement asynchrone
                extract_document_text.apply_async(
                    args=[str(document.id)],
                    queue="processing"
                )
                
                uploaded_documents.append(document)
                
                logger.info(
                    f"Document uploaded: {file.filename} "
                    f"(ID: {document.id}, Hash: {file_meta['file_hash'][:16]}...)"
                )
                
            except HTTPException as e:
                errors.append({
                    "filename": file.filename,
                    "error": e.detail
                })
                logger.warning(f"Upload failed for {file.filename}: {e.detail}")
                
            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": f"Erreur interne: {str(e)}"
                })
                logger.error(f"Upload error for {file.filename}: {e}", exc_info=True)
        
        # Commit si au moins un document uploadé
        if uploaded_documents:
            db.commit()
            for doc in uploaded_documents:
                db.refresh(doc)

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="DOCUMENT_CREATED",
                    entity_type="DOCUMENT",
                    entity_id=doc.id,
                    details={
                        "filename": doc.original_filename,
                        "file_size": doc.file_size_bytes,
                        "file_type": doc.file_extension,
                        "category_id": str(category_id),
                        "status": str(doc.status.value) if hasattr(doc.status, 'value') else str(doc.status)
                    }
                )
                db.add(audit_log)
            
            # Commit des audit logs
            db.commit()
        
        return {
            "uploaded": len(uploaded_documents),
            "documents": uploaded_documents,
            "errors": errors
        }
    
    @staticmethod
    def get_document_by_id(
        db: Session,
        document_id: UUID,
        current_user: User
    ) -> Optional[Document]:
        """
        Récupérer un document par ID.
        
        Args:
            db: Session database
            document_id: ID du document
            current_user: Utilisateur courant
            
        Returns:
            Document ou None
        """
        query = db.query(Document).filter(Document.id == document_id)
        
        # Les managers ne voient que leurs documents
        if current_user.role == "manager":
            query = query.filter(Document.uploaded_by == current_user.id)
        
        return query.first()
    
    @staticmethod
    def get_document_status(
        db: Session,
        document_id: UUID,
        current_user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Obtenir le status d'un document avec infos d'extraction hybride.
        
        Args:
            db: Session database
            document_id: ID du document
            current_user: Utilisateur courant
            
        Returns:
            Dict avec status du document et métadonnées d'extraction
        """
        document = DocumentService.get_document_by_id(db, document_id, current_user)
        
        if not document:
            return None
        
        # Calculer le progrès (0-100)
        stage_progress = {
            ProcessingStage.VALIDATION: 10,
            ProcessingStage.EXTRACTION: 30,
            ProcessingStage.CHUNKING: 50,
            ProcessingStage.EMBEDDING: 70,
            ProcessingStage.INDEXING: 90
        }
        
        progress = stage_progress.get(document.processing_stage, 0)
        
        if document.status == DocumentStatus.COMPLETED:
            progress = 100
        elif document.status == DocumentStatus.FAILED:
            progress = 0
        
        # NOUVEAU : Récupérer les infos d'extraction hybride
        metadata = document.document_metadata or {}
        extraction_method = metadata.get('extraction_method', 'unknown')
        total_images_ocr = metadata.get('total_images_ocr', 0)
        has_images = metadata.get('has_images', False)
        chunking_stats = metadata.get('chunking_stats', {})
        
        return {
            "id": document.id,
            "status": document.status.value,
            "processing_stage": document.processing_stage.value,
            "progress": progress,
            "error_message": document.error_message,
            "retry_count": document.retry_count,
            "total_pages": document.total_pages,
            "total_chunks": document.total_chunks,
            "uploaded_at": document.uploaded_at,
            "processed_at": document.processed_at,
            # NOUVEAU : Infos extraction hybride
            "extraction_method": extraction_method,
            "total_images_ocr": total_images_ocr,
            "has_images": has_images,
            "chunking_stats": chunking_stats
        }
    
    @staticmethod
    def get_document_details(
        db: Session,
        document_id: UUID,
        current_user: User
    ) -> Optional[Dict[str, Any]]:
        """
        NOUVEAU : Obtenir les détails complets d'un document.
        
        Inclut toutes les métadonnées d'extraction et de chunking.
        
        Args:
            db: Session database
            document_id: ID du document
            current_user: Utilisateur courant
            
        Returns:
            Dict avec tous les détails du document
        """
        document = DocumentService.get_document_by_id(db, document_id, current_user)
        
        if not document:
            return None
        
        metadata = document.document_metadata or {}
        
        return {
            # Infos de base
            "id": document.id,
            "original_filename": document.original_filename,
            "file_extension": document.file_extension,
            "file_size_bytes": document.file_size_bytes,
            "file_hash": document.file_hash,
            "mime_type": document.mime_type,
            "category_id": document.category_id,
            "uploaded_by": document.uploaded_by,
            
            # Status
            "status": document.status.value,
            "processing_stage": document.processing_stage.value,
            "error_message": document.error_message,
            "retry_count": document.retry_count,
            
            # Métriques d'extraction
            "total_pages": document.total_pages,
            "extracted_text_length": document.extracted_text_length,
            "extraction_time_seconds": metadata.get('extraction_time_seconds'),
            
            # NOUVEAU : Infos extraction hybride
            "extraction_method": metadata.get('extraction_method', 'unknown'),
            "total_images_ocr": metadata.get('total_images_ocr', 0),
            "has_images": metadata.get('has_images', False),
            
            # Métriques de chunking
            "total_chunks": document.total_chunks,
            "chunking_stats": metadata.get('chunking_stats', {}),
            
            # Timestamps
            "uploaded_at": document.uploaded_at,
            "processed_at": document.processed_at
        }
    
    @staticmethod
    async def retry_document(
        db: Session,
        document_id: UUID,
        from_stage: str,
        current_user: User
    ) -> Document:
        """
        Relancer le traitement d'un document en erreur.
        
        MODIFICATION: Le retry manuel remet TOUJOURS retry_count à 0
        car c'est une action volontaire de l'utilisateur après correction
        du problème sous-jacent.
        
        Args:
            db: Session database
            document_id: ID du document
            from_stage: Étape à partir de laquelle relancer
            current_user: Utilisateur courant
            
        Returns:
            Document mis à jour
        """
        from app.models.document import Document, DocumentStatus, ProcessingStage
        from app.models.audit_log import AuditLog
        
        # Récupérer le document
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        # Vérifier que le document est en erreur
        if document.status != DocumentStatus.FAILED:
            raise HTTPException(
                status_code=400, 
                detail=f"Le document n'est pas en erreur (status: {document.status})"
            )
        
        # =================================================================
        # CORRECTION : Réinitialiser le compteur de retry
        # Le retry manuel est une action volontaire après correction du problème
        # =================================================================
        document.retry_count = 0  # ← LIGNE AJOUTÉE
        document.status = DocumentStatus.PENDING
        document.processing_stage = ProcessingStage(from_stage)
        document.error_message = None
        
        db.commit()
        db.refresh(document)
        
        # Créer l'audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="RETRY",
            entity_type="DOCUMENT",
            entity_id=document.id,
            details={
                "filename": document.original_filename,
                "from_stage": from_stage,
                "retry_count_reset": True  # ← Indique que le compteur a été remis à 0
            }
        )
        db.add(audit_log)
        db.commit()
        
        # Lancer la tâche appropriée selon l'étape
        if from_stage == "VALIDATION" or from_stage == "EXTRACTION":
            from app.workers.processing_tasks import extract_document_text
            extract_document_text.delay(str(document.id))
        elif from_stage == "CHUNKING":
            from app.workers.chunking_tasks import chunk_document
            chunk_document.delay(str(document.id))
        elif from_stage == "EMBEDDING":
            from app.workers.embedding_tasks import embed_chunks
            embed_chunks.delay(str(document.id))
        elif from_stage == "INDEXING":
            from app.workers.indexing_tasks import index_to_weaviate
            index_to_weaviate.delay(str(document.id))
        
        return document
    
    @staticmethod
    def list_documents(
        db: Session,
        current_user: User,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[UUID] = None,
        status: Optional[str] = None,
        uploaded_by: Optional[UUID] = None,
        search: Optional[str] = None,
        sort_by: str = "uploaded_at",
        sort_order: str = "desc",
        has_images: Optional[bool] = None,
        extraction_method: Optional[str] = None,
        file_types: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> DocumentListResponse:
        """
        Lister les documents avec filtres et pagination.
        
        MODIFICATION: Retourne DocumentListItem avec informations enrichies
        (nom uploader, coûts, temps de traitement).
        """
        from app.models.document import Document, DocumentStatus
        from app.models.user import User as UserModel
        from app.models.category import Category
        
        # Construction de la requête de base avec jointure pour l'uploader
        query = db.query(Document)
        
        # Filtrage par rôle
        if current_user.role.value != "ADMIN":
            # Manager ne voit que ses propres documents
            query = query.filter(Document.uploaded_by == current_user.id)
        elif uploaded_by:
            # Admin peut filtrer par uploader
            query = query.filter(Document.uploaded_by == uploaded_by)
        
        # Filtre par catégorie
        if category_id:
            query = query.filter(Document.category_id == category_id)
        
        # Filtre par status
        if status:
            try:
                status_enum = DocumentStatus(status.upper())
                query = query.filter(Document.status == status_enum)
            except ValueError:
                pass
        
        # Recherche dans le nom de fichier
        if search:
            query = query.filter(
                Document.original_filename.ilike(f"%{search}%")
            )
        
            # =========================================================================
        # NOUVEAU : Filtre par types de fichiers
        # =========================================================================
        if file_types:
            types_list = [t.strip().lower() for t in file_types.split(',')]
            
            # Mapper les types génériques vers les extensions réelles
            extensions = []
            for t in types_list:
                if t == 'image':
                    extensions.extend(['png', 'jpg', 'jpeg', 'webp', 'gif'])
                elif t == 'txt':
                    extensions.extend(['txt', 'md', 'rtf'])
                elif t == 'doc':
                    extensions.extend(['doc', 'docx'])
                elif t == 'xls':
                    extensions.extend(['xls', 'xlsx'])
                elif t == 'ppt':
                    extensions.extend(['ppt', 'pptx'])
                else:
                    extensions.append(t)
            
            if extensions:
                query = query.filter(Document.file_extension.in_(extensions))
        
        # =========================================================================
        # NOUVEAU : Filtre par plage de dates
        # =========================================================================
        if date_from:
            try:
                from datetime import datetime
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Document.uploaded_at >= start_date)
            except ValueError:
                pass  # Ignorer si format invalide
        
        if date_to:
            try:
                from datetime import datetime, timedelta
                # Ajouter 1 jour pour inclure toute la journée de fin
                end_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(Document.uploaded_at < end_date)
            except ValueError:
                pass  # Ignorer si format invalide
        

        # Compter le total avant pagination
        total = query.count()
        
        # Tri
        sort_column = getattr(Document, sort_by, Document.uploaded_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * limit
        documents = query.offset(offset).limit(limit).all()
        
        # Construire les items enrichis
        items = []
        for doc in documents:
            # Récupérer l'uploader
            uploader = db.query(UserModel).filter(UserModel.id == doc.uploaded_by).first()
            uploader_name = None
            uploader_matricule = None
            if uploader:
                uploader_name = f"{uploader.prenom} {uploader.nom}".strip()
                uploader_matricule = uploader.matricule
            
            # Récupérer la catégorie
            category_name = None
            if doc.category_id:
                category = db.query(Category).filter(Category.id == doc.category_id).first()
                if category:
                    category_name = category.name
            
            # Calculer les coûts depuis les métadonnées
            total_cost_usd = 0.0
            total_cost_xaf = 0.0
            total_tokens = 0
            
            if doc.document_metadata:
                meta = doc.document_metadata
                
                # Coût OCR
                if meta.get("ocr_stats"):
                    total_cost_usd += meta["ocr_stats"].get("cost_usd", 0) or 0
                    total_cost_xaf += meta["ocr_stats"].get("cost_xaf", 0) or 0
                
                # Coût embedding
                if meta.get("embedding_stats"):
                    total_cost_usd += meta["embedding_stats"].get("cost_usd", 0) or 0
                    total_cost_xaf += meta["embedding_stats"].get("cost_xaf", 0) or 0
                    total_tokens += meta["embedding_stats"].get("total_tokens", 0) or 0
            
            # Calculer le temps total de traitement
            total_processing_time = 0.0
            if doc.extraction_time_seconds:
                total_processing_time += doc.extraction_time_seconds
            if doc.chunking_time_seconds:
                total_processing_time += doc.chunking_time_seconds
            if doc.embedding_time_seconds:
                total_processing_time += doc.embedding_time_seconds
            
            # Temps d'indexation depuis les métadonnées
            indexing_time = None
            if doc.document_metadata and doc.document_metadata.get("indexing_stats"):
                indexing_time = doc.document_metadata["indexing_stats"].get("indexing_time_seconds")
                if indexing_time:
                    total_processing_time += indexing_time
            
            # Créer l'item enrichi
            item = DocumentListItem(
                id=doc.id,
                original_filename=doc.original_filename,
                file_extension=doc.file_extension,
                file_size_bytes=doc.file_size_bytes,
                file_hash=doc.file_hash,
                mime_type=doc.mime_type,
                status=doc.status.value,
                processing_stage=doc.processing_stage.value if doc.processing_stage else None,
                error_message=doc.error_message,
                retry_count=doc.retry_count or 0,
                total_pages=doc.total_pages,
                total_chunks=doc.total_chunks or 0,
                category_id=doc.category_id,
                category_name=category_name,
                uploaded_by=doc.uploaded_by,
                uploader_name=uploader_name,
                uploader_matricule=uploader_matricule,
                uploaded_at=doc.uploaded_at,
                processed_at=doc.processed_at,
                extraction_time_seconds=doc.extraction_time_seconds,
                chunking_time_seconds=doc.chunking_time_seconds,
                embedding_time_seconds=doc.embedding_time_seconds,
                indexing_time_seconds=indexing_time,
                total_processing_time_seconds=total_processing_time if total_processing_time > 0 else None,
                total_cost_usd=total_cost_usd if total_cost_usd > 0 else None,
                total_cost_xaf=total_cost_xaf if total_cost_xaf > 0 else None,
                total_tokens=total_tokens if total_tokens > 0 else None
            )
            items.append(item)
        
        # Calculer le nombre de pages
        total_pages = (total + limit - 1) // limit
        
        return DocumentListResponse(
            items=items,
            total=total,
            page=page,
            pages=total_pages
        )
    
    @staticmethod
    def get_documents_stats(
        db: Session,
        current_user: User,
        category_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        NOUVEAU : Obtenir les statistiques des documents.
        
        Inclut les stats d'extraction hybride.
        
        Args:
            db: Session database
            current_user: Utilisateur courant
            category_id: Filtrer par catégorie (optionnel)
            
        Returns:
            Dict avec statistiques
        """
        query = db.query(Document)
        
        # Les managers ne voient que leurs documents
        if current_user.role == "manager":
            query = query.filter(Document.uploaded_by == current_user.id)
        
        if category_id:
            query = query.filter(Document.category_id == category_id)
        
        documents = query.all()
        
        # Calculer les stats
        total_documents = len(documents)
        total_pages = sum(doc.total_pages or 0 for doc in documents)
        total_chunks = sum(doc.total_chunks or 0 for doc in documents)
        total_size_bytes = sum(doc.file_size_bytes or 0 for doc in documents)
        
        # Stats par status
        status_counts = {}
        for status in DocumentStatus:
            count = sum(1 for doc in documents if doc.status == status)
            status_counts[status.value] = count
        
        # NOUVEAU : Stats extraction hybride
        extraction_methods = {"TEXT": 0, "OCR": 0, "HYBRID": 0, "UNKNOWN": 0}
        total_images_ocr = 0
        documents_with_images = 0
        
        for doc in documents:
            metadata = doc.document_metadata or {}
            method = metadata.get('extraction_method', 'unknown')
            if method in extraction_methods:
                extraction_methods[method] += 1
            else:
                extraction_methods['unknown'] += 1
            
            images = metadata.get('total_images_ocr', 0)
            total_images_ocr += images
            
            if metadata.get('has_images', False):
                documents_with_images += 1
        
        return {
            "total_documents": total_documents,
            "total_pages": total_pages,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "status_counts": status_counts,
            # NOUVEAU : Stats extraction hybride
            "extraction_methods": extraction_methods,
            "total_images_ocr": total_images_ocr,
            "documents_with_images": documents_with_images,
            "ocr_coverage_percent": round(
                (documents_with_images / total_documents * 100) if total_documents > 0 else 0, 1
            )
        }
    
    @staticmethod
    def delete_document(
        db: Session,
        document_id: UUID,
        current_user: User
    ) -> bool:
        """
        Supprimer un document (hard delete uniquement).
        
        Args:
            db: Session database
            document_id: ID du document
            current_user: Utilisateur courant
            
        Returns:
            True si supprimé
        """
        document = DocumentService.get_document_by_id(db, document_id, current_user)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        # Suppression physique du fichier
        if document.file_path:
            delete_file(document.file_path)
        
        # Suppression de la base
        db.delete(document)
        db.commit()
        
        logger.info(f"Deleted document {document.id}")
        
        # TODO: Invalider le cache Redis si nécessaire
        # TODO: Supprimer les chunks de Weaviate
        
        return True