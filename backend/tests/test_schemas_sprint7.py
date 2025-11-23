# -*- coding: utf-8 -*-
"""
Tests simples pour les schemas Sprint 7.

Tests pour :
- ConversationSchemas
- MessageSchemas
- FeedbackSchemas

Sprint 7 - Phase 5 : Tests
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from pydantic import ValidationError

from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationArchive,
    ConversationResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationSearchParams,
)
from app.schemas.message import (
    ChatRequest,
    ChatStreamStartEvent,
    ChatStreamTokenEvent,
    ChatStreamSourcesEvent,
    ChatStreamMetadataEvent,
    ChatStreamEndEvent,
    ChatStreamErrorEvent,
    SourceReference,
    MessageResponse,
)
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackRatingEnum,
    FeedbackStats,
)


# =============================================================================
# TESTS CONVERSATION SCHEMAS
# =============================================================================

class TestConversationSchemas:
    """Tests pour les schemas de conversation."""
    
    def test_conversation_create_default(self):
        """Test création avec valeurs par défaut."""
        schema = ConversationCreate()
        assert schema.title is None
    
    def test_conversation_create_with_title(self):
        """Test création avec titre."""
        schema = ConversationCreate(title="Ma conversation")
        assert schema.title == "Ma conversation"
    
    def test_conversation_create_title_max_length(self):
        """Test que le titre respecte la longueur max."""
        long_title = "x" * 300
        with pytest.raises(ValidationError):
            ConversationCreate(title=long_title)
    
    def test_conversation_update_partial(self):
        """Test mise à jour partielle."""
        schema = ConversationUpdate(title="Nouveau titre")
        assert schema.title == "Nouveau titre"
        assert schema.is_archived is None
    
    def test_conversation_update_archive(self):
        """Test mise à jour archivage."""
        schema = ConversationUpdate(is_archived=True)
        assert schema.is_archived is True
        assert schema.title is None
    
    def test_conversation_archive_required(self):
        """Test que is_archived est requis."""
        with pytest.raises(ValidationError):
            ConversationArchive()
    
    def test_conversation_archive_valid(self):
        """Test archivage valide."""
        schema = ConversationArchive(is_archived=True)
        assert schema.is_archived is True
    
    def test_conversation_response_from_dict(self):
        """Test création depuis un dict."""
        data = {
            "id": uuid4(),
            "user_id": uuid4(),
            "title": "Test conversation",
            "is_archived": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        schema = ConversationResponse(**data)
        assert schema.title == "Test conversation"
        assert schema.is_archived is False
    
    def test_conversation_response_optional_fields(self):
        """Test champs optionnels."""
        data = {
            "id": uuid4(),
            "user_id": uuid4(),
            "title": "Test",
            "is_archived": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 5,
            "last_message_at": datetime.utcnow(),
        }
        schema = ConversationResponse(**data)
        assert schema.message_count == 5
        assert schema.last_message_at is not None
    
    def test_conversation_list_response(self):
        """Test liste de conversations."""
        conv = ConversationResponse(
            id=uuid4(),
            user_id=uuid4(),
            title="Test",
            is_archived=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        schema = ConversationListResponse(
            conversations=[conv],
            total=1,
            page=1,
            page_size=20,
            has_more=False
        )
        assert len(schema.conversations) == 1
        assert schema.total == 1
        assert schema.has_more is False
    
    def test_conversation_summary(self):
        """Test résumé de conversation."""
        schema = ConversationSummary(
            id=uuid4(),
            title="Discussion BEAC",
            is_archived=False,
            updated_at=datetime.utcnow(),
            message_count=10,
            last_message_preview="Voici la réponse..."
        )
        assert schema.message_count == 10
        assert "réponse" in schema.last_message_preview
    
    def test_conversation_search_params_defaults(self):
        """Test paramètres de recherche par défaut."""
        schema = ConversationSearchParams()
        assert schema.page == 1
        assert schema.page_size == 20
        assert schema.search_query is None
        assert schema.is_archived is None
    
    def test_conversation_search_params_with_filters(self):
        """Test paramètres de recherche avec filtres."""
        schema = ConversationSearchParams(
            search_query="circulaire",
            is_archived=False,
            page=2,
            page_size=50
        )
        assert schema.search_query == "circulaire"
        assert schema.page == 2
        assert schema.page_size == 50


# =============================================================================
# TESTS MESSAGE SCHEMAS
# =============================================================================

class TestMessageSchemas:
    """Tests pour les schemas de message."""
    
    def test_chat_request_simple(self):
        """Test requête chat simple."""
        schema = ChatRequest(message="Quelle est la procédure ?")
        assert schema.message == "Quelle est la procédure ?"
        assert schema.conversation_id is None
    
    def test_chat_request_with_conversation(self):
        """Test requête chat avec conversation existante."""
        conv_id = uuid4()
        schema = ChatRequest(
            message="Suite de ma question",
            conversation_id=conv_id
        )
        assert schema.conversation_id == conv_id
    
    def test_chat_request_empty_message(self):
        """Test que le message ne peut pas être vide."""
        with pytest.raises(ValidationError):
            ChatRequest(message="")
    
    def test_source_reference(self):
        """Test référence de source."""
        schema = SourceReference(
            document_id="doc-123",
            title="Circulaire N°001/2024",
            category="Lettres Circulaires",
            page=5,
            relevance_score=0.95
        )
        assert schema.document_id == "doc-123"
        assert schema.relevance_score == 0.95
    
    def test_source_reference_minimal(self):
        """Test référence de source minimale."""
        schema = SourceReference(
            document_id="doc-123",
            title="Document test"
        )
        assert schema.category is None
        assert schema.page is None
    
    def test_stream_start_event(self):
        """Test événement de début de stream."""
        conv_id = uuid4()
        msg_id = uuid4()
        schema = ChatStreamStartEvent(
            conversation_id=conv_id,
            message_id=msg_id,
            is_new_conversation=True
        )
        assert schema.conversation_id == conv_id
        assert schema.is_new_conversation is True
    
    def test_stream_token_event(self):
        """Test événement de token."""
        schema = ChatStreamTokenEvent(content="Voici ")
        assert schema.content == "Voici "
    
    def test_stream_sources_event(self):
        """Test événement de sources."""
        sources = [
            SourceReference(document_id="1", title="Doc 1"),
            SourceReference(document_id="2", title="Doc 2"),
        ]
        schema = ChatStreamSourcesEvent(sources=sources)
        assert len(schema.sources) == 2
    
    def test_stream_metadata_event(self):
        """Test événement de métadonnées."""
        schema = ChatStreamMetadataEvent(
            token_count_input=1500,
            token_count_output=200,
            cost_usd=0.002,
            cost_xaf=1.2,
            cache_hit=False,
            response_time_seconds=2.5,
            model_used="mistral-medium-latest"
        )
        assert schema.token_count_input == 1500
        assert schema.cache_hit is False
        assert schema.model_used == "mistral-medium-latest"
    
    def test_stream_end_event(self):
        """Test événement de fin."""
        msg_id = uuid4()
        schema = ChatStreamEndEvent(message_id=msg_id)
        assert schema.message_id == msg_id
    
    def test_stream_error_event(self):
        """Test événement d'erreur."""
        schema = ChatStreamErrorEvent(
            error="Erreur de connexion",
            code="CONNECTION_ERROR"
        )
        assert schema.error == "Erreur de connexion"
        assert schema.code == "CONNECTION_ERROR"


