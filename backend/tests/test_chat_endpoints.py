# -*- coding: utf-8 -*-
"""
Tests simples pour les endpoints Chat API.

Tests pour :
- POST /chat/stream
- POST /chat
- GET /conversations
- GET /conversations/{id}
- DELETE /conversations/{id}
- PUT /conversations/{id}/archive
- POST /messages/{id}/feedback

Sprint 7 - Phase 5 : Tests

Note: Ces tests utilisent des mocks pour les services externes.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.feedback import Feedback, FeedbackRating


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_conversation(db_session, admin_user):
    """Créer une conversation de test."""
    conversation = Conversation(
        user_id=admin_user.id,
        title="Test Conversation"
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


@pytest.fixture
def test_message(db_session, test_conversation):
    """Créer un message de test."""
    message = Message(
        conversation_id=test_conversation.id,
        role=MessageRole.ASSISTANT,
        content="Voici la réponse de test.",
        sources=[{"document_id": "doc-1", "title": "Test Doc"}],
        token_count_input=100,
        token_count_output=50,
        token_count_total=150,
        cache_hit=False
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


@pytest.fixture
def multiple_conversations(db_session, admin_user):
    """Créer plusieurs conversations pour tests de pagination."""
    conversations = []
    for i in range(15):
        conv = Conversation(
            user_id=admin_user.id,
            title=f"Conversation {i}",
            is_archived=(i >= 10)  # 5 archivées
        )
        db_session.add(conv)
        conversations.append(conv)
    db_session.commit()
    return conversations


# =============================================================================
# TESTS LISTE CONVERSATIONS
# =============================================================================

class TestListConversations:
    """Tests pour GET /chat/conversations."""
    
    def test_list_conversations_empty(self, client, admin_headers):
        """Test liste vide."""
        response = client.get(
            "/api/v1/chat/conversations",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0
    
    def test_list_conversations_with_data(
        self, client, admin_headers, multiple_conversations
    ):
        """Test liste avec données."""
        response = client.get(
            "/api/v1/chat/conversations",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Par défaut, exclut les archivées
        assert data["total"] == 10
        assert len(data["conversations"]) <= 20
    
    def test_list_conversations_pagination(
        self, client, admin_headers, multiple_conversations
    ):
        """Test pagination."""
        response = client.get(
            "/api/v1/chat/conversations?page=1&page_size=5",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["conversations"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["has_more"] is True
    
    def test_list_conversations_include_archived(
        self, client, admin_headers, multiple_conversations
    ):
        """Test inclusion des archivées."""
        response = client.get(
            "/api/v1/chat/conversations?include_archived=true",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 15  # Toutes les conversations
    
    def test_list_conversations_unauthorized(self, client):
        """Test accès non autorisé."""
        response = client.get("/api/v1/chat/conversations")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# TESTS GET CONVERSATION
# =============================================================================

class TestGetConversation:
    """Tests pour GET /chat/conversations/{id}."""
    
    def test_get_conversation_success(
        self, client, admin_headers, test_conversation, test_message
    ):
        """Test récupération conversation avec messages."""
        response = client.get(
            f"/api/v1/chat/conversations/{test_conversation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "conversation" in data
        assert "messages" in data
        assert str(data["conversation"]["id"]) == str(test_conversation.id)
        assert len(data["messages"]) == 1
    
    def test_get_conversation_not_found(self, client, admin_headers):
        """Test conversation non trouvée."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_conversation_wrong_user(
        self, client, user_headers, test_conversation
    ):
        """Test accès à une conversation d'un autre utilisateur."""
        # test_conversation appartient à admin_user
        response = client.get(
            f"/api/v1/chat/conversations/{test_conversation.id}",
            headers=user_headers  # regular_user
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS DELETE CONVERSATION
# =============================================================================

class TestDeleteConversation:
    """Tests pour DELETE /chat/conversations/{id}."""
    
    def test_delete_conversation_success(
        self, client, admin_headers, test_conversation, db_session
    ):
        """Test suppression conversation."""
        conv_id = test_conversation.id
        
        response = client.delete(
            f"/api/v1/chat/conversations/{conv_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Vérifier suppression
        deleted = db_session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()
        assert deleted is None
    
    def test_delete_conversation_not_found(self, client, admin_headers):
        """Test suppression conversation inexistante."""
        fake_id = uuid4()
        response = client.delete(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_conversation_wrong_user(
        self, client, user_headers, test_conversation
    ):
        """Test suppression conversation d'un autre utilisateur."""
        response = client.delete(
            f"/api/v1/chat/conversations/{test_conversation.id}",
            headers=user_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS ARCHIVE CONVERSATION
# =============================================================================

class TestArchiveConversation:
    """Tests pour PUT /chat/conversations/{id}/archive."""
    
    def test_archive_conversation(
        self, client, admin_headers, test_conversation
    ):
        """Test archivage conversation."""
        response = client.put(
            f"/api/v1/chat/conversations/{test_conversation.id}/archive",
            headers=admin_headers,
            json={"is_archived": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_archived"] is True
        assert data["archived_at"] is not None
    
    def test_unarchive_conversation(
        self, client, admin_headers, db_session, admin_user
    ):
        """Test désarchivage conversation."""
        # Créer une conversation archivée
        from datetime import datetime
        conv = Conversation(
            user_id=admin_user.id,
            title="Archivée",
            is_archived=True,
            archived_at=datetime.utcnow()
        )
        db_session.add(conv)
        db_session.commit()
        
        response = client.put(
            f"/api/v1/chat/conversations/{conv.id}/archive",
            headers=admin_headers,
            json={"is_archived": False}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["is_archived"] is False
        assert data["archived_at"] is None
    
    def test_archive_not_found(self, client, admin_headers):
        """Test archivage conversation inexistante."""
        fake_id = uuid4()
        response = client.put(
            f"/api/v1/chat/conversations/{fake_id}/archive",
            headers=admin_headers,
            json={"is_archived": True}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS UPDATE CONVERSATION
# =============================================================================

class TestUpdateConversation:
    """Tests pour PATCH /chat/conversations/{id}."""
    
    def test_update_title(
        self, client, admin_headers, test_conversation
    ):
        """Test mise à jour du titre."""
        response = client.patch(
            f"/api/v1/chat/conversations/{test_conversation.id}",
            headers=admin_headers,
            json={"title": "Nouveau titre"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["title"] == "Nouveau titre"
    
    def test_update_partial(
        self, client, admin_headers, test_conversation
    ):
        """Test mise à jour partielle."""
        original_title = test_conversation.title
        
        response = client.patch(
            f"/api/v1/chat/conversations/{test_conversation.id}",
            headers=admin_headers,
            json={"is_archived": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["title"] == original_title
        assert data["is_archived"] is True


# =============================================================================
# TESTS FEEDBACK
# =============================================================================

class TestFeedback:
    """Tests pour les endpoints de feedback."""
    
    def test_add_feedback_thumbs_up(
        self, client, admin_headers, test_message
    ):
        """Test ajout feedback positif."""
        response = client.post(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers,
            json={
                "message_id": str(test_message.id),
                "rating": "thumbs_up"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["rating"] == "thumbs_up"
        assert data["comment"] is None
    
    def test_add_feedback_with_comment(
        self, client, admin_headers, test_message
    ):
        """Test ajout feedback avec commentaire."""
        response = client.post(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers,
            json={
                "message_id": str(test_message.id),
                "rating": "thumbs_down",
                "comment": "Réponse incorrecte"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["rating"] == "thumbs_down"
        assert data["comment"] == "Réponse incorrecte"
    
    def test_update_existing_feedback(
        self, client, admin_headers, test_message, db_session, admin_user, test_conversation
    ):
        """Test mise à jour d'un feedback existant."""
        # Créer un feedback existant
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=test_conversation.id,
            message_id=test_message.id,
            rating=FeedbackRating.THUMBS_DOWN
        )
        db_session.add(feedback)
        db_session.commit()
        
        # Mettre à jour
        response = client.post(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers,
            json={
                "message_id": str(test_message.id),
                "rating": "thumbs_up",
                "comment": "Finalement correct"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["rating"] == "thumbs_up"
        assert data["comment"] == "Finalement correct"
    
    def test_get_feedback(
        self, client, admin_headers, test_message, db_session, admin_user, test_conversation
    ):
        """Test récupération feedback."""
        # Créer un feedback
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=test_conversation.id,
            message_id=test_message.id,
            rating=FeedbackRating.THUMBS_UP
        )
        db_session.add(feedback)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["rating"] == "thumbs_up"
    
    def test_get_feedback_not_found(
        self, client, admin_headers, test_message
    ):
        """Test récupération feedback inexistant."""
        response = client.get(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers
        )
        
        # Devrait retourner null, pas 404
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None
    
    def test_delete_feedback(
        self, client, admin_headers, test_message, db_session, admin_user, test_conversation
    ):
        """Test suppression feedback."""
        # Créer un feedback
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=test_conversation.id,
            message_id=test_message.id,
            rating=FeedbackRating.THUMBS_UP
        )
        db_session.add(feedback)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/chat/messages/{test_message.id}/feedback",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Vérifier suppression
        remaining = db_session.query(Feedback).filter(
            Feedback.message_id == test_message.id
        ).count()
        assert remaining == 0
    
    def test_feedback_message_not_found(self, client, admin_headers):
        """Test feedback sur message inexistant."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/chat/messages/{fake_id}/feedback",
            headers=admin_headers,
            json={
                "message_id": str(fake_id),
                "rating": "thumbs_up"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS CHAT ENDPOINT (MOCKED)
# =============================================================================

class TestChatEndpoint:
    """Tests pour POST /chat (version synchrone, mockée)."""
    
    @patch('app.services.chat_service.get_chat_service')
    def test_chat_sync_mocked(
        self, mock_get_service, client, admin_headers
    ):
        """Test endpoint chat synchrone (mocké)."""
        # Setup mock
        mock_service = Mock()
        
        async def mock_process_query(*args, **kwargs):
            yield {"event": "start", "data": {"conversation_id": str(uuid4()), "message_id": str(uuid4()), "is_new_conversation": True}}
            yield {"event": "token", "data": {"content": "Voici "}}
            yield {"event": "token", "data": {"content": "la réponse."}}
            yield {"event": "metadata", "data": {"token_count_input": 100, "token_count_output": 50, "cost_usd": 0.001, "cost_xaf": 0.6, "cache_hit": False, "response_time_seconds": 1.5, "model_used": "mistral-medium-latest"}}
            yield {"event": "done", "data": {"message_id": str(uuid4())}}
        
        mock_service.process_query_streaming = mock_process_query
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/chat",
            headers=admin_headers,
            json={"message": "Quelle est la procédure ?"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "content" in data
        assert data["content"] == "Voici la réponse."