"""
Endpoints API pour la gestion des documents.

Permet l'upload, le suivi et la gestion des documents.
"""
import logging
from typing import List, Optional
from uuid import UUID
import asyncio
import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    status
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin, require_admin_or_manager
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentUploadItem,
    DocumentStatusResponse,
    DocumentListResponse,
    DocumentRetryRequest,
    DocumentRetryResponse,
    DocumentDeleteResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


# ============================================================================
# UPLOAD
# ============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(..., description="Fichiers à uploader (max 10)"),
    category_id: UUID = Form(..., description="ID de la catégorie"),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Uploader un ou plusieurs documents.
    
    **Permissions**: Admin, Manager
    
    **Limites**:
    - Maximum 10 fichiers simultanément
    - Taille maximale par fichier: 50 MB
    - Types autorisés: PDF, DOCX, XLSX, PPTX, Images, TXT, MD, RTF
    
    **Processus**:
    1. Validation (type, taille, hash)
    2. Sauvegarde sur disque
    3. Création DB (status=PENDING)
    4. Envoi à la queue de traitement Celery
    5. Retour immédiat des IDs
    
    Le traitement se fait en asynchrone:
    - PENDING → PROCESSING → COMPLETED
    - Utiliser GET /documents/{id}/status pour suivre la progression
    """
    result = await DocumentService.upload_documents(
        db=db,
        files=files,
        category_id=category_id,
        current_user=current_user
    )
    
    # Transformer les documents en réponse
    document_items = [
        DocumentUploadItem(
            id=doc.id,
            original_filename=doc.original_filename,
            status=doc.status.value,
            message="En attente de traitement"
        )
        for doc in result["documents"]
    ]
    
    return DocumentUploadResponse(
        uploaded=result["uploaded"],
        documents=document_items,
        errors=result["errors"]
    )


# ============================================================================
# STATUS (SSE STREAMING)
# ============================================================================

@router.get("/{document_id}/status")
async def get_document_status_stream(
    document_id: UUID,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Obtenir le status d'un document en temps réel (SSE).
    
    **Permissions**: Admin, Manager (own documents only)
    
    **Format SSE**:
    ```
    event: status
    data: {"status": "processing", "stage": "extraction", "progress": 30}
    
    event: complete
    data: {"status": "completed", "progress": 100}
    
    event: error
    data: {"status": "failed", "error": "OCR failed"}
    ```
    
    **Usage frontend**:
    ```javascript
    const eventSource = new EventSource('/api/v1/documents/{id}/status');
    eventSource.addEventListener('status', (e) => {
        const data = JSON.parse(e.data);
        console.log(data.status, data.progress);
    });
    ```
    """
    async def event_generator():
        """Générateur d'événements SSE."""
        previous_status = None
        
        while True:
            # Récupérer le status actuel
            status_data = DocumentService.get_document_status(
                db=db,
                document_id=document_id,
                current_user=current_user
            )
            
            if not status_data:
                yield f"event: error\ndata: {json.dumps({'error': 'Document non trouvé'})}\n\n"
                break
            
            # FIXED: Convertir UUID et datetime en types JSON serializable
            status_data_serializable = {
                "id": str(status_data["id"]),
                "status": status_data["status"],
                "processing_stage": status_data["processing_stage"],
                "progress": status_data["progress"],
                "error_message": status_data["error_message"],
                "retry_count": status_data["retry_count"],
                "total_pages": status_data["total_pages"],
                "total_chunks": status_data["total_chunks"],
                "uploaded_at": status_data["uploaded_at"].isoformat() if status_data["uploaded_at"] else None,
                "processed_at": status_data["processed_at"].isoformat() if status_data["processed_at"] else None
            }
            
            # Envoyer seulement si changement
            current_status = (status_data["status"], status_data["processing_stage"])
            if current_status != previous_status:
                yield f"event: status\ndata: {json.dumps(status_data_serializable)}\n\n"
                previous_status = current_status
            
            # Si terminé ou échoué, arrêter le stream
            if status_data["status"] in ["completed", "failed"]:
                event_type = "complete" if status_data["status"] == "completed" else "error"
                yield f"event: {event_type}\ndata: {json.dumps(status_data_serializable)}\n\n"
                break
            
            # Attendre avant le prochain check
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Nginx buffering
        }
    )


