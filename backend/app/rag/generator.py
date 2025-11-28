# -*- coding: utf-8 -*-
"""
LLM Generator pour la génération de réponses avec streaming.

Sprint 7 - Phase 2 : Génération des réponses
CORRIGÉ : Interface exacte attendue par chat_service.py

Le chat_service.py attend :
- generate_streaming() retourne un AsyncGenerator
- Les chunks ont un attribut .type ("token", "metadata", "error")
- Les chunks ont .content, .metadata, .error
- metadata a .token_count_input, .token_count_output, .model_used
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import settings
from app.db.session import SessionLocal
from app.rag.prompts import (
    PromptBuilder,
    get_prompt_builder,
    ResponseFormat,
    get_format_for_query,
    ChunkForPrompt,
    HistoryMessage
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION (lecture depuis DB)
# =============================================================================

def get_generation_config() -> Dict[str, Any]:
    """
    Récupère la configuration pour la génération LLM depuis la DB.
    
    Returns:
        Dict avec model, max_tokens, temperature
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            model_config = service.get_model_config("generation", db)
            return {
                "model": model_config.get("model_name", "mistral-medium-latest"),
                "max_tokens": model_config.get("max_tokens", 2048),
                "temperature": model_config.get("temperature", 0.7),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config génération: {e}")
        return {
            "model": "mistral-medium-latest",
            "max_tokens": 2048,
            "temperature": 0.7,
        }


def get_title_generation_config() -> Dict[str, Any]:
    """
    Récupère la configuration pour la génération de titres.
    
    Returns:
        Dict avec model, max_tokens, temperature
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            model_config = service.get_model_config("title_generation", db)
            return {
                "model": model_config.get("model_name", "mistral-small-latest"),
                "max_tokens": model_config.get("max_tokens", 30),
                "temperature": model_config.get("temperature", 0.3),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config titre: {e}")
        return {
            "model": "mistral-small-latest",
            "max_tokens": 30,
            "temperature": 0.3,
        }


def get_generation_pricing() -> Dict[str, float]:
    """
    Récupère les tarifs pour la génération depuis la DB.
    
    Returns:
        Dict avec price_per_million_input, price_per_million_output
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            pricing = service.get_pricing("medium", db)
            return {
                "price_per_million_input": pricing.get("price_per_million_input", 2.5),
                "price_per_million_output": pricing.get("price_per_million_output", 7.5),
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire tarifs: {e}")
        return {
            "price_per_million_input": 2.5,
            "price_per_million_output": 7.5,
        }


def get_exchange_rate() -> float:
    """
    Récupère le taux de change USD -> XAF depuis la DB.
    
    Returns:
        Taux de change (défaut: 615.0)
    """
    try:
        from app.services.exchange_rate_service import ExchangeRateService
        db = SessionLocal()
        try:
            rate = ExchangeRateService.get_current_rate(db, "USD", "XAF")
            return float(rate) if rate else 615.0
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire taux de change: {e}")
        return 615.0


def calculate_title_generation_cost(
    token_count_input: int,
    token_count_output: int,
    model_name: str,
    exchange_rate: float
) -> tuple[float, float]:
    """
    Calcule le coût de génération de titre.
    
    Args:
        token_count_input: Tokens en entrée
        token_count_output: Tokens en sortie
        model_name: Nom du modèle (pour récupérer tarifs)
        exchange_rate: Taux USD/XAF
        
    Returns:
        Tuple (cost_usd, cost_xaf)
    """
    # Tarifs Mistral par défaut (mistral-small pour titres)
    price_per_million_input = 0.10
    price_per_million_output = 0.30
    
    # Adapter selon le modèle
    if "medium" in model_name.lower():
        price_per_million_input = 2.7
        price_per_million_output = 8.1
    elif "large" in model_name.lower():
        price_per_million_input = 2.0
        price_per_million_output = 6.0
    
    # Calcul coût USD
    cost_input = (token_count_input / 1_000_000) * price_per_million_input
    cost_output = (token_count_output / 1_000_000) * price_per_million_output
    cost_usd = cost_input + cost_output
    
    # Calcul coût XAF
    cost_xaf = cost_usd * exchange_rate
    
    return round(cost_usd, 6), round(cost_xaf, 4)


# =============================================================================
# DATA CLASSES (Interface attendue par chat_service.py)
# =============================================================================

@dataclass
class GenerationMetadata:
    """
    Métadonnées de génération.
    
    Attributs attendus par chat_service.py :
    - token_count_input
    - token_count_output
    - model_used (pas 'model')
    """
    token_count_input: int = 0
    token_count_output: int = 0
    token_count_total: int = 0
    model_used: str = ""  # ← chat_service.py attend model_used, pas model
    processing_time: float = 0.0
    cost_usd: float = 0.0
    cost_xaf: float = 0.0


@dataclass
class StreamedChunk:
    """
    Chunk de réponse streaming.
    
    Interface attendue par chat_service.py (lignes 482-502) :
    - chunk.type == "token" / "metadata" / "error"
    - chunk.content pour le texte
    - chunk.metadata pour les métadonnées
    - chunk.error pour les erreurs
    """
    type: str  # "token", "metadata", "error"
    content: Optional[str] = None
    metadata: Optional[GenerationMetadata] = None
    error: Optional[str] = None
    is_final: bool = False  # Gardé pour compatibilité


@dataclass
class GenerationResult:
    """Résultat complet d'une génération."""
    content: str
    metadata: GenerationMetadata
    sources: List[Dict[str, Any]] = field(default_factory=list)
    format_used: ResponseFormat = ResponseFormat.DEFAULT


@dataclass
class TitleGenerationResult:
    """
    Résultat de génération de titre avec métriques complètes.
    
    Attributes:
        content: Le titre généré
        model_name: Nom du modèle utilisé
        token_count_input: Nombre de tokens en entrée
        token_count_output: Nombre de tokens en sortie
        token_count_total: Total tokens
        cost_usd: Coût en USD
        cost_xaf: Coût en XAF
        exchange_rate: Taux de change utilisé
    """
    content: str
    model_name: str
    token_count_input: int
    token_count_output: int
    token_count_total: int
    cost_usd: float
    cost_xaf: float
    exchange_rate: float


# =============================================================================
# LLM GENERATOR
# =============================================================================

class LLMGenerator:
    """
    Générateur de réponses LLM avec support streaming.
    
    Utilise Mistral pour générer des réponses contextualisées
    avec les documents de la BEAC.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le générateur LLM.
        
        Args:
            api_key: Clé API Mistral (utilise settings si non fournie)
        """
        from mistralai import Mistral
        
        self.api_key = api_key or settings.MISTRAL_API_KEY
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY non configurée")
        
        self.client = Mistral(api_key=self.api_key)
        self.prompt_builder = get_prompt_builder()
        
        logger.info("LLMGenerator initialisé")
    
    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """Calcule le coût d'une génération."""
        pricing = get_generation_pricing()
        exchange_rate = get_exchange_rate()
        
        cost_usd = (
            (input_tokens / 1_000_000) * pricing["price_per_million_input"] +
            (output_tokens / 1_000_000) * pricing["price_per_million_output"]
        )
        
        cost_xaf = cost_usd * exchange_rate
        
        return {
            "cost_usd": round(cost_usd, 6),
            "cost_xaf": round(cost_xaf, 2)
        }
    
    def _prepare_messages(
        self,
        query: str,
        chunks: List[ChunkForPrompt],
        history: Optional[List[HistoryMessage]] = None,
        response_format: ResponseFormat = ResponseFormat.DEFAULT
    ) -> List[Dict[str, str]]:
        """Prépare les messages pour l'API Mistral."""
        # build_system_prompt() ne prend pas d'argument
        system_prompt = self.prompt_builder.build_system_prompt()
        
        # build_full_prompt gère le response_format
        user_prompt = self.prompt_builder.build_full_prompt(
            query=query,
            chunks=chunks,
            history=history,
            response_format=response_format
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _convert_chunks(self, chunks: List[Dict[str, Any]]) -> List[ChunkForPrompt]:
        """Convertit les chunks dict en ChunkForPrompt."""
        return [
            ChunkForPrompt(
                document_id=c.get("document_id", ""),
                title=c.get("document_title", c.get("title", "Document sans titre")),
                category=c.get("category_name", c.get("category", "")),
                page=c.get("page_number", c.get("page", 0)),
                text=c.get("text", c.get("content", "")),  # ← text, pas content
                score=c.get("score", c.get("relevance_score", 0.0)),
                date=c.get("upload_date", c.get("date")),
                reference=c.get("reference")
            )
            for c in chunks
        ]
    
    def _convert_history(
        self, 
        history: Optional[List[Dict[str, str]]]
    ) -> Optional[List[HistoryMessage]]:
        """Convertit l'historique dict en HistoryMessage."""
        if not history:
            return None
        return [
            HistoryMessage(
                role=h.get("role", "user"),
                content=h.get("content", "")
            )
            for h in history
        ]
    
    async def generate_streaming(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[StreamedChunk, None]:
        """
        Génère une réponse en streaming (ASYNCHRONE).
        
        Interface attendue par chat_service.py :
        - Retourne un AsyncGenerator compatible avec 'async for'
        - Yield des StreamedChunk avec .type, .content, .metadata
        
        Args:
            query: Question de l'utilisateur
            chunks: Chunks de contexte
            history: Historique de conversation
            model: Modèle à utiliser
            max_tokens: Nombre max de tokens
            temperature: Température de génération
            
        Yields:
            StreamedChunk avec type="token" ou type="metadata" ou type="error"
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()
        
        # Charger la config depuis la DB si non spécifiée
        config = get_generation_config()
        if model is None:
            model = config["model"]
        if max_tokens is None:
            max_tokens = config["max_tokens"]
        if temperature is None:
            temperature = config["temperature"]
        
        # Détecter le format de réponse optimal
        response_format = get_format_for_query(query)
        
        # Convertir les données
        chunks_for_prompt = self._convert_chunks(chunks)
        history_messages = self._convert_history(history)
        
        # Préparer les messages
        messages = self._prepare_messages(
            query=query,
            chunks=chunks_for_prompt,
            history=history_messages,
            response_format=response_format
        )
        
        logger.info(f"Génération streaming - Query: '{query[:50]}...', Model: {model}")
        
        # Variables pour collecter les métriques
        full_content = ""
        input_tokens = 0
        output_tokens = 0
        
        try:
            # Fonction synchrone pour le streaming Mistral
            def run_mistral_stream():
                nonlocal input_tokens, output_tokens
                
                stream_response = self.client.chat.stream(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                results = []
                for event in stream_response:
                    if hasattr(event, 'data') and event.data:
                        chunk_data = event.data
                        
                        # Extraire le contenu
                        if hasattr(chunk_data, 'choices') and chunk_data.choices:
                            choice = chunk_data.choices[0]
                            if hasattr(choice, 'delta') and choice.delta:
                                if hasattr(choice.delta, 'content') and choice.delta.content:
                                    results.append(choice.delta.content)
                        
                        # Extraire l'usage si disponible
                        if hasattr(chunk_data, 'usage') and chunk_data.usage:
                            usage = chunk_data.usage
                            if hasattr(usage, 'prompt_tokens'):
                                input_tokens = usage.prompt_tokens
                            if hasattr(usage, 'completion_tokens'):
                                output_tokens = usage.completion_tokens
                
                return results
            
            # Exécuter le stream dans un thread pool
            token_chunks = await loop.run_in_executor(None, run_mistral_stream)
            
            # Yield chaque token
            for content in token_chunks:
                full_content += content
                yield StreamedChunk(
                    type="token",
                    content=content,
                    is_final=False
                )
            
            # Calculer les métriques finales
            processing_time = time.time() - start_time
            
            # Estimer les tokens si non fournis
            if input_tokens == 0:
                total_input = sum(len(m["content"]) for m in messages)
                input_tokens = total_input // 4
            
            if output_tokens == 0:
                output_tokens = len(full_content) // 4
            
            # Calculer les coûts
            costs = self._calculate_cost(input_tokens, output_tokens)
            
            # Créer les métadonnées finales
            metadata = GenerationMetadata(
                token_count_input=input_tokens,
                token_count_output=output_tokens,
                token_count_total=input_tokens + output_tokens,
                model_used=model,  # ← chat_service attend model_used
                processing_time=processing_time,
                cost_usd=costs["cost_usd"],
                cost_xaf=costs["cost_xaf"]
            )
            
            # Yield les métadonnées
            yield StreamedChunk(
                type="metadata",
                metadata=metadata,
                is_final=True
            )
            
            logger.info(
                f"Génération terminée - {output_tokens} tokens, "
                f"{processing_time:.2f}s, ${costs['cost_usd']:.6f}"
            )
            
        except Exception as e:
            logger.error(f"Erreur génération streaming: {e}")
            yield StreamedChunk(
                type="error",
                error=str(e),
                is_final=True
            )
    
    def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> GenerationResult:
        """Génère une réponse complète (non-streaming)."""
        start_time = time.time()
        
        config = get_generation_config()
        if model is None:
            model = config["model"]
        if max_tokens is None:
            max_tokens = config["max_tokens"]
        if temperature is None:
            temperature = config["temperature"]
        
        response_format = get_format_for_query(query)
        chunks_for_prompt = self._convert_chunks(chunks)
        history_messages = self._convert_history(history)
        
        messages = self._prepare_messages(
            query=query,
            chunks=chunks_for_prompt,
            history=history_messages,
            response_format=response_format
        )
        
        logger.info(f"Génération - Query: '{query[:50]}...', Model: {model}")
        
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
            costs = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            metadata = GenerationMetadata(
                token_count_input=usage.prompt_tokens,
                token_count_output=usage.completion_tokens,
                token_count_total=usage.total_tokens,
                model_used=model,
                processing_time=processing_time,
                cost_usd=costs["cost_usd"],
                cost_xaf=costs["cost_xaf"]
            )
            
            sources = [
                {
                    "document_title": c.document_title,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "category": c.category,
                    "relevance_score": c.score
                }
                for c in chunks_for_prompt
            ]
            
            logger.info(f"Génération terminée - {usage.completion_tokens} tokens")
            
            return GenerationResult(
                content=content,
                metadata=metadata,
                sources=sources,
                format_used=response_format
            )
            
        except Exception as e:
            logger.error(f"Erreur génération: {e}")
            raise
    
    def generate_title_with_metrics(
        self, 
        query: str, 
        model: Optional[str] = None
    ) -> TitleGenerationResult:
        """
        Génère un titre court pour une conversation avec métriques complètes.
        
        ✅ NOUVEAU : Retourne TOUTES les métriques (tokens, coûts) en plus du titre.
        
        Args:
            query: Question de l'utilisateur
            model: Modèle à utiliser (optionnel, utilise config DB si None)
            
        Returns:
            TitleGenerationResult avec titre et métriques complètes
            
        Raises:
            Exception: Si erreur génération (retourne titre fallback avec métriques)
        """
        config = get_title_generation_config()
        if model is None:
            model = config["model"]
        
        # Récupérer le taux de change
        exchange_rate = get_exchange_rate()
        
        # Construire le prompt
        prompt = self.prompt_builder.build_title_prompt(query)
        
        try:
            # Appel API Mistral
            response = self.client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )
            
            # Extraire le titre
            title = response.choices[0].message.content.strip()
            title = title.strip('"\'')
            
            if len(title) > 50:
                title = title[:47] + "..."
            
            # Extraire les métriques de l'API Mistral
            token_count_input = response.usage.prompt_tokens
            token_count_output = response.usage.completion_tokens
            token_count_total = response.usage.total_tokens
            
            # Calculer les coûts
            cost_usd, cost_xaf = calculate_title_generation_cost(
                token_count_input=token_count_input,
                token_count_output=token_count_output,
                model_name=model,
                exchange_rate=exchange_rate
            )
            
            logger.debug(
                f"Titre généré: '{title}' "
                f"(tokens: {token_count_total}, cost: ${cost_usd:.6f})"
            )
            
            # Retourner résultat complet
            return TitleGenerationResult(
                content=title,
                model_name=model,
                token_count_input=token_count_input,
                token_count_output=token_count_output,
                token_count_total=token_count_total,
                cost_usd=cost_usd,
                cost_xaf=cost_xaf,
                exchange_rate=exchange_rate
            )
            
        except Exception as e:
            logger.error(f"Erreur génération titre: {e}")
            
            # Fallback : premiers mots de la question
            words = query.split()[:5]
            fallback_title = " ".join(words)[:50]
            
            # Retourner résultat fallback avec métriques à 0
            return TitleGenerationResult(
                content=fallback_title,
                model_name=model,
                token_count_input=0,
                token_count_output=0,
                token_count_total=0,
                cost_usd=0.0,
                cost_xaf=0.0,
                exchange_rate=exchange_rate
            )
    
    def generate_title(self, query: str, model: Optional[str] = None) -> str:
        """
        Génère un titre court pour une conversation.
        
        ✅ MODIFIÉ : Appelle generate_title_with_metrics() en interne mais retourne
        seulement le titre (backward compatibility).
        
        Args:
            query: Question de l'utilisateur
            model: Modèle à utiliser (optionnel)
            
        Returns:
            str: Le titre généré
        """
        # Appeler la nouvelle fonction avec métriques
        result = self.generate_title_with_metrics(query, model)
        
        # Retourner seulement le titre (backward compatibility)
        return result.content
        

        


# =============================================================================
# SINGLETON ET FACTORY
# =============================================================================

_generator: Optional[LLMGenerator] = None


def get_generator() -> LLMGenerator:
    """Retourne une instance singleton du générateur."""
    global _generator
    if _generator is None:
        _generator = LLMGenerator()
    return _generator


def create_generator(api_key: Optional[str] = None) -> LLMGenerator:
    """Crée une nouvelle instance du générateur."""
    return LLMGenerator(api_key=api_key)