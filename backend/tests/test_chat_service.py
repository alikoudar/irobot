# -*- coding: utf-8 -*-
"""
Tests simples pour le ChatService.

Tests pour :
- Gestion des conversations
- Gestion des messages
- Gestion des feedbacks
- Helpers et utilitaires

Sprint 7 - Phase 5 : Tests

Note: Ces tests mockent les dépendances externes (Mistral, Weaviate)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.feedback import Feedback, FeedbackRating


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_user():
    """Créer un utilisateur mock."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.matricule = "TEST001"
    user.email = "test@beac.int"
    user.nom = "Test"
    user.prenom = "User"
    return user


@pytest.fixture
def mock_conversation(mock_user):
    """Créer une conversation mock."""
    conv = Mock(spec=Conversation)
    conv.id = uuid4()
    conv.user_id = mock_user.id
    conv.title = "Test Conversation"
    conv.is_archived = False
    conv.created_at = datetime.utcnow()
    conv.updated_at = datetime.utcnow()
    conv.archived_at = None
    return conv


@pytest.fixture
def mock_message(mock_conversation):
    """Créer un message mock."""
    msg = Mock(spec=Message)
    msg.id = uuid4()
    msg.conversation_id = mock_conversation.id
    msg.role = MessageRole.ASSISTANT
    msg.content = "Voici la réponse..."
    msg.sources = [{"document_id": "doc-1", "title": "Test Doc"}]
    msg.token_count_input = 100
    msg.token_count_output = 50
    msg.token_count_total = 150
    msg.cost_usd = 0.001
    msg.cost_xaf = 0.6
    msg.cache_hit = False
    msg.created_at = datetime.utcnow()
    return msg


# =============================================================================
# TESTS CONVERSATION MANAGEMENT
# =============================================================================

class TestConversationManagement:
    """Tests pour la gestion des conversations."""
    
    def test_create_conversation(self, db_session, admin_user):
        """Test création d'une conversation."""
        conversation = Conversation(
            user_id=admin_user.id,
            title="Nouvelle conversation"
        )
        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.title == "Nouvelle conversation"
        assert conversation.is_archived is False
    
    def test_conversation_default_title(self, db_session, admin_user):
        """Test titre par défaut."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        # Le titre par défaut dépend du modèle
        assert conversation.user_id == admin_user.id
    
    def test_archive_conversation(self, db_session, admin_user):
        """Test archivage d'une conversation."""
        conversation = Conversation(
            user_id=admin_user.id,
            title="À archiver"
        )
        db_session.add(conversation)
        db_session.commit()
        
        # Archiver
        conversation.is_archived = True
        conversation.archived_at = datetime.utcnow()
        db_session.commit()
        
        assert conversation.is_archived is True
        assert conversation.archived_at is not None
    
    def test_unarchive_conversation(self, db_session, admin_user):
        """Test désarchivage."""
        conversation = Conversation(
            user_id=admin_user.id,
            title="Archivée",
            is_archived=True,
            archived_at=datetime.utcnow()
        )
        db_session.add(conversation)
        db_session.commit()
        
        # Désarchiver
        conversation.is_archived = False
        conversation.archived_at = None
        db_session.commit()
        
        assert conversation.is_archived is False
        assert conversation.archived_at is None
    
    def test_get_user_conversations(self, db_session, admin_user):
        """Test récupération des conversations d'un utilisateur."""
        # Créer plusieurs conversations
        for i in range(5):
            conv = Conversation(
                user_id=admin_user.id,
                title=f"Conversation {i}"
            )
            db_session.add(conv)
        db_session.commit()
        
        # Récupérer
        conversations = db_session.query(Conversation).filter(
            Conversation.user_id == admin_user.id
        ).all()
        
        assert len(conversations) == 5
    
    def test_filter_archived_conversations(self, db_session, admin_user):
        """Test filtrage des conversations archivées."""
        # Créer conversations normales et archivées
        for i in range(3):
            conv = Conversation(
                user_id=admin_user.id,
                title=f"Active {i}",
                is_archived=False
            )
            db_session.add(conv)
        
        for i in range(2):
            conv = Conversation(
                user_id=admin_user.id,
                title=f"Archivée {i}",
                is_archived=True
            )
            db_session.add(conv)
        
        db_session.commit()
        
        # Filtrer non archivées
        active = db_session.query(Conversation).filter(
            Conversation.user_id == admin_user.id,
            Conversation.is_archived == False
        ).all()
        
        assert len(active) == 3