# =============================================================================
# TESTS FEEDBACK SCHEMAS
# =============================================================================

class TestFeedbackSchemas:
    """Tests pour les schemas de feedback."""
    
    def test_feedback_rating_enum(self):
        """Test enum des ratings."""
        assert FeedbackRatingEnum.THUMBS_UP.value == "THUMBS_UP"
        assert FeedbackRatingEnum.THUMBS_DOWN.value == "THUMBS_DOWN"
    
    def test_feedback_create_thumbs_up(self):
        """Test création feedback positif."""
        msg_id = uuid4()
        schema = FeedbackCreate(
            message_id=msg_id,
            rating=FeedbackRatingEnum.THUMBS_UP
        )
        assert schema.rating == FeedbackRatingEnum.THUMBS_UP
        assert schema.comment is None
    
    def test_feedback_create_with_comment(self):
        """Test création feedback avec commentaire."""
        msg_id = uuid4()
        schema = FeedbackCreate(
            message_id=msg_id,
            rating=FeedbackRatingEnum.THUMBS_DOWN,
            comment="Réponse incorrecte"
        )
        assert schema.rating == FeedbackRatingEnum.THUMBS_DOWN
        assert schema.comment == "Réponse incorrecte"
    
    def test_feedback_update(self):
        """Test mise à jour feedback."""
        schema = FeedbackUpdate(
            rating=FeedbackRatingEnum.THUMBS_UP,
            comment="Finalement correct"
        )
        assert schema.rating == FeedbackRatingEnum.THUMBS_UP
    
    def test_feedback_response(self):
        """Test réponse feedback."""
        schema = FeedbackResponse(
            id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            message_id=uuid4(),
            rating=FeedbackRatingEnum.THUMBS_UP,
            comment=None,
            created_at=datetime.utcnow()
        )
        assert schema.rating == FeedbackRatingEnum.THUMBS_UP
    
    def test_feedback_stats(self):
        """Test statistiques feedback."""
        schema = FeedbackStats(
            total_feedbacks=100,
            thumbs_up_count=80,
            thumbs_down_count=20,
            satisfaction_rate=80.0,
            feedbacks_with_comments=15
        )
        assert schema.total_feedbacks == 100
        assert schema.satisfaction_rate == 80.0
        assert schema.feedbacks_with_comments == 15


# =============================================================================
# TESTS VALIDATION
# =============================================================================

class TestSchemaValidation:
    """Tests de validation des schemas."""
    
    def test_uuid_validation(self):
        """Test validation UUID."""
        with pytest.raises(ValidationError):
            ChatRequest(
                message="Test",
                conversation_id="not-a-uuid"
            )
    
    def test_page_size_max(self):
        """Test limite max de page_size."""
        with pytest.raises(ValidationError):
            ConversationSearchParams(page_size=200)
    
    def test_page_min(self):
        """Test limite min de page."""
        with pytest.raises(ValidationError):
            ConversationSearchParams(page=0)
    
    def test_feedback_comment_optional(self):
        """Test que le commentaire est optionnel."""
        schema = FeedbackCreate(
            message_id=uuid4(),
            rating=FeedbackRatingEnum.THUMBS_UP
        )
        assert schema.comment is None