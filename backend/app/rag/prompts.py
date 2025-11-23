# -*- coding: utf-8 -*-
"""
Prompts système pour le chatbot RAG BEAC.

Ce module définit tous les prompts utilisés pour :
- La génération de réponses (système et utilisateur)
- La génération de titres de conversation
- Le formatage du contexte et de l'historique
- Les instructions de formatage (tableaux, code, listes)

Sprint 7 - Phase 2 : Prompts & Generator
CORRIGÉ : Prompt système strict pour éviter hallucinations et recommandations
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# TYPES DE FORMAT DE RÉPONSE
# =============================================================================

class ResponseFormat(str, Enum):
    """Types de format de réponse attendu."""
    DEFAULT = "default"
    TABLE = "table"
    LIST = "list"
    NUMBERED = "numbered"
    CODE = "code"
    COMPARISON = "comparison"
    CHRONOLOGICAL = "chronological"
    STEP_BY_STEP = "step_by_step"


# =============================================================================
# PROMPT SYSTÈME PRINCIPAL - VERSION STRICTE
# =============================================================================

SYSTEM_PROMPT_BASE = """Tu es un assistant documentaire de la BEAC (Banque des États de l'Afrique Centrale).

═══════════════════════════════════════════════════════════════════════════════
                        RÈGLES ABSOLUES ET NON NÉGOCIABLES
═══════════════════════════════════════════════════════════════════════════════

1. UTILISE UNIQUEMENT le contenu des documents fournis dans le CONTEXTE
2. Si l'information N'EST PAS dans le contexte, réponds : "Cette information n'est pas disponible dans les documents fournis."
3. NE JAMAIS inventer, supposer, ou compléter avec des connaissances externes
4. NE JAMAIS donner de recommandations, conseils ou suggestions
5. NE JAMAIS mentionner les scores de pertinence aux utilisateurs
6. NE JAMAIS dire "à titre indicatif", "processus générique", "exemple standard"

═══════════════════════════════════════════════════════════════════════════════
                              INTERDICTIONS STRICTES
═══════════════════════════════════════════════════════════════════════════════

❌ INTERDIT : "Je recommande de consulter..."
❌ INTERDIT : "Il serait nécessaire de..."
❌ INTERDIT : "Voici un processus générique..."
❌ INTERDIT : "À titre indicatif..."
❌ INTERDIT : "Non sourcé des documents BEAC..."
❌ INTERDIT : Toute information NON PRÉSENTE dans le contexte fourni
❌ INTERDIT : Ajouter des avertissements ou disclaimers inventés

═══════════════════════════════════════════════════════════════════════════════
                              CE QUE TU DOIS FAIRE
═══════════════════════════════════════════════════════════════════════════════

✅ Extraire et reformuler UNIQUEMENT les informations du contexte
✅ Citer les sources avec [Document X] - Nom du document
✅ Structurer la réponse de manière claire (listes, tableaux si pertinent)
✅ Répondre de façon concise et factuelle
✅ Si plusieurs documents traitent du sujet, les synthétiser

═══════════════════════════════════════════════════════════════════════════════
                              FORMAT DES CITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Pour chaque information, cite la source : [Document X]
- Format : **[Document 1]** Nom du document - information extraite
- Pour les décisions/circulaires : cite le numéro (ex: Décision N°024/GR/2018)

═══════════════════════════════════════════════════════════════════════════════

Réponds en français, de manière concise et STRICTEMENT basée sur le contexte."""


# =============================================================================
# TEMPLATES DE SECTIONS - VERSION SIMPLIFIÉE (sans score de pertinence)
# =============================================================================

CONTEXT_HEADER = """
## CONTEXTE DOCUMENTAIRE

Voici les extraits de documents disponibles pour répondre à la question :
"""

# Template SANS le score de pertinence (ne pas montrer à l'utilisateur)
CONTEXT_CHUNK_TEMPLATE = """
---
**[Document {index}]** {title}
- Catégorie : {category}
- Page : {page}
- Date : {date}

{text}
---
"""

CONTEXT_CHUNK_SIMPLE_TEMPLATE = """
**[Document {index}]** {title} (Page {page})
{text}
"""

HISTORY_HEADER = """
## HISTORIQUE DE CONVERSATION
"""

HISTORY_MESSAGE_TEMPLATE = """**{role}** : {content}
"""

QUERY_HEADER = """
## QUESTION
"""

# Instructions de fin STRICTES
INSTRUCTIONS_FOOTER = """
## INSTRUCTIONS

{format_instructions}

⚠️ RAPPEL CRITIQUE : Réponds UNIQUEMENT avec les informations du contexte ci-dessus.
Si l'information n'y figure pas, indique simplement qu'elle n'est pas disponible.
NE DONNE AUCUNE recommandation ou information externe."""


# =============================================================================
# INSTRUCTIONS DE FORMATAGE SPÉCIFIQUES
# =============================================================================

FORMAT_INSTRUCTIONS = {
    ResponseFormat.DEFAULT: """
Réponds de manière claire et structurée en utilisant UNIQUEMENT le contenu des documents.""",

    ResponseFormat.TABLE: """
Présente les informations sous forme de tableau Markdown.
Utilise UNIQUEMENT les données présentes dans les documents.""",

    ResponseFormat.LIST: """
Présente les informations sous forme de liste à puces.
Chaque point doit provenir des documents fournis.""",

    ResponseFormat.NUMBERED: """
Présente les informations sous forme de liste numérotée.
L'ordre doit refléter celui des documents ou la logique du processus décrit.""",

    ResponseFormat.CODE: """
Présente les informations techniques telles qu'elles apparaissent dans les documents.
Utilise des blocs de code si le document contient du code.""",

    ResponseFormat.COMPARISON: """
Compare les éléments en utilisant UNIQUEMENT les informations des documents.
Présente sous forme de tableau comparatif si pertinent.""",

    ResponseFormat.CHRONOLOGICAL: """
Présente les informations par ordre chronologique.
Utilise les dates mentionnées dans les documents.""",

    ResponseFormat.STEP_BY_STEP: """
Présente le processus étape par étape tel que décrit dans les documents.
Numérote les étapes dans l'ordre indiqué par le document source."""
}


