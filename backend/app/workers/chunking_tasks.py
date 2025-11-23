"""
Chunking worker tasks avec nettoyage et restructuration du texte.

MODIFICATION: Les paramètres de chunking sont lus depuis la DB via ConfigService.
- chunk_size: depuis config "chunking.size"
- overlap: depuis config "chunking.overlap"
- min_size: depuis config "chunking.min_size"
- max_size: depuis config "chunking.max_size"
"""
import logging
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from celery import Task

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus, ProcessingStage
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT (fallback si DB non disponible)
# =============================================================================

DEFAULT_CHUNK_SIZE = 512       # Taille cible en tokens
DEFAULT_CHUNK_OVERLAP = 51     # Chevauchement (10%)
DEFAULT_MIN_CHUNK_SIZE = 50    # Taille minimum
DEFAULT_MAX_CHUNK_SIZE = 1024  # Taille maximum


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_chunking_config() -> Dict[str, int]:
    """
    Récupère les paramètres de chunking depuis la DB.
    
    Returns:
        Dict avec chunk_size, overlap, min_size, max_size
    """
    try:
        from app.services.config_service import get_chunking_config as _get_chunking_config
        db = SessionLocal()
        try:
            config = _get_chunking_config(db)
            return config
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config chunking: {e}, utilisation des défauts")
        return {
            "chunk_size": DEFAULT_CHUNK_SIZE,
            "overlap": DEFAULT_CHUNK_OVERLAP,
            "min_size": DEFAULT_MIN_CHUNK_SIZE,
            "max_size": DEFAULT_MAX_CHUNK_SIZE,
        }


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
    queue="chunking",
    max_retries=3,
    default_retry_delay=30
)
def chunk_document(self, document_id: str) -> Dict[str, Any]:
    """
    Découper un document en chunks avec nettoyage et enrichissement.
    
    Les paramètres de chunking sont lus depuis la DB:
    - chunking.size: taille cible en tokens
    - chunking.overlap: chevauchement entre chunks
    - chunking.min_size: taille minimum
    - chunking.max_size: taille maximum
    
    Args:
        document_id: UUID du document
        
    Returns:
        Dict avec statistiques du chunking
    """
    # Import ici pour éviter les imports circulaires
    from app.rag.text_cleaner import (
        clean_extracted_text,
        prepare_text_for_chunking,
        detect_document_language,
        extract_document_title
    )
    
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        # =================================================================
        # 0. CHARGER LES CONFIGURATIONS DEPUIS LA DB
        # =================================================================
        
        config = get_chunking_config()
        chunk_size = config.get("chunk_size", DEFAULT_CHUNK_SIZE)
        chunk_overlap = config.get("overlap", DEFAULT_CHUNK_OVERLAP)
        min_chunk_size = config.get("min_size", DEFAULT_MIN_CHUNK_SIZE)
        max_chunk_size = config.get("max_size", DEFAULT_MAX_CHUNK_SIZE)
        
        logger.info(
            f"Config chunking chargée - Size: {chunk_size}, Overlap: {chunk_overlap}, "
            f"Min: {min_chunk_size}, Max: {max_chunk_size}"
        )
        
        # =================================================================
        # 1. CHARGER LE DOCUMENT
        # =================================================================
        
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} non trouvé")
        
        # Mettre à jour le status
        document.status = DocumentStatus.PROCESSING
        document.processing_stage = ProcessingStage.CHUNKING
        db.commit()
        
        # =================================================================
        # 2. RÉCUPÉRER LE TEXTE EXTRAIT
        # =================================================================
        
        doc_metadata = document.document_metadata or {}
        raw_text = doc_metadata.get('extracted_text', '')
        
        if not raw_text:
            raise ValueError(f"Pas de texte extrait pour le document {document_id}")
        
        extraction_method = doc_metadata.get('extraction_method', 'UNKNOWN')
        total_images_ocr = doc_metadata.get('total_images_ocr', 0)
        
        # =================================================================
        # 3. NETTOYER LE TEXTE
        # =================================================================
        
        cleaned_text = clean_extracted_text(raw_text)
        cleaned_text = prepare_text_for_chunking(cleaned_text)
        
        # Détecter langue et titre
        document_language = detect_document_language(cleaned_text)
        document_title = extract_document_title(cleaned_text) or document.original_filename
        
        # =================================================================
        # 4. DÉCOUPER EN CHUNKS (avec config de la DB)
        # =================================================================
        
        chunks_data = create_smart_chunks(
            text=cleaned_text,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            min_size=min_chunk_size,
            max_size=max_chunk_size
        )
        
        # =================================================================
        # 5. SUPPRIMER LES ANCIENS CHUNKS
        # =================================================================
        
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        db.flush()
        
        # =================================================================
        # 6. CRÉER LES NOUVEAUX CHUNKS
        # =================================================================
        
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
            
            # Métadonnées enrichies
            chunk_metadata = {
                'document_id': str(document.id),
                'document_filename': document.original_filename,
                'document_type': document.file_extension,
                'document_language': document_language,
                'document_title': document_title,
                'extraction_method': extraction_method,
                'has_ocr_content': has_ocr_content,
                'total_images_in_doc': total_images_ocr,
                'chunk_index': idx,
                'chunk_total': len(chunks_data),
                'has_table': has_table,
                'page_hint': chunk_data.get('page_hint'),
                'char_start': chunk_data.get('char_start', 0),
                'char_end': chunk_data.get('char_end', 0),
                # Config utilisée
                'chunking_config': {
                    'chunk_size': chunk_size,
                    'overlap': chunk_overlap,
                }
            }
            
            # Générer un weaviate_id temporaire
            temp_weaviate_id = str(uuid.uuid4())
            
            chunk = Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                weaviate_id=temp_weaviate_id,
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
        
        # =================================================================
        # 7. METTRE À JOUR LE DOCUMENT
        # =================================================================
        
        chunking_time = (datetime.utcnow() - start_time).total_seconds()
        
        document.total_chunks = len(created_chunks)
        document.chunking_time_seconds = chunking_time
        document.processing_stage = ProcessingStage.CHUNKING
        
        document.document_metadata['chunking_stats'] = {
            'total_chunks': len(created_chunks),
            'chunks_with_ocr': chunks_with_ocr,
            'avg_chunk_size': sum(len(c.content) for c in created_chunks) / len(created_chunks) if created_chunks else 0,
            'chunking_time_seconds': chunking_time,
            'text_cleaned_chars_removed': len(raw_text) - len(cleaned_text),
            'document_language': document_language,
            'document_title': document_title,
            # Config utilisée
            'config_used': {
                'chunk_size': chunk_size,
                'overlap': chunk_overlap,
                'min_size': min_chunk_size,
                'max_size': max_chunk_size,
            }
        }
        
        document.document_metadata['extracted_text'] = cleaned_text
        document.document_metadata['raw_text_length'] = len(raw_text)
        
        db.commit()
        
        logger.info(
            f"Chunking terminé pour {document_id}: "
            f"{len(created_chunks)} chunks (config: size={chunk_size}, overlap={chunk_overlap}), "
            f"{chunks_with_ocr} avec OCR, {chunking_time:.2f}s"
        )
        
        # =================================================================
        # 8. LANCER L'EMBEDDING
        # =================================================================
        
        from app.workers.embedding_tasks import embed_chunks
        embed_chunks.delay(str(document_id))
        
        logger.info(f"Document {document_id} envoyé à la queue embedding")
        
        return {
            'document_id': str(document_id),
            'total_chunks': len(created_chunks),
            'chunks_with_ocr': chunks_with_ocr,
            'chunking_time_seconds': chunking_time,
            'text_cleaned': True,
            'chars_removed': len(raw_text) - len(cleaned_text),
            'document_language': document_language,
            'config_used': {
                'chunk_size': chunk_size,
                'overlap': chunk_overlap,
            },
            'next_stage': 'embedding'
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
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_size: int = DEFAULT_MIN_CHUNK_SIZE,
    max_size: int = DEFAULT_MAX_CHUNK_SIZE
) -> List[Dict[str, Any]]:
    """
    Découper le texte en chunks intelligents.
    
    Args:
        text: Texte à découper
        chunk_size: Taille cible en tokens
        overlap: Chevauchement entre chunks
        min_size: Taille minimum
        max_size: Taille maximum
        
    Returns:
        Liste de dicts avec 'text', 'char_start', 'char_end', 'page_hint'
    """
    # Convertir tokens en caractères (approximation: 1 token ≈ 4 caractères)
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    char_min = min_size * 4
    
    if not text or len(text) < char_min:
        return [{'text': text, 'char_start': 0, 'char_end': len(text), 'page_hint': None}] if text else []
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(text):
        end_pos = min(current_pos + char_size, len(text))
        
        # Chercher une bonne coupure si on n'est pas à la fin
        if end_pos < len(text):
            # Chercher un séparateur de section
            section_match = re.search(r'\n(?:---|\===)[^\n]*\n', text[current_pos:end_pos])
            if section_match and section_match.end() > char_size * 0.5:
                end_pos = current_pos + section_match.end()
            else:
                # Chercher un double saut de ligne
                para_pos = text.rfind('\n\n', current_pos, end_pos)
                if para_pos > current_pos + char_size * 0.5:
                    end_pos = para_pos + 2
                else:
                    # Chercher un simple saut de ligne
                    line_pos = text.rfind('\n', current_pos, end_pos)
                    if line_pos > current_pos + char_size * 0.5:
                        end_pos = line_pos + 1
                    else:
                        # Chercher un espace
                        space_pos = text.rfind(' ', current_pos, end_pos)
                        if space_pos > current_pos + char_size * 0.5:
                            end_pos = space_pos + 1
        
        # Extraire le chunk
        chunk_text = text[current_pos:end_pos].strip()
        
        if len(chunk_text) >= char_min or current_pos + char_size >= len(text):
            # Détecter le numéro de page
            page_match = re.search(r'(?:Page|PAGE|page)\s*(\d+)', chunk_text)
            page_hint = int(page_match.group(1)) if page_match else None
            
            chunks.append({
                'text': chunk_text,
                'char_start': current_pos,
                'char_end': end_pos,
                'page_hint': page_hint,
                'page_number': page_hint
            })
        
        # Avancer avec overlap
        current_pos = end_pos - char_overlap if end_pos < len(text) else len(text)
    
    return chunks


def estimate_tokens(text: str) -> int:
    """
    Estime le nombre de tokens dans un texte.
    
    Approximation: 1 token ≈ 4 caractères (français)
    
    Args:
        text: Texte à analyser
        
    Returns:
        Nombre estimé de tokens
    """
    return int(len(text) / 4)