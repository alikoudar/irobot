"""
Module de nettoyage et normalisation du texte extrait.

Nettoie les artefacts d'OCR et prépare le texte pour le chunking.
"""
import re
import unicodedata
from typing import Optional


def clean_extracted_text(text: str) -> str:
    """
    Nettoyer le texte extrait (OCR + natif) pour le chunking.
    
    Opérations :
    1. Supprimer les caractères NULL et de contrôle
    2. Normaliser les espaces et retours à la ligne
    3. Supprimer les artefacts OCR courants
    4. Normaliser l'Unicode
    5. Nettoyer la ponctuation
    
    Args:
        text: Texte brut extrait
        
    Returns:
        Texte nettoyé
    """
    if not text:
        return ""
    
    # 1. Supprimer caractères NULL et de contrôle
    text = remove_null_bytes(text)
    
    # 2. Normaliser Unicode (NFC)
    text = unicodedata.normalize('NFC', text)
    
    # 3. Supprimer artefacts OCR courants
    text = remove_ocr_artifacts(text)
    
    # 4. Normaliser espaces et lignes
    text = normalize_whitespace(text)
    
    # 5. Nettoyer ponctuation
    text = clean_punctuation(text)
    
    return text.strip()


def remove_null_bytes(text: str) -> str:
    """Supprimer les caractères NULL et de contrôle problématiques."""
    # Supprimer \x00 (NULL)
    text = text.replace('\x00', '')
    
    # Supprimer caractères de contrôle (sauf \n, \t, \r)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    return text