# =============================================================================
# PROMPT POUR GÉNÉRATION DE TITRE
# =============================================================================

TITLE_GENERATION_PROMPT = """Génère un titre court et descriptif pour cette conversation.

Question : "{query}"

Règles :
- Maximum 50 caractères
- Pas de guillemets
- Pas de ponctuation finale
- En français
- Résume le sujet principal

Réponds UNIQUEMENT avec le titre."""


TITLE_GENERATION_SYSTEM_PROMPT = """Tu génères des titres courts pour des conversations. Réponds uniquement avec le titre."""


# =============================================================================
# RÉPONSE QUAND PAS DE CONTEXTE - VERSION SIMPLE
# =============================================================================

NO_CONTEXT_RESPONSE = """Cette information n'est pas disponible dans les documents actuellement indexés.

Vous pouvez reformuler votre question ou vérifier que les documents pertinents ont été ajoutés à la base documentaire."""


# =============================================================================
# CLASSE PROMPT BUILDER
# =============================================================================

@dataclass
class ChunkForPrompt:
    """Représentation d'un chunk pour le prompt."""
    document_id: str
    title: str
    category: str
    page: int
    text: str
    score: float
    date: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class HistoryMessage:
    """Représentation d'un message d'historique."""
    role: str  # "user" ou "assistant"
    content: str


