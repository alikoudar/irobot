"""
Chunking worker tasks avec nettoyage et restructuration du texte.

CORRECTIONS :
- Génération de weaviate_id (UUID) pour satisfaire contrainte NOT NULL
- Nettoyage des artefacts OCR avant chunking
- Préservation de la structure (tableaux, listes)
- Métadonnées enrichies par chunk
"""
import logging
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from celery import Task

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus, ProcessingStage
from app.models.chunk import Chunk
from app.rag.text_cleaner import (
    clean_extracted_text,
    prepare_text_for_chunking,
    detect_document_language,
    extract_document_title
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CHUNKING
# =============================================================================

CHUNK_SIZE = 1000          # Taille cible en caractères
CHUNK_OVERLAP = 200        # Chevauchement entre chunks
MIN_CHUNK_SIZE = 100       # Taille minimum d'un chunk
MAX_CHUNK_SIZE = 2000      # Taille maximum d'un chunk


# =============================================================================
# TASK BASE CLASS
# =============================================================================

class ChunkingTask(Task):
    """Base task for chunking operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Chunking task {task_id} failed: {exc}")
        document_id = args[0] if args else kwargs.get('document_id')
        if document_id:
            db = SessionLocal()
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = DocumentStatus.FAILED
                    document.processing_stage = ProcessingStage.CHUNKING
                    document.error_message = str(exc)[:1000]
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to update document status: {e}")
                db.rollback()
            finally:
                db.close()


# =============================================================================
# MAIN CHUNKING TASK
# =============================================================================

@celery_app.task(
    base=ChunkingTask,
    bind=True,
    name="app.workers.chunking_tasks.chunk_document",
    max_retries=3,
    default_retry_delay=30
)
def chunk_document(self, document_id: str) -> Dict[str, Any]:
    """
    Découper un document en chunks avec nettoyage et enrichissement.
    
    Étapes :
    1. Récupérer le texte extrait
    2. NETTOYER les artefacts OCR
    3. Découper en chunks intelligents
    4. Enrichir les métadonnées
    5. Sauvegarder les chunks
    
    Args:
        document_id: UUID du document
        
    Returns:
        Dict avec statistiques de chunking
    """
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        # 1. Charger le document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        logger.info(f"Starting chunking for document {document_id}: {document.original_filename}")
        
        # Mettre à jour le statut
        document.status = DocumentStatus.PROCESSING
        document.processing_stage = ProcessingStage.CHUNKING
        db.commit()
        
        # 2. Récupérer le texte extrait
        metadata = document.document_metadata or {}
        raw_text = metadata.get('extracted_text', '')
        
        if not raw_text:
            raise ValueError("No extracted text found in document metadata")
        
        # 3. NETTOYER LE TEXTE (artefacts OCR, caractères problématiques)
        cleaned_text = prepare_text_for_chunking(raw_text, deduplicate=True)
        
        logger.info(
            f"Text cleaned: {len(raw_text)} -> {len(cleaned_text)} chars "
            f"({len(raw_text) - len(cleaned_text)} chars removed)"
        )
        
        # 4. Extraire métadonnées globales
        document_language = detect_document_language(cleaned_text)
        document_title = extract_document_title(cleaned_text)
        extraction_method = metadata.get('extraction_method', 'TEXT')
        has_images = metadata.get('has_images', False)
        total_images_ocr = metadata.get('total_images_ocr', 0)
        
        # 5. Découper en chunks
        chunks_data = create_smart_chunks(
            text=cleaned_text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )
        
        # 6. Supprimer les anciens chunks s'ils existent
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        db.flush()
        
        # 7. Créer les objets Chunk avec métadonnées enrichies
        created_chunks = []
        chunks_with_ocr = 0
        
        for idx, chunk_data in enumerate(chunks_data):
            chunk_text = chunk_data['text']
            
            # Détecter si le chunk contient du contenu OCR
            has_ocr_content = bool(re.search(r'\[Image \d+\]|=== Page', chunk_text))
            if has_ocr_content:
                chunks_with_ocr += 1
            
            # Détecter si le chunk contient un tableau
            has_table = bool(re.search(r'\|[^\n]+\|', chunk_text))
            
            # Métadonnées enrichies du chunk
            chunk_metadata = {
                # Infos document
                'document_id': str(document.id),
                'document_filename': document.original_filename,
                'document_type': document.file_extension,
                'document_language': document_language,
                'document_title': document_title,
                
                # Infos extraction
                'extraction_method': extraction_method,
                'has_ocr_content': has_ocr_content,
                'total_images_in_doc': total_images_ocr,
                
                # Infos chunk
                'chunk_index': idx,
                'chunk_total': len(chunks_data),
                'has_table': has_table,
                'page_hint': chunk_data.get('page_hint'),
                
                # Position
                'char_start': chunk_data.get('char_start', 0),
                'char_end': chunk_data.get('char_end', 0),
            }
            
            # CORRECTION : Générer un weaviate_id temporaire (sera mis à jour lors de l'indexation)
            # Le weaviate_id réel sera assigné lors de l'étape INDEXING dans Weaviate
            temp_weaviate_id = str(uuid.uuid4())
            
            # Créer l'objet Chunk
            chunk = Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                weaviate_id=temp_weaviate_id,  # CORRECTION: UUID temporaire
                content=chunk_text,
                chunk_index=idx,
                token_count=estimate_tokens(chunk_text),
                char_count=len(chunk_text),
                page_number=chunk_data.get('page_number'),
                start_char=chunk_data.get('char_start'),
                end_char=chunk_data.get('char_end'),
                chunk_metadata=chunk_metadata
            )
            
            db.add(chunk)
            created_chunks.append(chunk)
        
        # 8. Mettre à jour le document
        chunking_time = (datetime.utcnow() - start_time).total_seconds()
        
        document.total_chunks = len(created_chunks)
        document.chunking_time_seconds = chunking_time
        document.processing_stage = ProcessingStage.CHUNKING
        
        # Mettre à jour les métadonnées
        document.document_metadata['chunking_stats'] = {
            'total_chunks': len(created_chunks),
            'chunks_with_ocr': chunks_with_ocr,
            'avg_chunk_size': sum(len(c.content) for c in created_chunks) / len(created_chunks) if created_chunks else 0,
            'chunking_time_seconds': chunking_time,
            'text_cleaned_chars_removed': len(raw_text) - len(cleaned_text),
            'document_language': document_language,
            'document_title': document_title
        }
        
        # Remplacer extracted_text par le texte nettoyé
        document.document_metadata['extracted_text'] = cleaned_text
        document.document_metadata['raw_text_length'] = len(raw_text)
        
        db.commit()
        
        logger.info(
            f"Chunking completed for {document_id}: "
            f"{len(created_chunks)} chunks, {chunks_with_ocr} with OCR, "
            f"{chunking_time:.2f}s"
        )
        
        # 9. Lancer l'embedding (prochaine étape)
        # TODO: Décommenter quand le worker embedding sera prêt
        # from app.workers.embedding_tasks import embed_document
        # embed_document.apply_async(args=[str(document_id)], queue='embedding')
        
        return {
            'document_id': str(document_id),
            'total_chunks': len(created_chunks),
            'chunks_with_ocr': chunks_with_ocr,
            'chunking_time_seconds': chunking_time,
            'text_cleaned': True,
            'chars_removed': len(raw_text) - len(cleaned_text),
            'document_language': document_language
        }
        
    except Exception as e:
        logger.error(f"Chunking failed for document {document_id}: {e}")
        db.rollback()
        raise
        
    finally:
        db.close()


# =============================================================================
# CHUNKING INTELLIGENT
# =============================================================================

def create_smart_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Découper le texte en chunks intelligents.
    
    Stratégie :
    1. Découper par sections (--- Page ---, === Page ===)
    2. Puis par paragraphes
    3. Puis par phrases
    4. Respecter les tableaux (ne pas les couper)
    
    Args:
        text: Texte nettoyé
        chunk_size: Taille cible en caractères
        overlap: Chevauchement entre chunks
        
    Returns:
        Liste de dicts avec 'text', 'char_start', 'char_end', 'page_hint'
    """
    chunks = []
    
    # Si le texte est vide ou très court
    if not text or len(text.strip()) < MIN_CHUNK_SIZE:
        if text and text.strip():
            return [{
                'text': text.strip(),
                'char_start': 0,
                'char_end': len(text),
                'page_number': None,
                'page_hint': None
            }]
        return []
    
    # Détecter les marqueurs de page
    page_pattern = r'(?:\n---\s*Page\s*(\d+)\s*---|\n===\s*Page\s*(\d+)\s*===)'
    
    # Découper par pages d'abord
    sections = re.split(page_pattern, text)
    
    current_page = None
    current_position = 0
    
    for section in sections:
        if not section:
            continue
        
        # Si c'est un numéro de page
        if section.isdigit():
            current_page = int(section)
            continue
        
        # Découper cette section en chunks
        section_chunks = chunk_section(
            section,
            chunk_size=chunk_size,
            overlap=overlap,
            page_number=current_page,
            start_position=current_position
        )
        
        chunks.extend(section_chunks)
        current_position += len(section)
    
    # Si aucun chunk créé, créer au moins un chunk avec tout le texte
    if not chunks and text.strip():
        chunks = [{
            'text': text.strip(),
            'char_start': 0,
            'char_end': len(text),
            'page_number': None,
            'page_hint': None
        }]
    
    return chunks


def chunk_section(
    text: str,
    chunk_size: int,
    overlap: int,
    page_number: Optional[int] = None,
    start_position: int = 0
) -> List[Dict[str, Any]]:
    """
    Découper une section de texte en chunks.
    
    Préserve :
    - Les tableaux (ne coupe pas au milieu)
    - Les paragraphes (coupe entre paragraphes si possible)
    """
    chunks = []
    
    # Section vide
    if not text or not text.strip():
        return []
    
    if len(text) <= chunk_size:
        # Section assez petite, un seul chunk
        if text.strip():
            chunks.append({
                'text': text.strip(),
                'char_start': start_position,
                'char_end': start_position + len(text),
                'page_number': page_number,
                'page_hint': f"Page {page_number}" if page_number else None
            })
        return chunks
    
    # Découper par paragraphes (double retour à la ligne)
    paragraphs = re.split(r'\n\n+', text)
    
    current_chunk = ""
    chunk_start = start_position
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Vérifier si c'est un tableau
        is_table = bool(re.match(r'\|', para))
        
        # Si ajouter ce paragraphe dépasse la taille
        if len(current_chunk) + len(para) + 2 > chunk_size:
            # Sauvegarder le chunk actuel
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'char_start': chunk_start,
                    'char_end': chunk_start + len(current_chunk),
                    'page_number': page_number,
                    'page_hint': f"Page {page_number}" if page_number else None
                })
            
            # Nouveau chunk avec overlap
            if overlap > 0 and current_chunk:
                # Prendre les derniers caractères pour l'overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk = para
            
            chunk_start = start_position + len(text) - len(current_chunk)
        else:
            # Ajouter au chunk actuel
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Dernier chunk
    if current_chunk.strip():
        chunks.append({
            'text': current_chunk.strip(),
            'char_start': chunk_start,
            'char_end': start_position + len(text),
            'page_number': page_number,
            'page_hint': f"Page {page_number}" if page_number else None
        })
    
    return chunks


def estimate_tokens(text: str) -> int:
    """
    Estimer le nombre de tokens dans un texte.
    
    Approximation : 1 token ≈ 4 caractères (pour langues latines)
    """
    if not text:
        return 0
    return len(text) // 4


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def sanitize_for_postgres(text: str) -> str:
    """Nettoyer le texte pour PostgreSQL (caractères NULL)."""
    if not text:
        return text
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text.replace('\x00', ''))