"""
File upload utilities for document processing.

Provides validation, hashing, and storage utilities for uploaded files.
"""
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import uuid

from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)


# Configuration (sera importée depuis settings)
UPLOAD_MAX_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls",
    "pptx", "ppt", "txt", "md", "rtf",
    "png", "jpg", "jpeg", "webp", "gif"
}
UPLOAD_DIR = "/app/uploads"


def validate_file_type(filename: str) -> bool:
    """
    Valider le type de fichier par son extension.
    
    Args:
        filename: Nom du fichier
        
    Returns:
        True si le type est autorisé
        
    Raises:
        HTTPException: Si le type n'est pas autorisé
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if extension not in UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé: .{extension}. "
                   f"Types autorisés: {', '.join(sorted(UPLOAD_ALLOWED_EXTENSIONS))}"
        )
    
    return True


def validate_file_size(file_size: int, max_size: int = UPLOAD_MAX_SIZE) -> bool:
    """
    Valider la taille du fichier.
    
    Args:
        file_size: Taille du fichier en bytes
        max_size: Taille maximale autorisée en bytes
        
    Returns:
        True si la taille est valide
        
    Raises:
        HTTPException: Si le fichier est trop gros
    """
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux: {file_size_mb:.2f} MB. "
                   f"Taille maximale: {max_size_mb:.2f} MB"
        )
    
    return True


async def calculate_file_hash(file: UploadFile) -> str:
    """
    Calculer le hash SHA-256 d'un fichier.
    
    Args:
        file: Fichier uploadé
        
    Returns:
        Hash SHA-256 hexadécimal
    """
    hasher = hashlib.sha256()
    
    # Lire le fichier par chunks pour économiser la mémoire
    chunk_size = 8192
    await file.seek(0)
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
    
    # Remettre le curseur au début pour usage ultérieur
    await file.seek(0)
    
    file_hash = hasher.hexdigest()
    logger.info(f"Calculated hash for {file.filename}: {file_hash[:16]}...")
    
    return file_hash


def generate_stored_filename(original_filename: str) -> str:
    """
    Générer un nom de fichier unique pour le stockage.
    
    Format: {timestamp}_{uuid}_{original_name}
    
    Args:
        original_filename: Nom original du fichier
        
    Returns:
        Nom de fichier unique
    """
    # Extraire l'extension
    extension = ""
    if "." in original_filename:
        extension = "." + original_filename.rsplit(".", 1)[-1]
    
    # Nettoyer le nom (garder seulement alphanumeric et _-)
    clean_name = "".join(
        c if c.isalnum() or c in ("_", "-") else "_"
        for c in original_filename.rsplit(".", 1)[0]
    )
    
    # Limiter la longueur
    clean_name = clean_name[:50]
    
    # Générer nom unique
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    stored_filename = f"{timestamp}_{unique_id}_{clean_name}{extension}"
    
    return stored_filename


async def save_uploaded_file(
    file: UploadFile,
    upload_dir: str = UPLOAD_DIR
) -> Tuple[str, str]:
    """
    Sauvegarder un fichier uploadé sur le disque.
    
    Args:
        file: Fichier uploadé
        upload_dir: Répertoire de destination
        
    Returns:
        Tuple (stored_filename, file_path)
        
    Raises:
        HTTPException: Si l'écriture échoue
    """
    try:
        # Créer le répertoire si nécessaire
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Générer nom unique
        stored_filename = generate_stored_filename(file.filename)
        file_path = upload_path / stored_filename
        
        # Écrire le fichier par chunks
        chunk_size = 8192
        await file.seek(0)
        
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        logger.info(f"Saved file: {file.filename} -> {stored_filename}")
        
        return stored_filename, str(file_path)
    
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde du fichier: {str(e)}"
        )


def get_file_size_bytes(file_size: int) -> float:
    """
    Convertir taille en bytes vers MB.
    
    Args:
        file_size: Taille en bytes
        
    Returns:
        Taille en MB
    """
    return file_size


def get_file_type(filename: str) -> str:
    """
    Déterminer le type de fichier basé sur l'extension.
    
    Args:
        filename: Nom du fichier
        
    Returns:
        Type de fichier (pdf, docx, xlsx, image, text)
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    type_mapping = {
        "pdf": "pdf",
        "doc": "docx",
        "docx": "docx",
        "xls": "xlsx",
        "xlsx": "xlsx",
        "ppt": "pptx",
        "pptx": "pptx",
        "txt": "text",
        "md": "text",
        "rtf": "text",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "webp": "image",
        "gif": "image"
    }
    
    return type_mapping.get(extension, "unknown")


"""
Fix COMPLET pour file_upload.py - validate_and_prepare_file()
"""

async def validate_and_prepare_file(
    file: UploadFile,
    max_size: int = UPLOAD_MAX_SIZE
) -> dict:
    """
    Valider et préparer un fichier pour l'upload.
    
    Effectue toutes les validations nécessaires et calcule les métadonnées.
    
    Args:
        file: Fichier uploadé
        max_size: Taille maximale autorisée
        
    Returns:
        Dict avec métadonnées du fichier
        
    Raises:
        HTTPException: Si la validation échoue
    """
    # Valider le type
    validate_file_type(file.filename)
    
    # FIXED: Obtenir la taille du fichier
    # file.file est un SpooledTemporaryFile (sync, pas async)
    try:
        # Méthode 1: Utiliser file.file (SpooledTemporaryFile) - SYNC, pas await
        file.file.seek(0, 2)  # ✅ SANS await - c'est sync
        file_size = file.file.tell()
        file.file.seek(0)  # Retour au début
    except (AttributeError, TypeError):
        # Méthode 2: Lire tout le contenu (fallback)
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Remettre au début
    
    # Valider la taille
    validate_file_size(file_size, max_size)
    
    # Calculer le hash
    file_hash = await calculate_file_hash(file)
    
    # Déterminer le type
    file_type = get_file_type(file.filename)
    
    return {
        "original_filename": file.filename,
        "file_size": file_size,
        "file_size_bytes": get_file_size_bytes(file_size),
        "file_hash": file_hash,
        "file_extension": file_type,
        "mime_type": get_mime_type(file), 
    }

def get_mime_type(file: UploadFile) -> str:
    return file.content_type or "application/octet-stream"    


def delete_file(file_path: str) -> bool:
    """
    Supprimer un fichier du disque.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        True si supprimé, False sinon
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        else:
            logger.warning(f"File not found: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        return False