class PromptBuilder:
    """
    Constructeur de prompts pour le chatbot RAG.
    
    Version corrigée : n'affiche PAS les scores de pertinence.
    """
    
    def __init__(
        self,
        max_context_tokens: int = 4000,
        max_history_messages: int = 5,
        max_chunk_length: int = 1500,
        use_detailed_chunks: bool = True
    ):
        """
        Initialise le PromptBuilder.
        
        Args:
            max_context_tokens: Limite approximative de tokens pour le contexte
            max_history_messages: Nombre maximum de messages d'historique
            max_chunk_length: Longueur maximale d'un chunk (caractères)
            use_detailed_chunks: Utiliser le format détaillé pour les chunks
        """
        self.max_context_tokens = max_context_tokens
        self.max_history_messages = max_history_messages
        self.max_chunk_length = max_chunk_length
        self.use_detailed_chunks = use_detailed_chunks
    
    def build_system_prompt(self) -> str:
        """
        Construit le prompt système.
        
        Returns:
            Prompt système complet
        """
        return SYSTEM_PROMPT_BASE
    
    def build_context_section(
        self,
        chunks: List[ChunkForPrompt],
        detailed: bool = None
    ) -> str:
        """
        Construit la section contexte avec les chunks de documents.
        
        NOTE: Ne pas inclure les scores de pertinence dans le prompt !
        
        Args:
            chunks: Liste des chunks à inclure
            detailed: Utiliser le format détaillé (défaut: self.use_detailed_chunks)
        
        Returns:
            Section contexte formatée
        """
        if not chunks:
            return ""
        
        if detailed is None:
            detailed = self.use_detailed_chunks
        
        context_parts = [CONTEXT_HEADER]
        
        for i, chunk in enumerate(chunks, 1):
            # Tronquer le texte si nécessaire
            text = chunk.text
            if len(text) > self.max_chunk_length:
                text = text[:self.max_chunk_length] + "..."
            
            if detailed:
                # Format détaillé SANS le score de pertinence
                context_parts.append(
                    CONTEXT_CHUNK_TEMPLATE.format(
                        index=i,
                        title=chunk.title,
                        category=chunk.category or "Non catégorisé",
                        page=chunk.page or "N/A",
                        date=chunk.date or "Non spécifiée",
                        text=text
                    )
                )
            else:
                context_parts.append(
                    CONTEXT_CHUNK_SIMPLE_TEMPLATE.format(
                        index=i,
                        title=chunk.title,
                        page=chunk.page or "N/A",
                        text=text
                    )
                )
        
        return "\n".join(context_parts)
    
    def build_history_section(
        self,
        history: List[HistoryMessage]
    ) -> str:
        """
        Construit la section historique de conversation.
        
        Args:
            history: Liste des messages d'historique
        
        Returns:
            Section historique formatée
        """
        if not history:
            return ""
        
        # Limiter le nombre de messages
        recent_history = history[-self.max_history_messages:]
        
        history_parts = [HISTORY_HEADER]
        
        for msg in recent_history:
            role_display = "Vous" if msg.role == "user" else "Assistant"
            # Tronquer les messages longs
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            
            history_parts.append(
                HISTORY_MESSAGE_TEMPLATE.format(
                    role=role_display,
                    content=content
                )
            )
        
        return "\n".join(history_parts)
    
    def build_query_section(self, query: str) -> str:
        """
        Construit la section question utilisateur.
        
        Args:
            query: Question de l'utilisateur
        
        Returns:
            Section question formatée
        """
        return f"{QUERY_HEADER}\n\n{query}"
    
    def build_format_instructions(
        self,
        response_format: ResponseFormat = ResponseFormat.DEFAULT
    ) -> str:
        """
        Construit les instructions de formatage.
        
        Args:
            response_format: Type de format demandé
        
        Returns:
            Instructions de formatage
        """
        format_instructions = FORMAT_INSTRUCTIONS.get(
            response_format,
            FORMAT_INSTRUCTIONS[ResponseFormat.DEFAULT]
        )
        
        return INSTRUCTIONS_FOOTER.format(format_instructions=format_instructions)
    
    def detect_response_format(self, query: str) -> ResponseFormat:
        """
        Détecte automatiquement le format de réponse approprié.
        
        Args:
            query: Question de l'utilisateur
        
        Returns:
            ResponseFormat détecté
        """
        query_lower = query.lower()
        
        # Détection des tableaux/comparaisons
        if any(word in query_lower for word in [
            "compare", "comparaison", "différence", "versus", "vs",
            "tableau", "liste des", "récapitulatif", "synthèse"
        ]):
            return ResponseFormat.TABLE
        
        # Détection des processus/étapes
        if any(word in query_lower for word in [
            "comment", "procédure", "étapes", "processus", "faire pour",
            "démarche", "méthode", "comment faire"
        ]):
            return ResponseFormat.STEP_BY_STEP
        
        # Détection chronologique
        if any(word in query_lower for word in [
            "évolution", "historique", "chronologie", "depuis",
            "quelles décisions", "quelles circulaires", "au fil du temps",
            "par ordre", "dates"
        ]):
            return ResponseFormat.CHRONOLOGICAL
        
        # Détection code/technique
        if any(word in query_lower for word in [
            "code", "commande", "script", "configuration", "technique",
            "paramètre", "syntaxe", "format", "terminal", "shell",
            "sql", "python", "bash", "json", "xml"
        ]):
            return ResponseFormat.CODE
        
        # Détection comparaison
        if any(word in query_lower for word in [
            "avantages", "inconvénients", "pour et contre",
            "meilleur", "préférable", "choisir entre"
        ]):
            return ResponseFormat.COMPARISON
        
        # Détection liste numérotée
        if any(word in query_lower for word in [
            "combien", "nombre de", "classement", "top", "rang"
        ]):
            return ResponseFormat.NUMBERED
        
        # Détection liste simple
        if any(word in query_lower for word in [
            "liste", "énumère", "quels sont", "quelles sont",
            "citez", "nommez", "exemples"
        ]):
            return ResponseFormat.LIST
        
        return ResponseFormat.DEFAULT
    
    def build_full_prompt(
        self,
        query: str,
        chunks: Optional[List[ChunkForPrompt]] = None,
        history: Optional[List[HistoryMessage]] = None,
        response_format: Optional[ResponseFormat] = None,
        include_format_instructions: bool = True
    ) -> str:
        """
        Construit le prompt complet (partie utilisateur).
        
        Args:
            query: Question de l'utilisateur
            chunks: Liste des chunks de contexte
            history: Historique de conversation
            response_format: Format de réponse (auto-détecté si None)
            include_format_instructions: Inclure les instructions de format
        
        Returns:
            Prompt utilisateur complet
        """
        parts = []
        
        # Ajouter le contexte si disponible
        if chunks:
            context_section = self.build_context_section(chunks)
            parts.append(context_section)
        
        # Ajouter l'historique si disponible
        if history:
            history_section = self.build_history_section(history)
            parts.append(history_section)
        
        # Ajouter la question
        query_section = self.build_query_section(query)
        parts.append(query_section)
        
        # Ajouter les instructions de formatage
        if include_format_instructions:
            if response_format is None:
                response_format = self.detect_response_format(query)
            
            format_section = self.build_format_instructions(response_format)
            parts.append(format_section)
        
        return "\n\n".join(parts)
    
    def build_title_prompt(self, query: str) -> str:
        """
        Construit le prompt pour générer un titre de conversation.
        
        Args:
            query: Question initiale de l'utilisateur
        
        Returns:
            Prompt pour la génération de titre
        """
        return TITLE_GENERATION_PROMPT.format(query=query[:200])


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def chunks_to_prompt_format(
    chunks: List[Dict[str, Any]]
) -> List[ChunkForPrompt]:
    """
    Convertit une liste de chunks (dict) en ChunkForPrompt.
    
    Args:
        chunks: Liste de dictionnaires de chunks
    
    Returns:
        Liste de ChunkForPrompt
    """
    result = []
    
    for chunk in chunks:
        # Extraire la date si disponible dans les métadonnées
        metadata = chunk.get("metadata", {})
        date = metadata.get("upload_date") or metadata.get("date")
        
        result.append(ChunkForPrompt(
            document_id=chunk.get("document_id", ""),
            title=chunk.get("document_title", chunk.get("title", "Document sans titre")),
            category=chunk.get("category_name", chunk.get("category", "")),
            page=chunk.get("page_number", chunk.get("page", 0)),
            text=chunk.get("text", ""),
            score=chunk.get("score", chunk.get("relevance_score", 0.0)),
            date=date,
            reference=chunk.get("reference")
        ))
    
    return result