@router.get("/{document_id}/status/simple", response_model=DocumentStatusResponse)
async def get_document_status_simple(
    document_id: UUID,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Obtenir le status d'un document (simple, sans streaming).
    
    **Permissions**: Admin, Manager (own documents only)
    
    Alternative à l'endpoint SSE pour un simple GET.
    """
    status_data = DocumentService.get_document_status(
        db=db,
        document_id=document_id,
        current_user=current_user
    )
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé"
        )
    
    return DocumentStatusResponse(**status_data)


# ============================================================================
# RETRY
# ============================================================================

@router.post("/{document_id}/retry", response_model=DocumentRetryResponse)
async def retry_document(
    document_id: UUID,
    retry_request: DocumentRetryRequest = None,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Relancer le traitement d'un document en échec.
    
    **Permissions**: Admin, Manager (own documents only)
    
    **Conditions**:
    - Document doit être en status FAILED
    - Maximum 3 tentatives de retry
    
    **Comportement**:
    1. Réinitialise le status à PENDING
    2. Incrémente retry_count
    3. Relance le traitement via Celery
    """
    document = await DocumentService.retry_document(
        db=db,
        document_id=document_id,
        current_user=current_user,
        from_stage=retry_request.from_stage if retry_request else None
    )
    
    return DocumentRetryResponse(
        id=document.id,
        status=document.status.value,
        message=f"Document en attente de retraitement (tentative {document.retry_count}/3)",
        retry_count=document.retry_count
    )


# ============================================================================
# LIST
# ============================================================================

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Résultats par page"),
    category_id: Optional[UUID] = Query(None, description="Filtrer par catégorie"),
    status: Optional[str] = Query(None, description="Filtrer par status (pending, processing, completed, failed)"),
    uploaded_by: Optional[UUID] = Query(None, description="Filtrer par uploadeur (admin only)"),
    search: Optional[str] = Query(None, description="Rechercher dans les noms de fichiers"),
    sort_by: str = Query("uploaded_at", description="Champ de tri"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Ordre de tri"),
    file_types: Optional[str] = Query(None, description="Types de fichiers (séparés par virgule: pdf,docx,xlsx)"),
    date_from: Optional[str] = Query(None, description="Date début (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date fin (YYYY-MM-DD)"),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Lister les documents avec filtres et pagination.
    
    **Permissions**: 
    - Admin: Tous les documents
    - Manager: Uniquement ses documents
    
    **Filtres disponibles**:
    - `category_id`: Filtrer par catégorie
    - `status`: pending, processing, completed, failed
    - `uploaded_by`: Uploadeur (admin only)
    - `search`: Recherche textuelle dans noms de fichiers
    
    **Tri**:
    - `sort_by`: uploaded_at, original_filename, file_size, status
    - `sort_order`: asc, desc
    
    **Pagination**:
    - `page`: Numéro de page (1+)
    - `limit`: Résultats par page (1-100)
    """
    # Vérifier permission pour uploaded_by filter
    if uploaded_by and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les administrateurs peuvent filtrer par uploadeur"
        )
    
    return DocumentService.list_documents(
        db=db,
        current_user=current_user,
        page=page,
        limit=limit,
        category_id=category_id,
        status=status,
        uploaded_by=uploaded_by,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        file_types=file_types,      # NOUVEAU
        date_from=date_from,        # NOUVEAU
        date_to=date_to 
    )


# ============================================================================
# DELETE
# ============================================================================

@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Supprimer un document (hard delete uniquement).
    
    **Permissions**: Admin, Manager (own documents only)
    
    **Comportement**:
    - Suppression de la base de données
    - Suppression du fichier sur disque
    - Suppression définitive (pas de soft delete)
    - Cache Redis invalidé
    """
    DocumentService.delete_document(
        db=db,
        document_id=document_id,
        current_user=current_user
    )
    
    return DocumentDeleteResponse(
        id=document_id,
        message="Document supprimé avec succès"
    )