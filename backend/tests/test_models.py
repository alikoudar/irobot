"""Tests for database models."""
import pytest
from datetime import datetime

from app.models import (
    User, UserRole,
    Category,
    Document, DocumentStatus,
    Conversation,
    Message, MessageRole,
    Feedback, FeedbackRating,
)


class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self, db_session):
        """Test creating a user."""
        from app.core.security import get_password_hash
        
        user = User(
            id="00000000-0000-0000-0000-000000000100",
            matricule="TEST001",
            email="test@example.com",
            nom="Doe",
            prenom="John",
            hashed_password=get_password_hash("password123"),
            role="USER",
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.matricule == "TEST001"
        assert user.email == "test@example.com"
        assert user.role == "USER"
        assert user.is_active is True
        assert user.is_verified is False
    
    def test_user_full_name(self, admin_user):
        """Test user full_name property."""
        assert admin_user.full_name == "Test Admin"
    
    def test_user_repr(self, admin_user):
        """Test user __repr__."""
        repr_str = repr(admin_user)
        assert "ADMIN001" in repr_str
        assert "Test Admin" in repr_str
    
    def test_user_unique_matricule(self, db_session, admin_user):
        """Test that matricule must be unique."""
        from app.core.security import get_password_hash
        
        duplicate_user = User(
            id="00000000-0000-0000-0000-000000000100",
            matricule="ADMIN001",  # Same as admin_user
            email="different@test.com",
            nom="Doe",
            prenom="Jane",
            hashed_password=get_password_hash("password123"),
            role="USER"
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestCategoryModel:
    """Tests for Category model."""
    
    def test_create_category(self, db_session):
        """Test creating a category."""
        category = Category(
            id="00000000-0000-0000-0000-000000000100",
            name="Documents Officiels",
            description="Documents officiels de la BEAC",
            color="#005ca9"
        )
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        
        assert category.id is not None
        assert category.name == "Documents Officiels"
        assert category.color == "#005ca9"
    
    def test_category_repr(self, test_category):
        """Test category __repr__."""
        repr_str = repr(test_category)
        assert "Test Category" in repr_str
    
    def test_category_unique_name(self, db_session, test_category):
        """Test that category name must be unique."""
        duplicate_category = Category(
            id="00000000-0000-0000-0000-000000000100",
            name="Test Category",  # Same as test_category
            description="Another category"
        )
        db_session.add(duplicate_category)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestDocumentModel:
    """Tests for Document model."""
    
    def test_create_document(self, db_session, admin_user, test_category):
        """Test creating a document."""
        document = Document(
            id="00000000-0000-0000-0000-000000000100",
            category_id=test_category.id,
            uploaded_by=admin_user.id,
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            file_extension="pdf",
            status="PENDING"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.id is not None
        assert document.original_filename == "test.pdf"
        assert document.status == "PENDING"
        assert document.category_id == test_category.id
        assert document.uploaded_by == admin_user.id
    
    def test_document_repr(self, db_session, admin_user):
        """Test document __repr__."""
        document = Document(
            id="00000000-0000-0000-0000-000000000100",
            uploaded_by=admin_user.id,
            original_filename="rapport.pdf",
            file_path="/uploads/rapport.pdf",
            file_size_bytes=2048,
            mime_type="application/pdf",
            file_extension="pdf",
            status="COMPLETED"
        )
        db_session.add(document)
        db_session.commit()
        
        repr_str = repr(document)
        assert "rapport.pdf" in repr_str
        assert "COMPLETED" in repr_str


class TestConversationModel:
    """Tests for Conversation model."""
    
    def test_create_conversation(self, db_session, regular_user):
        """Test creating a conversation."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Ma première question",
            is_archived=False
        )
        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.title == "Ma première question"
        assert conversation.is_archived is False
        assert conversation.user_id == regular_user.id
    
    def test_conversation_repr(self, db_session, regular_user):
        """Test conversation __repr__."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Test Conversation"
        )
        db_session.add(conversation)
        db_session.commit()
        
        repr_str = repr(conversation)
        assert "Test Conversation" in repr_str


class TestMessageModel:
    """Tests for Message model."""
    
    def test_create_user_message(self, db_session, regular_user):
        """Test creating a user message."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Test"
        )
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            id="00000000-0000-0000-0000-000000000100",
            conversation_id=conversation.id,
            role="USER",
            content="Quelle est la politique monétaire ?"
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        
        assert message.id is not None
        assert message.role == "USER"
        assert message.content == "Quelle est la politique monétaire ?"
        assert message.cache_hit is False
    
    def test_create_assistant_message_with_sources(self, db_session, regular_user):
        """Test creating an assistant message with sources."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Test"
        )
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            id="00000000-0000-0000-0000-000000000100",
            conversation_id=conversation.id,
            role="ASSISTANT",
            content="Voici la réponse...",
            sources={"chunks": ["chunk-1", "chunk-2"]},
            token_count_input=100,
            token_count_output=200,
            token_count_total=300,
            cost_usd=0.01,
            cost_xaf=6.0,
            model_used="mistral-medium",
            cache_hit=True,
            response_time_seconds=1.5
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        
        assert message.role == "ASSISTANT"
        assert message.sources == {"chunks": ["chunk-1", "chunk-2"]}
        assert message.token_count_total == 300
        assert message.cache_hit is True


class TestFeedbackModel:
    """Tests for Feedback model."""
    
    def test_create_positive_feedback(self, db_session, regular_user):
        """Test creating positive feedback."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Test"
        )
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            id="00000000-0000-0000-0000-000000000100",
            conversation_id=conversation.id,
            role="ASSISTANT",
            content="Test response"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating="THUMBS_UP",
            comment="Très bonne réponse !"
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)
        
        assert feedback.id is not None
        assert feedback.rating == "THUMBS_UP"
        assert feedback.comment == "Très bonne réponse !"
    
    def test_create_negative_feedback(self, db_session, regular_user):
        """Test creating negative feedback."""
        conversation = Conversation(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            title="Test"
        )
        db_session.add(conversation)
        db_session.commit()
        
        message = Message(
            id="00000000-0000-0000-0000-000000000100",
            conversation_id=conversation.id,
            role="ASSISTANT",
            content="Test response"
        )
        db_session.add(message)
        db_session.commit()
        
        feedback = Feedback(
            id="00000000-0000-0000-0000-000000000100",
            user_id=regular_user.id,
            conversation_id=conversation.id,
            message_id=message.id,
            rating="THUMBS_DOWN",
            comment="Réponse imprécise"
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)
        
        assert feedback.rating == "THUMBS_DOWN"
        assert feedback.comment == "Réponse imprécise"