def remove_ocr_artifacts(text: str) -> str:
    """
    Supprimer les artefacts courants de l'OCR.
    
    Artefacts détectés :
    - --Mo, -Mo, Mo-- (fragments)
    - \-n (retours mal interprétés)
    - Tirets multiples mal placés
    - Caractères répétés anormaux
    """
    # Artefacts spécifiques observés
    artifacts = [
        r'--Mo',
        r'-Mo',
        r'Mo--',
        r'\\-n',
        r'\-n',
        r'--Ml',
        r'P--More',
        r'b--More',
    ]
    
    for artifact in artifacts:
        text = re.sub(re.escape(artifact), '', text)
    
    # Tirets multiples isolés (ex: "--- " mais pas "--- Page")
    text = re.sub(r'(?<!-)-{2,}(?![\s]*Page)(?![\s]*Slide)(?!\s*=)', '', text)
    
    # Supprimer lignes avec seulement des tirets/espaces
    text = re.sub(r'^[\s\-]+$', '', text, flags=re.MULTILINE)
    
    # Caractères répétés anormaux (plus de 3 fois)
    text = re.sub(r'(.)\1{4,}', r'\1\1\1', text)
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normaliser les espaces et retours à la ligne.
    
    - Remplacer tabulations par espaces
    - Supprimer espaces multiples
    - Normaliser retours à la ligne (max 2 consécutifs)
    - Supprimer espaces en fin de ligne
    """
    # Tabulations → espaces
    text = text.replace('\t', '  ')
    
    # Espaces multiples → un seul
    text = re.sub(r'[ ]+', ' ', text)
    
    # Supprimer espaces en fin de ligne
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)
    
    # Supprimer espaces en début de ligne (sauf indentation code)
    text = re.sub(r'^[ ]{1,3}(?=[^\s])', '', text, flags=re.MULTILINE)
    
    # Maximum 2 retours à la ligne consécutifs
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


def clean_punctuation(text: str) -> str:
    """
    Nettoyer la ponctuation mal formée.
    
    - Espaces avant ponctuation
    - Ponctuation doublée
    - Guillemets inconsistants
    """
    # Supprimer espace avant ponctuation
    text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
    
    # Ajouter espace après ponctuation si manquant
    text = re.sub(r'([.,;:!?])([A-ZÀ-Ÿa-zà-ÿ])', r'\1 \2', text)
    
    # Ponctuation doublée
    text = re.sub(r'([.,;:!?])\1+', r'\1', text)
    
    # Normaliser guillemets
    text = text.replace('``', '"').replace("''", '"')
    text = text.replace('«', '"').replace('»', '"')
    
    return text


def remove_duplicate_content(text: str) -> str:
    """
    Détecter et supprimer le contenu dupliqué.
    
    Quand l'extraction hybride génère du texte natif + OCR similaire,
    cette fonction tente de dédupliquer.
    """
    # Séparer par marqueurs de page/image
    sections = re.split(r'(?=\n---\s*Page|\n===\s*Page|\n\[Image)', text)
    
    seen_content = set()
    unique_sections = []
    
    for section in sections:
        # Normaliser pour comparaison (lowercase, sans espaces multiples)
        normalized = re.sub(r'\s+', ' ', section.lower().strip())
        
        # Garder seulement les 100 premiers caractères pour comparaison
        signature = normalized[:100]
        
        if signature and signature not in seen_content:
            seen_content.add(signature)
            unique_sections.append(section)
    
    return ''.join(unique_sections)


def extract_structured_data(text: str) -> dict:
    """
    Extraire les données structurées du texte (tableaux, listes, etc.).
    
    Returns:
        Dict avec :
        - tables: Liste des tableaux Markdown détectés
        - lists: Liste des listes détectées
        - headers: Liste des titres/headers
        - plain_text: Texte sans structure
    """
    result = {
        'tables': [],
        'lists': [],
        'headers': [],
        'plain_text': ''
    }
    
    # Extraire tableaux Markdown
    table_pattern = r'(\|[^\n]+\|\n)+'
    tables = re.findall(table_pattern, text)
    result['tables'] = tables
    
    # Extraire headers Markdown
    header_pattern = r'^#{1,6}\s+.+$'
    headers = re.findall(header_pattern, text, re.MULTILINE)
    result['headers'] = headers
    
    # Extraire listes
    list_pattern = r'^[\s]*[-*]\s+.+$'
    lists = re.findall(list_pattern, text, re.MULTILINE)
    result['lists'] = lists
    
    # Texte sans structure
    plain = text
    for table in tables:
        plain = plain.replace(table, '')
    result['plain_text'] = plain.strip()
    
    return result


def prepare_text_for_chunking(text: str, deduplicate: bool = True) -> str:
    """
    Pipeline complet de préparation du texte pour le chunking.
    
    Args:
        text: Texte brut extrait
        deduplicate: Tenter de supprimer les doublons
        
    Returns:
        Texte propre prêt pour le chunking
    """
    # 1. Nettoyage de base
    cleaned = clean_extracted_text(text)
    
    # 2. Déduplication optionnelle
    if deduplicate:
        cleaned = remove_duplicate_content(cleaned)
    
    # 3. Nettoyage final
    cleaned = normalize_whitespace(cleaned)
    
    return cleaned


# =============================================================================
# HELPERS POUR MÉTADONNÉES
# =============================================================================

def detect_document_language(text: str) -> str:
    """
    Détecter la langue du document (basique).
    
    Returns:
        Code langue ISO (fr, en, etc.)
    """
    # Mots-clés français
    french_keywords = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'est', 'pour', 'dans']
    
    # Mots-clés anglais
    english_keywords = ['the', 'is', 'are', 'for', 'and', 'with', 'this', 'that', 'from']
    
    text_lower = text.lower()
    words = text_lower.split()[:200]  # Analyser les 200 premiers mots
    
    fr_count = sum(1 for w in words if w in french_keywords)
    en_count = sum(1 for w in words if w in english_keywords)
    
    if fr_count > en_count:
        return 'fr'
    elif en_count > fr_count:
        return 'en'
    else:
        return 'unknown'


def extract_document_title(text: str) -> Optional[str]:
    """
    Tenter d'extraire le titre du document.
    
    Cherche :
    - Premier header Markdown
    - Première ligne non vide en majuscules
    - Premiers mots significatifs
    """
    lines = text.strip().split('\n')
    
    for line in lines[:10]:  # Chercher dans les 10 premières lignes
        line = line.strip()
        
        if not line:
            continue
        
        # Header Markdown
        if line.startswith('#'):
            return line.lstrip('#').strip()
        
        # Ligne en majuscules (probable titre)
        if line.isupper() and len(line) > 5:
            return line
        
        # Ligne commençant par majuscule, assez longue
        if line[0].isupper() and len(line) > 10 and not line.startswith('---'):
            return line[:100]  # Limiter à 100 caractères
    
    return None