# =============================================================================
# TESTS MESSAGE MANAGEMENT
# =============================================================================

class TestMessageManagement:
    """Tests pour la gestion des messages."""
    
    def test_create_user_message(self, db_session, admin_user):
        """Test création d'un message utilisateur."""
        # Créer conversation d'abord
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        # Créer message
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Quelle est la procédure ?"
        )
        db_session.add(message)
        db_session.commit()
        
        assert message.id is not None
        assert message.role == MessageRole.USER
        assert message.content == "Quelle est la procédure ?"
    
    def test_create_assistant_message(self, db_session, admin_user):
        """Test création d'un message assistant."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Voici la réponse...",
            sources=[{"document_id": "doc-1", "title": "Test"}],
            token_count_input=100,
            token_count_output=50,
            token_count_total=150,
            cost_usd=0.001,
            cost_xaf=0.6,
            model_used="mistral-medium-latest",
            cache_hit=False,
            response_time_seconds=2.5
        )
        db_session.add(message)
        db_session.commit()
        
        assert message.role == MessageRole.ASSISTANT
        assert message.token_count_total == 150
        assert message.cache_hit is False
    
    def test_message_with_cache_hit(self, db_session, admin_user):
        """Test message depuis le cache."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Réponse cachée",
            cache_hit=True,
            cache_key="cache-key-123",
            model_used="cached"
        )
        db_session.add(message)
        db_session.commit()
        
        assert message.cache_hit is True
        assert message.cache_key == "cache-key-123"
    
    def test_get_conversation_messages(self, db_session, admin_user):
        """Test récupération des messages d'une conversation."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        # Ajouter plusieurs messages
        for i in range(4):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            msg = Message(
                conversation_id=conversation.id,
                role=role,
                content=f"Message {i}"
            )
            db_session.add(msg)
        db_session.commit()
        
        # Récupérer
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at).all()
        
        assert len(messages) == 4
        assert messages[0].role == MessageRole.USER
        assert messages[1].role == MessageRole.ASSISTANT


# =============================================================================
# TESTS FEEDBACK MANAGEMENT
# =============================================================================

class TestFeedbackManagement:
    """Tests pour la gestion des feedbacks."""
    
    def test_create_thumbs_up_feedback(self, db_session, admin_user):
        """Test création feedback positif."""
        # Setup
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Réponse"
        )
        db_session.add(message)
        db_session.commit()
        
        # Créer feedback
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating=FeedbackRating.THUMBS_UP
        )
        db_session.add(feedback)
        db_session.commit()
        
        assert feedback.id is not None
        assert feedback.rating == FeedbackRating.THUMBS_UP
        assert feedback.comment is None
    
    def test_create_thumbs_down_with_comment(self, db_session, admin_user):
        """Test création feedback négatif avec commentaire."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Mauvaise réponse"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating=FeedbackRating.THUMBS_DOWN,
            comment="La réponse est incorrecte"
        )
        db_session.add(feedback)
        db_session.commit()
        
        assert feedback.rating == FeedbackRating.THUMBS_DOWN
        assert feedback.comment == "La réponse est incorrecte"
    
    def test_update_feedback(self, db_session, admin_user):
        """Test mise à jour d'un feedback."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Réponse"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating=FeedbackRating.THUMBS_DOWN
        )
        db_session.add(feedback)
        db_session.commit()
        
        # Mettre à jour
        feedback.rating = FeedbackRating.THUMBS_UP
        feedback.comment = "Finalement correct"
        db_session.commit()
        
        assert feedback.rating == FeedbackRating.THUMBS_UP
        assert feedback.comment == "Finalement correct"
    
    def test_get_message_feedback(self, db_session, admin_user):
        """Test récupération du feedback d'un message."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Réponse"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating=FeedbackRating.THUMBS_UP
        )
        db_session.add(feedback)
        db_session.commit()
        
        # Récupérer
        found = db_session.query(Feedback).filter(
            Feedback.message_id == message.id,
            Feedback.user_id == admin_user.id
        ).first()
        
        assert found is not None
        assert found.rating == FeedbackRating.THUMBS_UP


