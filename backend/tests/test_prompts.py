# -*- coding: utf-8 -*-
"""
Tests simples pour le module prompts.

Tests pour :
- SYSTEM_PROMPT_BASE
- PromptBuilder
- ResponseFormat detection
- Conversion des chunks et historique

Sprint 7 - Phase 5 : Tests
"""

import pytest

from app.rag.prompts import (
    SYSTEM_PROMPT_BASE,
    CONTEXT_HEADER,
    HISTORY_HEADER,
    QUERY_HEADER,
    NO_CONTEXT_RESPONSE,
    TITLE_GENERATION_PROMPT,
    FORMAT_INSTRUCTIONS,
    ResponseFormat,
    ChunkForPrompt,
    HistoryMessage,
    PromptBuilder,
    chunks_to_prompt_format,
    messages_to_history_format,
    get_format_for_query,
    get_prompt_builder,
)


# =============================================================================
# TESTS CONSTANTES
# =============================================================================

class TestPromptConstants:
    """Tests pour les constantes de prompts."""
    
    def test_system_prompt_exists(self):
        """Test que le prompt système existe."""
        assert SYSTEM_PROMPT_BASE is not None
        assert len(SYSTEM_PROMPT_BASE) > 100
    
    def test_system_prompt_contains_beac(self):
        """Test que le prompt mentionne la BEAC."""
        assert "BEAC" in SYSTEM_PROMPT_BASE
    
    def test_system_prompt_contains_rules(self):
        """Test que le prompt contient les règles."""
        assert "RÈGLES STRICTES" in SYSTEM_PROMPT_BASE
        assert "UNIQUEMENT" in SYSTEM_PROMPT_BASE
    
    def test_system_prompt_contains_citation_format(self):
        """Test format de citation."""
        assert "[Document" in SYSTEM_PROMPT_BASE
    
    def test_system_prompt_contains_code_formatting(self):
        """Test instructions de formatage code."""
        assert "```" in SYSTEM_PROMPT_BASE
        assert "bash" in SYSTEM_PROMPT_BASE or "python" in SYSTEM_PROMPT_BASE
    
    def test_context_header_exists(self):
        """Test header de contexte."""
        assert "CONTEXTE" in CONTEXT_HEADER
        assert "📚" in CONTEXT_HEADER
    
    def test_history_header_exists(self):
        """Test header d'historique."""
        assert "HISTORIQUE" in HISTORY_HEADER
        assert "💬" in HISTORY_HEADER
    
    def test_query_header_exists(self):
        """Test header de question."""
        assert "QUESTION" in QUERY_HEADER
        assert "❓" in QUERY_HEADER
    
    def test_no_context_response(self):
        """Test réponse sans contexte."""
        assert "ne trouve pas" in NO_CONTEXT_RESPONSE
        assert "reformuler" in NO_CONTEXT_RESPONSE
    
    def test_title_generation_prompt(self):
        """Test prompt de génération de titre."""
        assert "titre" in TITLE_GENERATION_PROMPT.lower()
        assert "50" in TITLE_GENERATION_PROMPT
        assert "{query}" in TITLE_GENERATION_PROMPT


# =============================================================================
# TESTS RESPONSE FORMAT
# =============================================================================

class TestResponseFormat:
    """Tests pour l'enum ResponseFormat."""
    
    def test_response_format_values(self):
        """Test valeurs de l'enum."""
        assert ResponseFormat.DEFAULT.value == "default"
        assert ResponseFormat.TABLE.value == "table"
        assert ResponseFormat.LIST.value == "list"
        assert ResponseFormat.CODE.value == "code"
        assert ResponseFormat.CHRONOLOGICAL.value == "chronological"
        assert ResponseFormat.STEP_BY_STEP.value == "step_by_step"
    
    def test_format_instructions_exist(self):
        """Test que les instructions existent pour chaque format."""
        for format_type in ResponseFormat:
            assert format_type in FORMAT_INSTRUCTIONS
            assert len(FORMAT_INSTRUCTIONS[format_type]) > 10


# =============================================================================
# TESTS DATA CLASSES
# =============================================================================

