"""Initial migration - Create all tables

Revision ID: c42dca1179ea
Revises: 
Create Date: 2025-11-21 11:43:09.506829

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c42dca1179ea'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('matricule', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('nom', sa.String(100), nullable=False),
        sa.Column('prenom', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'MANAGER', 'USER', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('last_login', sa.DateTime, nullable=True),
        sa.Column('reset_token', sa.String(255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime, nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_matricule', 'users', ['matricule'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_categories_id', 'categories', ['id'])
    op.create_index('ix_categories_name', 'categories', ['name'])
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_extension', sa.String(10), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='documentstatus'), nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('total_pages', sa.Integer, nullable=True),
        sa.Column('total_chunks', sa.Integer, nullable=False, default=0),
        sa.Column('extracted_text_length', sa.Integer, nullable=True),
        sa.Column('document_metadata', postgresql.JSONB, nullable=True),
        sa.Column('extraction_time_seconds', sa.Float, nullable=True),
        sa.Column('chunking_time_seconds', sa.Float, nullable=True),
        sa.Column('embedding_time_seconds', sa.Float, nullable=True),
        sa.Column('total_processing_time_seconds', sa.Float, nullable=True),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_documents_id', 'documents', ['id'])
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    
    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('weaviate_id', sa.String(255), nullable=False, unique=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('token_count', sa.Integer, nullable=False),
        sa.Column('char_count', sa.Integer, nullable=False),
        sa.Column('page_number', sa.Integer, nullable=True),
        sa.Column('start_char', sa.Integer, nullable=True),
        sa.Column('end_char', sa.Integer, nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB, nullable=True),
        sa.Column('embedding_model', sa.String(50), nullable=True),
        sa.Column('embedding_time_seconds', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('indexed_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_chunks_id', 'chunks', ['id'])
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('ix_chunks_weaviate_id', 'chunks', ['weaviate_id'])
    
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('is_archived', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('archived_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_is_archived', 'conversations', ['is_archived'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sources', postgresql.JSONB, nullable=True),
        sa.Column('token_count_input', sa.Integer, nullable=True),
        sa.Column('token_count_output', sa.Integer, nullable=True),
        sa.Column('token_count_total', sa.Integer, nullable=True),
        sa.Column('cost_usd', sa.Float, nullable=True),
        sa.Column('cost_xaf', sa.Float, nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('cache_hit', sa.Boolean, nullable=False, default=False),
        sa.Column('cache_key', sa.String(255), nullable=True),
        sa.Column('response_time_seconds', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_messages_id', 'messages', ['id'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    op.create_index('ix_messages_cache_key', 'messages', ['cache_key'])
    
    # Create feedbacks table
    op.create_table(
        'feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Enum('THUMBS_UP', 'THUMBS_DOWN', name='feedbackrating'), nullable=False),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_feedbacks_id', 'feedbacks', ['id'])
    op.create_index('ix_feedbacks_user_id', 'feedbacks', ['user_id'])
    op.create_index('ix_feedbacks_conversation_id', 'feedbacks', ['conversation_id'])
    op.create_index('ix_feedbacks_message_id', 'feedbacks', ['message_id'])
    op.create_index('ix_feedbacks_created_at', 'feedbacks', ['created_at'])
    
    # Create token_usages table
    op.create_table(
        'token_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('operation_type', sa.Enum('EMBEDDING', 'RERANKING', 'TITLE_GENERATION', 'RESPONSE_GENERATION', name='operationtype'), nullable=False),
        sa.Column('model_name', sa.String(50), nullable=False),
        sa.Column('token_count_input', sa.Integer, nullable=True),
        sa.Column('token_count_output', sa.Integer, nullable=True),
        sa.Column('token_count_total', sa.Integer, nullable=False),
        sa.Column('cost_usd', sa.Float, nullable=False),
        sa.Column('cost_xaf', sa.Float, nullable=False),
        sa.Column('exchange_rate', sa.Float, nullable=False),
        sa.Column('token_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_token_usages_id', 'token_usages', ['id'])
    op.create_index('ix_token_usages_operation_type', 'token_usages', ['operation_type'])
    op.create_index('ix_token_usages_created_at', 'token_usages', ['created_at'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # Create system_configs table
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_system_configs_id', 'system_configs', ['id'])
    op.create_index('ix_system_configs_key', 'system_configs', ['key'])


def downgrade() -> None:
    op.drop_table('system_configs')
    op.drop_table('audit_logs')
    op.drop_table('token_usages')
    op.drop_table('feedbacks')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('categories')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS feedbackrating')
    op.execute('DROP TYPE IF EXISTS operationtype')