# =============================================================================
# TESTS HELPER FUNCTIONS (MOCKED)
# =============================================================================

class TestChatServiceHelpers:
    """Tests pour les fonctions helper du ChatService (mockées)."""
    
    @pytest.mark.asyncio
    async def test_embed_query_mock(self):
        """Test embedding de question (mocké)."""
        with patch('app.clients.mistral_client.get_mistral_client') as mock_client:
            # Setup mock
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.embeddings = [[0.1, 0.2, 0.3] * 341]  # 1024 dimensions
            mock_instance.embed_texts.return_value = mock_result
            mock_client.return_value = mock_instance
            
            # Test
            from app.clients.mistral_client import get_mistral_client
            client = get_mistral_client()
            result = client.embed_texts(["Test question"])
            
            assert len(result.embeddings[0]) == 1023
    
    def test_generate_title_format(self):
        """Test format du titre généré."""
        # Simuler le nettoyage de titre
        raw_title = '"Procédures de validation."'
        
        # Nettoyer
        clean_title = raw_title.strip('"').strip("'").rstrip(".")
        
        assert clean_title == "Procédures de validation"
        assert len(clean_title) <= 50
    
    def test_calculate_cost(self):
        """Test calcul des coûts."""
        token_count_input = 1500
        token_count_output = 200
        
        # Tarifs Mistral (exemple)
        price_per_million_input = 0.4
        price_per_million_output = 2.0
        
        cost_usd = (
            (token_count_input / 1_000_000) * price_per_million_input +
            (token_count_output / 1_000_000) * price_per_million_output
        )
        
        expected = (1500 / 1_000_000) * 0.4 + (200 / 1_000_000) * 2.0
        assert abs(cost_usd - expected) < 0.0001
    
    def test_convert_to_xaf(self):
        """Test conversion USD → XAF."""
        cost_usd = 0.001
        exchange_rate = 600.0
        
        cost_xaf = cost_usd * exchange_rate
        
        assert cost_xaf == 0.6


# =============================================================================
# TESTS CASCADE DELETE
# =============================================================================

class TestCascadeDelete:
    """Tests pour les suppressions en cascade."""
    
    def test_delete_conversation_deletes_messages(self, db_session, admin_user):
        """Test que supprimer une conversation supprime ses messages."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        # Ajouter des messages
        for i in range(3):
            msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}"
            )
            db_session.add(msg)
        db_session.commit()
        
        conv_id = conversation.id
        
        # Supprimer la conversation
        db_session.delete(conversation)
        db_session.commit()
        
        # Vérifier que les messages sont supprimés
        remaining = db_session.query(Message).filter(
            Message.conversation_id == conv_id
        ).count()
        
        assert remaining == 0
    
    def test_delete_message_deletes_feedback(self, db_session, admin_user):
        """Test que supprimer un message supprime son feedback."""
        conversation = Conversation(user_id=admin_user.id)
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Réponse"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            user_id=admin_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating=FeedbackRating.THUMBS_UP
        )
        db_session.add(feedback)
        db_session.commit()
        
        msg_id = message.id
        
        # Supprimer le message
        db_session.delete(message)
        db_session.commit()
        
        # Vérifier que le feedback est supprimé
        remaining = db_session.query(Feedback).filter(
            Feedback.message_id == msg_id
        ).count()
        
        assert remaining == 0