class TestDataClasses:
    """Tests pour les dataclasses."""
    
    def test_chunk_for_prompt(self):
        """Test création ChunkForPrompt."""
        chunk = ChunkForPrompt(
            document_id="doc-123",
            title="Circulaire N°001",
            category="Lettres Circulaires",
            page=5,
            text="Contenu du document...",
            score=0.95
        )
        assert chunk.document_id == "doc-123"
        assert chunk.score == 0.95
        assert chunk.date is None
    
    def test_chunk_for_prompt_with_date(self):
        """Test ChunkForPrompt avec date."""
        chunk = ChunkForPrompt(
            document_id="doc-123",
            title="Test",
            category="Test",
            page=1,
            text="Test",
            score=0.5,
            date="2024-01-15"
        )
        assert chunk.date == "2024-01-15"
    
    def test_history_message(self):
        """Test création HistoryMessage."""
        msg = HistoryMessage(
            role="user",
            content="Ma question"
        )
        assert msg.role == "user"
        assert msg.content == "Ma question"


# =============================================================================
# TESTS PROMPT BUILDER
# =============================================================================

class TestPromptBuilder:
    """Tests pour la classe PromptBuilder."""
    
    @pytest.fixture
    def builder(self):
        """Créer un PromptBuilder pour les tests."""
        return PromptBuilder(
            max_context_tokens=4000,
            max_history_messages=5,
            max_chunk_length=1500
        )
    
    @pytest.fixture
    def sample_chunks(self):
        """Créer des chunks de test."""
        return [
            ChunkForPrompt(
                document_id="doc-1",
                title="Circulaire N°001/2024",
                category="Lettres Circulaires",
                page=1,
                text="Contenu de la circulaire concernant les procédures...",
                score=0.95,
                date="2024-01-15"
            ),
            ChunkForPrompt(
                document_id="doc-2",
                title="Décision N°024/GR/2018",
                category="Décisions",
                page=3,
                text="La présente décision fixe les modalités...",
                score=0.88
            ),
        ]
    
    @pytest.fixture
    def sample_history(self):
        """Créer un historique de test."""
        return [
            HistoryMessage(role="user", content="Quelle est la procédure ?"),
            HistoryMessage(role="assistant", content="Voici la procédure..."),
        ]
    
    def test_build_system_prompt(self, builder):
        """Test construction du prompt système."""
        system_prompt = builder.build_system_prompt()
        assert system_prompt == SYSTEM_PROMPT_BASE
    
    def test_build_context_section_empty(self, builder):
        """Test section contexte vide."""
        context = builder.build_context_section([])
        assert context == ""
    
    def test_build_context_section(self, builder, sample_chunks):
        """Test construction section contexte."""
        context = builder.build_context_section(sample_chunks)
        
        assert "CONTEXTE DISPONIBLE" in context
        assert "[Document 1]" in context
        assert "[Document 2]" in context
        assert "Circulaire N°001/2024" in context
        assert "Décision N°024/GR/2018" in context
        assert "95%" in context  # Score formaté
    
    def test_build_context_section_truncates_long_text(self, builder):
        """Test que les textes longs sont tronqués."""
        long_text = "x" * 2000
        chunks = [
            ChunkForPrompt(
                document_id="doc-1",
                title="Test",
                category="Test",
                page=1,
                text=long_text,
                score=0.9
            )
        ]
        context = builder.build_context_section(chunks)
        assert "..." in context
        assert len(context) < len(long_text)
    
    def test_build_history_section_empty(self, builder):
        """Test section historique vide."""
        history = builder.build_history_section([])
        assert history == ""
    
    def test_build_history_section(self, builder, sample_history):
        """Test construction section historique."""
        history = builder.build_history_section(sample_history)
        
        assert "HISTORIQUE" in history
        assert "Vous" in history  # User affiché comme "Vous"
        assert "Assistant" in history
        assert "Quelle est la procédure" in history
    
    def test_build_history_limits_messages(self, builder):
        """Test limite du nombre de messages."""
        long_history = [
            HistoryMessage(role="user", content=f"Question {i}")
            for i in range(10)
        ]
        history = builder.build_history_section(long_history)
        
        # Devrait contenir seulement les 5 derniers
        assert "Question 9" in history
        assert "Question 5" in history
        # Les premiers ne devraient pas y être
        assert "Question 0" not in history
    
    def test_build_query_section(self, builder):
        """Test construction section question."""
        query = builder.build_query_section("Quelle est la procédure ?")
        
        assert "QUESTION" in query
        assert "Quelle est la procédure ?" in query
    
    def test_build_full_prompt(self, builder, sample_chunks, sample_history):
        """Test construction prompt complet."""
        prompt = builder.build_full_prompt(
            query="Quelle est la procédure de validation ?",
            chunks=sample_chunks,
            history=sample_history
        )
        
        assert "CONTEXTE DISPONIBLE" in prompt
        assert "HISTORIQUE" in prompt
        assert "QUESTION" in prompt
        assert "procédure de validation" in prompt
        assert "INSTRUCTIONS DE RÉPONSE" in prompt
    
    def test_build_full_prompt_without_history(self, builder, sample_chunks):
        """Test prompt sans historique."""
        prompt = builder.build_full_prompt(
            query="Ma question",
            chunks=sample_chunks,
            history=None
        )
        
        assert "CONTEXTE" in prompt
        assert "HISTORIQUE" not in prompt
        assert "Ma question" in prompt
    
    def test_build_title_prompt(self, builder):
        """Test prompt pour génération de titre."""
        title_prompt = builder.build_title_prompt("Comment valider un document ?")
        
        assert "titre" in title_prompt.lower()
        assert "Comment valider un document" in title_prompt