def messages_to_history_format(
    messages: List[Dict[str, Any]]
) -> List[HistoryMessage]:
    """
    Convertit une liste de messages (dict) en HistoryMessage.
    
    Args:
        messages: Liste de dictionnaires de messages
    
    Returns:
        Liste de HistoryMessage
    """
    result = []
    
    for msg in messages:
        role = msg.get("role", "user")
        if hasattr(role, "value"):  # Si c'est un enum
            role = role.value
        
        result.append(HistoryMessage(
            role=role,
            content=msg.get("content", "")
        ))
    
    return result


def get_format_for_query(query: str) -> ResponseFormat:
    """
    Détermine le meilleur format de réponse pour une question.
    
    Args:
        query: Question de l'utilisateur
    
    Returns:
        ResponseFormat approprié
    """
    builder = get_prompt_builder()
    return builder.detect_response_format(query)


# =============================================================================
# INSTANCE SINGLETON
# =============================================================================

_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """
    Retourne une instance singleton du PromptBuilder.
    
    Returns:
        Instance PromptBuilder
    """
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder


def create_prompt_builder(**kwargs) -> PromptBuilder:
    """
    Factory function pour créer un PromptBuilder personnalisé.
    
    Args:
        **kwargs: Arguments pour PromptBuilder
    
    Returns:
        Nouvelle instance PromptBuilder
    """
    return PromptBuilder(**kwargs)