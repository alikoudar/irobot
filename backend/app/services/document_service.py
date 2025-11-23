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
    DocumentListResponse
)
from app.utils.file_upload import (
    validate_and_prepare_file,
    save_uploaded_file,
    delete_file,
    UPLOAD_MAX_SIZE
)
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
    def retry_document(
        db: Session,
        document_id: UUID,
        current_user: User,
        from_stage: Optional[str] = None
    ) -> Document:
        """
        Relancer le traitement d'un document.
        
        Args:
            db: Session database
            document_id: ID du document
            current_user: Utilisateur courant
            from_stage: Stage depuis lequel recommencer (optionnel)
            
        Returns:
            Document mis à jour
        """
        document = DocumentService.get_document_by_id(db, document_id, current_user)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        # Vérifier que le document est en échec
        if document.status != DocumentStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail="Seuls les documents en échec peuvent être relancés"
            )
        
        # Limite de retry
        if document.retry_count >= 3:
            raise HTTPException(
                status_code=400,
                detail="Nombre maximum de tentatives atteint (3)"
            )
        
        # Réinitialiser le status
        document.status = DocumentStatus.PENDING
        document.processing_stage = ProcessingStage.VALIDATION
        document.error_message = None
        document.retry_count += 1
        
        # NOUVEAU : Réinitialiser les métadonnées d'extraction
        document.document_metadata = {}
        
        db.commit()
        db.refresh(document)
        
        # Relancer le traitement
        extract_document_text.apply_async(
            args=[str(document.id)],
            queue="processing"
        )
        
        logger.info(f"Retrying document {document.id} (attempt {document.retry_count})")
        
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
        # NOUVEAU : Filtres extraction hybride
        has_images: Optional[bool] = None,
        extraction_method: Optional[str] = None
    ) -> DocumentListResponse:
        """
        Lister les documents avec filtres et pagination.
        
        Args:
            db: Session database
            current_user: Utilisateur courant
            page: Numéro de page
            limit: Nombre de résultats par page
            category_id: Filtrer par catégorie
            status: Filtrer par status
            uploaded_by: Filtrer par uploadeur
            search: Recherche textuelle
            sort_by: Champ de tri
            sort_order: Ordre de tri (asc/desc)
            has_images: NOUVEAU - Filtrer par présence d'images OCR
            extraction_method: NOUVEAU - Filtrer par méthode d'extraction
            
        Returns:
            DocumentListResponse avec items et pagination
        """
        query = db.query(Document)
        
        # Les managers ne voient que leurs documents
        if current_user.role == "manager":
            query = query.filter(Document.uploaded_by == current_user.id)
        
        # Filtres standard
        if category_id:
            query = query.filter(Document.category_id == category_id)
        
        if status:
            try:
                status_enum = DocumentStatus(status)
                query = query.filter(Document.status == status_enum)
            except ValueError:
                pass
        
        if uploaded_by:
            query = query.filter(Document.uploaded_by == uploaded_by)
        
        if search:
            query = query.filter(Document.original_filename.ilike(f"%{search}%"))
        
        # NOUVEAU : Filtres extraction hybride (JSON)
        if has_images is not None:
            query = query.filter(
                Document.document_metadata['has_images'].astext.cast(db.bind.dialect.type_compiler.process(db.bind.dialect.type_descriptor(type(has_images)))) == str(has_images).lower()
            )
        
        if extraction_method:
            query = query.filter(
                Document.document_metadata['extraction_method'].astext == extraction_method
            )
        
        # Compter le total
        total = query.count()
        
        # Tri
        sort_column = getattr(Document, sort_by, Document.uploaded_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()
        
        # Calculer le nombre de pages
        pages = (total + limit - 1) // limit
        
        return DocumentListResponse(
            items=items,
            total=total,
            page=page,
            pages=pages
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