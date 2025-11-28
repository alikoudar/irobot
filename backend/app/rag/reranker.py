# -*- coding: utf-8 -*-
"""
MistralReranker - Reranking des chunks avec Mistral.

Ce module implémente le reranking des chunks récupérés par le HybridRetriever
en utilisant l'API Mistral pour évaluer la pertinence de chaque chunk
par rapport à la question de l'utilisateur.

Pipeline: top 10 chunks → reranking → top 3 chunks

MODIFICATION: Les configurations (model, top_n) sont lues depuis la DB via ConfigService.

Sprint 6 - Phase 2 : Retriever & Reranker
"""

import logging
import json
import re
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from app.core.config import settings
from app.db.session import SessionLocal
from app.rag.retriever import RetrievedChunk

from uuid import UUID

from sqlalchemy.orm import Session

# Configuration du logger
logger = logging.getLogger(__name__)


# =============================================================================
# VALEURS PAR DÉFAUT (fallback si DB non disponible)
# =============================================================================

DEFAULT_RERANKING_MODEL = "mistral-small-latest"
DEFAULT_RERANKING_TOP_N = 3
DEFAULT_RERANKING_TEMPERATURE = 0.0


# =============================================================================
# FONCTIONS POUR RÉCUPÉRER LES CONFIGS DEPUIS LA DB
# =============================================================================

def get_reranking_config() -> Dict[str, Any]:
    """
    Récupère la configuration de reranking depuis la DB.
    
    Returns:
        Dict avec model_name, top_k, temperature
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            service = get_config_service()
            model_config = service.get_model_config("reranking", db)
            return {
                "model_name": model_config.get("model_name", DEFAULT_RERANKING_MODEL),
                "top_k": model_config.get("top_k", DEFAULT_RERANKING_TOP_N),
                "temperature": model_config.get("temperature", DEFAULT_RERANKING_TEMPERATURE),
                "description": model_config.get("description", "")
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire config reranking: {e}")
        return {
            "model_name": DEFAULT_RERANKING_MODEL,
            "top_k": DEFAULT_RERANKING_TOP_N,
            "temperature": DEFAULT_RERANKING_TEMPERATURE
        }


def get_reranking_model() -> str:
    """Récupère le modèle de reranking depuis la config DB."""
    config = get_reranking_config()
    return config.get("model_name", DEFAULT_RERANKING_MODEL)


def get_reranking_top_n() -> int:
    """Récupère le paramètre top_n (top_k dans la DB) depuis la config DB."""
    config = get_reranking_config()
    return config.get("top_k", DEFAULT_RERANKING_TOP_N)


def get_reranking_pricing() -> Dict[str, float]:
    """
    Récupère les tarifs du modèle de reranking depuis la DB.
    
    Returns:
        Dict avec price_per_million_input, price_per_million_output
    """
    try:
        from app.services.config_service import get_config_service
        db = SessionLocal()
        try:
            pricing = get_config_service().get_pricing("small", db)
            return pricing
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Impossible de lire tarifs reranking: {e}")
        return {
            "price_per_million_input": 0.10,
            "price_per_million_output": 0.30,
            "model": DEFAULT_RERANKING_MODEL
        }


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RerankResult:
    """
    Résultat du reranking d'un chunk.
    
    Attributes:
        chunk: Le chunk original
        relevance_score: Score de pertinence (0-10)
        reasoning: Explication du score (optionnel)
    """
    chunk: RetrievedChunk
    relevance_score: float
    reasoning: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "chunk": self.chunk.to_dict(),
            "relevance_score": self.relevance_score,
            "reasoning": self.reasoning
        }


# =============================================================================
# MISTRAL RERANKER
# =============================================================================

class MistralReranker:
    """
    Classe pour le reranking des chunks avec Mistral.
    
    Utilise mistral-small pour évaluer la pertinence de chaque chunk
    par rapport à la question de l'utilisateur, puis retourne les
    N chunks les plus pertinents.
    
    Les configurations (model, top_n) sont lues dynamiquement depuis la DB.
    
    Attributes:
        mistral_client: Client Mistral pour les appels API
    """
    
    # Prompt système pour le reranking
    SYSTEM_PROMPT = """Tu es un expert en évaluation de la pertinence de textes.
Ta tâche est d'évaluer si un passage de texte répond à une question donnée.

