"""
Client Mistral AI pour les opérations d'embedding et génération.

Ce client centralise les interactions avec l'API Mistral pour :
- Embedding (mistral-embed)
- Reranking (mistral-small)
- Génération (mistral-medium, mistral-large)

MODIFICATION: Les tarifs et modèles sont maintenant lus depuis la DB via ConfigService.
Note: L'OCR est géré séparément dans app/rag/ocr_processor.py
"""
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from mistralai import Mistral
from mistralai.models import EmbeddingResponse

from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT (fallback si DB non disponible)
# =============================================================================

DEFAULT_EMBEDDING_MODEL = "mistral-embed"
DEFAULT_RERANKING_MODEL = "mistral-small-latest"
DEFAULT_GENERATION_MODEL = "mistral-medium-latest"
DEFAULT_EMBEDDING_BATCH_SIZE = 100
DEFAULT_EMBEDDING_DIMENSION = 1024

# Prix par défaut (fallback)
DEFAULT_PRICING = {
    "mistral-embed": {"input": 0.10, "output": 0.0},
    "mistral-small-latest": {"input": 0.10, "output": 0.30},
    "mistral-medium-latest": {"input": 0.40, "output": 2.00},
    "mistral-large-latest": {"input": 2.00, "output": 6.00},
}


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_model_config(model_type: str) -> Dict[str, Any]:
    """
    Récupère la configuration d'un modèle depuis la DB.
    
    Args:
        model_type: Type de modèle (embedding, reranking, generation, title_generation, ocr)
        
    Returns:
        Dict avec la configuration du modèle
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            config = get_config_service().get_model_config(model_type, db)
            return config if config else {}
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config modèle {model_type}: {e}")
        return {}


def get_pricing(model_key: str) -> Dict[str, float]:
    """
    Récupère les tarifs pour un modèle depuis la DB.
    
    Args:
        model_key: Clé du modèle (embed, small, medium, large, ocr)
        
    Returns:
        Dict avec price_per_million_input et price_per_million_output
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            pricing = get_config_service().get_pricing(model_key, db)
            return pricing
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire tarif {model_key}: {e}")
        # Retourner les valeurs par défaut
        model_name = f"mistral-{model_key}" if model_key != "embed" else "mistral-embed"
        default = DEFAULT_PRICING.get(model_name, {"input": 0.1, "output": 0.0})
        return {
            "price_per_million_input": default["input"],
            "price_per_million_output": default["output"],
            "model": model_name
        }


def get_embedding_model() -> str:
    """Récupère le modèle d'embedding depuis la config."""
    config = get_model_config("embedding")
    return config.get("model_name", DEFAULT_EMBEDDING_MODEL)


def get_embedding_batch_size() -> int:
    """Récupère la taille des batches d'embedding depuis la config."""
    try:
        from app.services.config_service import get_config_value
        db = SessionLocal()
        try:
            value = get_config_value("embedding.batch_size", db, default=DEFAULT_EMBEDDING_BATCH_SIZE)
            return value
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire batch_size: {e}")
        return DEFAULT_EMBEDDING_BATCH_SIZE


def get_embedding_dimension() -> int:
    """Récupère la dimension des embeddings depuis la config."""
    config = get_model_config("embedding")
    return config.get("dimension", DEFAULT_EMBEDDING_DIMENSION)


def get_reranking_model() -> str:
    """Récupère le modèle de reranking depuis la config."""
    config = get_model_config("reranking")
    return config.get("model_name", DEFAULT_RERANKING_MODEL)


def get_generation_model() -> str:
    """Récupère le modèle de génération depuis la config."""
    config = get_model_config("generation")
    return config.get("model_name", DEFAULT_GENERATION_MODEL)


# =============================================================================
# VARIABLES EXPORTÉES (pour compatibilité avec le code existant)
# =============================================================================

# Ces variables sont maintenant des fonctions, mais on garde les noms pour compatibilité
EMBEDDING_MODEL = DEFAULT_EMBEDDING_MODEL  # Utilisez get_embedding_model() pour la valeur dynamique
RERANKING_MODEL = DEFAULT_RERANKING_MODEL
EMBEDDING_BATCH_SIZE = DEFAULT_EMBEDDING_BATCH_SIZE
EMBEDDING_DIMENSION = DEFAULT_EMBEDDING_DIMENSION