# =============================================================================
# TESTS FORMAT DETECTION
# =============================================================================

class TestFormatDetection:
    """Tests pour la détection automatique du format."""
    
    @pytest.fixture
    def builder(self):
        return PromptBuilder()
    
    def test_detect_table_format(self, builder):
        """Test détection format tableau."""
        queries = [
            "Compare les procédures A et B",
            "Quelle est la différence entre X et Y",
            "Fais un tableau récapitulatif",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.TABLE, f"Failed for: {query}"
    
    def test_detect_step_by_step_format(self, builder):
        """Test détection format étapes."""
        queries = [
            "Comment faire pour valider un document ?",
            "Quelle est la procédure à suivre ?",
            "Quelles sont les étapes ?",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.STEP_BY_STEP, f"Failed for: {query}"
    
    def test_detect_chronological_format(self, builder):
        """Test détection format chronologique."""
        queries = [
            "Quelle est l'évolution de la réglementation ?",
            "Quelles décisions parlent de ce sujet ?",
            "Donne l'historique des modifications",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.CHRONOLOGICAL, f"Failed for: {query}"
    
    def test_detect_code_format(self, builder):
        """Test détection format code."""
        queries = [
            "Quelle commande bash utiliser ?",
            "Donne le code Python pour cela",
            "Montre-moi le script SQL",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.CODE, f"Failed for: {query}"
    
    def test_detect_list_format(self, builder):
        """Test détection format liste."""
        queries = [
            "Liste les documents requis",
            "Quels sont les prérequis ?",
            "Énumère les conditions",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.LIST, f"Failed for: {query}"
    
    def test_detect_default_format(self, builder):
        """Test format par défaut."""
        queries = [
            "Bonjour",
            "Merci",
            "Que signifie ce terme ?",
        ]
        for query in queries:
            format_type = builder.detect_response_format(query)
            assert format_type == ResponseFormat.DEFAULT, f"Failed for: {query}"


# =============================================================================
# TESTS FONCTIONS UTILITAIRES
# =============================================================================

class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires."""
    
    def test_chunks_to_prompt_format(self):
        """Test conversion chunks dict → ChunkForPrompt."""
        chunks_dict = [
            {
                "document_id": "doc-1",
                "document_title": "Test Document",
                "category_name": "Test Category",
                "page_number": 5,
                "text": "Contenu du document",
                "score": 0.9,
            },
            {
                "document_id": "doc-2",
                "title": "Autre Document",  # Alias
                "category": "Autre",  # Alias
                "page": 1,  # Alias
                "text": "Autre contenu",
                "relevance_score": 0.8,  # Alias
            },
        ]
        
        result = chunks_to_prompt_format(chunks_dict)
        
        assert len(result) == 2
        assert result[0].document_id == "doc-1"
        assert result[0].title == "Test Document"
        assert result[0].score == 0.9
        assert result[1].title == "Autre Document"
        assert result[1].score == 0.8
    
    def test_messages_to_history_format(self):
        """Test conversion messages dict → HistoryMessage."""
        messages_dict = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Réponse 1"},
        ]
        
        result = messages_to_history_format(messages_dict)
        
        assert len(result) == 2
        assert result[0].role == "user"
        assert result[0].content == "Question 1"
        assert result[1].role == "assistant"
    
    def test_get_format_for_query(self):
        """Test fonction raccourci get_format_for_query."""
        format_type = get_format_for_query("Compare A et B")
        assert format_type == ResponseFormat.TABLE
    
    def test_get_prompt_builder_singleton(self):
        """Test que get_prompt_builder retourne un singleton."""
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()
        assert builder1 is builder2