Pour chaque passage, attribue un score de pertinence de 0 à 10 :
- 0-2 : Pas pertinent du tout
- 3-4 : Légèrement pertinent mais ne répond pas à la question
- 5-6 : Partiellement pertinent, contient des informations utiles
- 7-8 : Très pertinent, répond en grande partie à la question
- 9-10 : Parfaitement pertinent, répond exactement à la question

Réponds UNIQUEMENT avec un JSON valide, sans aucun texte avant ou après."""

    # Template pour l'évaluation d'un batch de chunks
    BATCH_PROMPT_TEMPLATE = """Question de l'utilisateur : "{query}"

Évalue la pertinence des {num_chunks} passages suivants par rapport à cette question.

{chunks_text}

Réponds avec un JSON contenant uniquement un tableau "scores" avec {num_chunks} objets.
Chaque objet doit avoir : "index" (0 à {max_index}), "score" (0-10), "reason" (explication courte).

Format attendu :
{{"scores": [{{"index": 0, "score": 8, "reason": "Répond directement..."}}, ...]}}"""

    def __init__(
        self,
        mistral_client = None
    ):
        """
        Initialise le MistralReranker.
        
        Args:
            mistral_client: Client Mistral (optionnel, créé si non fourni)
        """
        # Import différé pour éviter les imports circulaires
        if mistral_client is None:
            from app.clients.mistral_client import get_mistral_client
            self.mistral_client = get_mistral_client()
        else:
            self.mistral_client = mistral_client
        
        # Lire les configs depuis la DB
        config = get_reranking_config()
        
        logger.info(
            f"MistralReranker initialisé - Model: {config['model_name']}, "
            f"Top-N: {config['top_k']} (depuis DB)"
        )
    
    async def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_n: int = None,
        user_id: Optional[UUID] = None,  # ✅ NOUVEAU
        db: Optional[Session] = None
    ) -> List[RerankResult]:
        """
        Rerank les chunks et retourne les top N les plus pertinents.
        
        Args:
            query: Question de l'utilisateur
            chunks: Liste de chunks à reranker
            top_n: Nombre de chunks à retourner (défaut: depuis DB)
        
        Returns:
            Liste de RerankResult triés par score décroissant
        
        Raises:
            ValueError: Si query est vide ou chunks est vide
        """
        # Validation
        if not query or not query.strip():
            raise ValueError("La question ne peut pas être vide")
        
        if not chunks:
            logger.warning("Liste de chunks vide, retourne liste vide")
            return []
        
        query = query.strip()
        
        # Récupérer les configs depuis la DB si non spécifiées
        if top_n is None:
            top_n = get_reranking_top_n()
        
        # Récupérer le modèle depuis la DB
        model = get_reranking_model()
        
        logger.info(f"Reranking de {len(chunks)} chunks pour top {top_n} avec {model}")
        
        try:
            # Étape 1: Évaluer la pertinence de chaque chunk
            # ✅ MODIFIÉ : Récupérer aussi result avec les métriques
            scores, mistral_result = await self._evaluate_chunks(query, chunks, model)

            # ✅ MODIFIÉ : Tracking direct avec le result
            if db is not None and user_id is not None and mistral_result:
                self._track_reranking_usage(
                    result=mistral_result,
                    user_id=user_id,
                    db=db
                )
            
            # Étape 2: Créer les RerankResult
            results = self._create_results(chunks, scores)
            
            # Étape 3: Trier et limiter aux top N
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            top_results = results[:top_n]
            
            logger.info(
                f"Reranking terminé - Top {len(top_results)} chunks sélectionnés, "
                f"scores: {[r.relevance_score for r in top_results]}"
            )
            
            return top_results
            
        except Exception as e:
            logger.error(f"Erreur lors du reranking: {str(e)}")
            # Fallback: retourner les premiers chunks sans reranking
            logger.warning("Fallback: retour des chunks sans reranking")
            return [
                RerankResult(chunk=c, relevance_score=c.score)
                for c in chunks[:top_n]
            ]
    
    async def _evaluate_chunks(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        model: str
    ) -> Tuple[List[dict], Any]:
        """
        Évalue la pertinence de chaque chunk via Mistral.
        
        Args:
            query: Question de l'utilisateur
            chunks: Liste de chunks à évaluer
            model: Modèle à utiliser
        
        Returns:
            Tuple (scores, result) où:
            - scores: Liste de dictionnaires avec index, score et reason
            - result: Résultat complet de l'appel Mistral (avec métriques)
        """
        # Construction du texte des chunks
        chunks_text = self._format_chunks_for_prompt(chunks)
        
        # Construction du prompt
        user_prompt = self.BATCH_PROMPT_TEMPLATE.format(
            query=query,
            num_chunks=len(chunks),
            chunks_text=chunks_text,
            max_index=len(chunks) - 1
        )
        
        # Appel à Mistral via le client
        result = self.mistral_client.generate(
            prompt=user_prompt,
            model=model,
            temperature=DEFAULT_RERANKING_TEMPERATURE,
            max_tokens=1000,
            system_prompt=self.SYSTEM_PROMPT
        )
        
        # Parsing de la réponse JSON
        scores = self._parse_scores_response(result.content, len(chunks))
        
        # ✅ MODIFIÉ : Retourner aussi result pour le tracking
        return scores, result
    
    def _format_chunks_for_prompt(self, chunks: List[RetrievedChunk]) -> str:
        """
        Formate les chunks pour le prompt.
        
        Args:
            chunks: Liste de chunks
        
        Returns:
            Texte formaté pour le prompt
        """
        formatted = []
        
        for i, chunk in enumerate(chunks):
            # Limiter la longueur du texte pour éviter les prompts trop longs
            text = chunk.text[:1500] if len(chunk.text) > 1500 else chunk.text
            
            formatted.append(
                f"--- Passage {i} ---\n"
                f"Document: {chunk.document_title}\n"
                f"Page: {chunk.page_number}\n"
                f"Texte: {text}\n"
            )
        
        return "\n".join(formatted)
    
    def _parse_scores_response(
        self,
        response: str,
        num_chunks: int
    ) -> List[dict]:
        """
        Parse la réponse JSON de Mistral.
        
        Args:
            response: Réponse de Mistral
            num_chunks: Nombre de chunks attendus
        
        Returns:
            Liste de dictionnaires avec index, score et reason
        """
        try:
            # Nettoyer la réponse (enlever les backticks markdown si présents)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"```json?\n?", "", cleaned)
                cleaned = re.sub(r"```\n?$", "", cleaned)
            
            # Parser le JSON
            data = json.loads(cleaned)
            
            # Extraire les scores
            if "scores" in data:
                scores = data["scores"]
            elif isinstance(data, list):
                scores = data
            else:
                raise ValueError("Format de réponse invalide")
            
            # Valider et normaliser
            validated_scores = []
            for item in scores:
                validated_scores.append({
                    "index": int(item.get("index", 0)),
                    "score": min(10, max(0, float(item.get("score", 0)))),
                    "reason": item.get("reason", "")
                })
            
            # Vérifier qu'on a tous les scores
            if len(validated_scores) < num_chunks:
                logger.warning(
                    f"Scores manquants: {len(validated_scores)}/{num_chunks}"
                )
                # Ajouter les scores manquants avec une valeur par défaut
                existing_indices = {s["index"] for s in validated_scores}
                for i in range(num_chunks):
                    if i not in existing_indices:
                        validated_scores.append({
                            "index": i,
                            "score": 5.0,  # Score neutre par défaut
                            "reason": "Score par défaut"
                        })
            
            return validated_scores
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {str(e)}")
            logger.debug(f"Réponse brute: {response}")
            # Retourner des scores par défaut
            return [
                {"index": i, "score": 5.0, "reason": "Erreur parsing"}
                for i in range(num_chunks)
            ]
        except Exception as e:
            logger.error(f"Erreur inattendue parsing: {str(e)}")
            return [
                {"index": i, "score": 5.0, "reason": "Erreur"}
                for i in range(num_chunks)
            ]
    
    def _create_results(
        self,
        chunks: List[RetrievedChunk],
        scores: List[dict]
    ) -> List[RerankResult]:
        """
        Crée les RerankResult à partir des chunks et scores.
        
        Args:
            chunks: Liste de chunks originaux
            scores: Liste de scores avec index
        
        Returns:
            Liste de RerankResult
        """
        # Créer un mapping index -> score
        score_map = {s["index"]: s for s in scores}
        
        results = []
        for i, chunk in enumerate(chunks):
            score_data = score_map.get(i, {"score": 5.0, "reason": "Non évalué"})
            
            results.append(RerankResult(
                chunk=chunk,
                relevance_score=score_data["score"],
                reasoning=score_data.get("reason")
            ))
        
        return results
    
    def _track_reranking_usage(
        self,
        result,
        user_id: UUID,
        db: Session
    ) -> None:
        """
        Track les tokens/coûts du reranking.
        
        Args:
            result: Résultat de l'appel Mistral (GenerationResult)
            user_id: ID de l'utilisateur
            db: Session DB
        """
        try:
            from app.models.token_usage import TokenUsage, OperationType
            from app.services.exchange_rate_service import ExchangeRateService
            
            # Récupérer le taux de change
            exchange_rate = ExchangeRateService.get_current_rate(db, "USD", "XAF")
            if exchange_rate is None:
                exchange_rate = 615.0  # Fallback
            
            # ✅ STRUCTURE RÉELLE : GenerationResult de mistral_client.py
            # result.content (str)
            # result.token_count_input (int)
            # result.token_count_output (int)
            # result.model (str)
            # result.processing_time (float)
            
            token_count_input = result.token_count_input
            token_count_output = result.token_count_output
            token_count_total = token_count_input + token_count_output
            model_name = result.model
            
            # Calculer les coûts via mistral_client
            costs = self.mistral_client.calculate_cost(
                model=model_name,
                token_count_input=token_count_input,
                token_count_output=token_count_output
            )
            cost_usd = costs["cost_total"]
            cost_xaf = cost_usd * float(exchange_rate)
            
            usage = TokenUsage(
                operation_type=OperationType.RERANKING,
                model_name=model_name,
                token_count_input=token_count_input,
                token_count_output=token_count_output,
                token_count_total=token_count_total,
                cost_usd=round(cost_usd, 6),
                cost_xaf=round(cost_xaf, 4),
                exchange_rate=float(exchange_rate),
                user_id=user_id,
                message_id=None,  # Pas de message associé
                document_id=None
            )
            db.add(usage)
            db.commit()
            
            logger.info(
                f"Reranking tokens tracked: {token_count_total} tokens, "
                f"${cost_usd:.6f} (model: {model_name})"
            )
        except Exception as e:
            logger.error(f"Erreur tracking reranking: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    async def rerank_simple(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_n: int = None
    ) -> List[RetrievedChunk]:
        """
        Version simplifiée qui retourne directement les chunks rerankés.
        
        Args:
            query: Question de l'utilisateur
            chunks: Liste de chunks
            top_n: Nombre de chunks à retourner
        
        Returns:
            Liste de RetrievedChunk rerankés
        """
        results = await self.rerank(query, chunks, top_n)
        return [r.chunk for r in results]
    
    def get_config(self) -> dict:
        """Retourne la configuration actuelle du reranker (depuis DB)."""
        config = get_reranking_config()
        pricing = get_reranking_pricing()
        return {
            "model": config["model_name"],
            "top_n": config["top_k"],
            "temperature": config.get("temperature", DEFAULT_RERANKING_TEMPERATURE),
            "price_per_million_input": pricing.get("price_per_million_input", 0.10),
            "price_per_million_output": pricing.get("price_per_million_output", 0.30),
            "source": "database"
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_reranker_instance: Optional[MistralReranker] = None


def get_reranker() -> MistralReranker:
    """
    Retourne une instance singleton du MistralReranker.
    
    Returns:
        Instance MistralReranker
    """
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = MistralReranker()
    return _reranker_instance


# =============================================================================
# FACTORY FUNCTION (pour compatibilité)
# =============================================================================

def create_reranker(
    top_n: int = None,
    model: str = None
) -> MistralReranker:
    """
    Factory function pour créer un MistralReranker.
    
    Note: Les valeurs top_n et model sont ignorées car elles sont
    maintenant lues dynamiquement depuis la DB à chaque reranking.
    
    Args:
        top_n: Ignoré (utilise DB)
        model: Ignoré (utilise DB)
    
    Returns:
        Instance de MistralReranker configurée
    """
    if top_n is not None or model is not None:
        logger.warning(
            "Les paramètres top_n/model passés à create_reranker() sont ignorés. "
            "Les valeurs sont lues depuis la base de données."
        )
    
    return MistralReranker()