# PRICING est maintenant dynamique - utilisez get_pricing()
PRICING = DEFAULT_PRICING  # Fallback, utilisez get_pricing() pour les vraies valeurs


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EmbeddingResult:
    """Résultat d'une opération d'embedding."""
    embeddings: List[List[float]]
    token_count: int
    model: str
    processing_time: float


@dataclass
class GenerationResult:
    """Résultat d'une opération de génération."""
    content: str
    token_count_input: int
    token_count_output: int
    model: str
    processing_time: float


# =============================================================================
# MISTRAL CLIENT
# =============================================================================

class MistralClient:
    """
    Client pour interagir avec l'API Mistral.
    
    Gère l'embedding, le reranking et la génération de texte.
    Les tarifs et modèles sont lus dynamiquement depuis la DB.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le client Mistral.
        
        Args:
            api_key: Clé API Mistral (utilise settings.MISTRAL_API_KEY par défaut)
        """
        self.api_key = api_key or settings.MISTRAL_API_KEY
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY non configurée")
        
        self.client = Mistral(api_key=self.api_key)
        logger.info("MistralClient initialisé")
    
    def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """
        Génère les embeddings pour une liste de textes.
        
        Args:
            texts: Liste de textes à embedder
            model: Modèle à utiliser (défaut: depuis config DB)
            
        Returns:
            EmbeddingResult avec les embeddings et métadonnées
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                token_count=0,
                model=model or get_embedding_model(),
                processing_time=0.0
            )
        
        # Utiliser le modèle de la config si non spécifié
        if model is None:
            model = get_embedding_model()
        
        start_time = time.time()
        
        try:
            response = self.client.embeddings.create(
                model=model,
                inputs=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            token_count = response.usage.total_tokens if response.usage else 0
            
            processing_time = time.time() - start_time
            
            logger.debug(
                f"Embedding: {len(texts)} textes, {token_count} tokens, "
                f"{processing_time:.2f}s"
            )
            
            return EmbeddingResult(
                embeddings=embeddings,
                token_count=token_count,
                model=model,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """
        Génère du texte à partir d'un prompt.
        
        Args:
            prompt: Prompt utilisateur
            model: Modèle à utiliser (défaut: depuis config DB)
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température de génération
            system_prompt: Prompt système optionnel
            
        Returns:
            GenerationResult avec le contenu généré et métadonnées
        """
        # Utiliser le modèle de la config si non spécifié
        if model is None:
            model = get_generation_model()
        
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            usage = response.usage
            
            processing_time = time.time() - start_time
            
            logger.debug(
                f"Generation: {usage.prompt_tokens} in, {usage.completion_tokens} out, "
                f"{processing_time:.2f}s"
            )
            
            return GenerationResult(
                content=content,
                token_count_input=usage.prompt_tokens,
                token_count_output=usage.completion_tokens,
                model=model,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Erreur génération: {e}")
            raise
    
    def calculate_cost(
        self,
        model: str,
        token_count_input: int,
        token_count_output: int = 0
    ) -> Dict[str, float]:
        """
        Calcule le coût d'une opération en USD.
        
        MODIFICATION: Lit les tarifs depuis la DB via ConfigService.
        
        Args:
            model: Nom du modèle utilisé
            token_count_input: Nombre de tokens en entrée
            token_count_output: Nombre de tokens en sortie
            
        Returns:
            Dict avec cost_input, cost_output, cost_total en USD
        """
        # Déterminer la clé de pricing
        if "embed" in model:
            pricing_key = "embed"
        elif "small" in model:
            pricing_key = "small"
        elif "medium" in model:
            pricing_key = "medium"
        elif "large" in model:
            pricing_key = "large"
        else:
            pricing_key = "embed"  # Fallback
        
        # Récupérer les tarifs depuis la DB
        pricing = get_pricing(pricing_key)
        
        price_input = pricing.get("price_per_million_input", 0.1)
        price_output = pricing.get("price_per_million_output", 0.0)
        
        cost_input = (token_count_input / 1_000_000) * price_input
        cost_output = (token_count_output / 1_000_000) * price_output
        
        return {
            "cost_input": cost_input,
            "cost_output": cost_output,
            "cost_total": cost_input + cost_output,
            "price_per_million_input": price_input,
            "price_per_million_output": price_output,
            "model": model
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_mistral_client: Optional[MistralClient] = None


def get_mistral_client() -> MistralClient:
    """
    Retourne une instance singleton du MistralClient.
    
    Returns:
        Instance MistralClient
    """
    global _mistral_client
    if _mistral_client is None:
        _mistral_client = MistralClient()
    return _mistral_client