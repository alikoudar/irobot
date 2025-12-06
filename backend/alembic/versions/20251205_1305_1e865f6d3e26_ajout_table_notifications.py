"""Ajout table notifications

Revision ID: 1e865f6d3e26
Revises: 29ed3953e296
Create Date: 2025-12-05 13:05:04.523665

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1e865f6d3e26'
down_revision = '29ed3953e296'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Créer la table notifications."""
    
    # Supprimer les types ENUM orphelins s'ils existent (cas d'une migration partielle précédente)
    op.execute('DROP TYPE IF EXISTS notificationtype CASCADE')
    op.execute('DROP TYPE IF EXISTS notificationpriority CASCADE')
    
    # Créer la table notifications (les ENUMs sont créés automatiquement par sa.Enum)
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.Enum(
            'DOCUMENT_UPLOADED', 'DOCUMENT_PROCESSING', 'DOCUMENT_COMPLETED', 'DOCUMENT_FAILED',
            'FEEDBACK_RECEIVED', 'FEEDBACK_NEGATIVE',
            'USER_CREATED', 'USER_UPDATED', 'USER_DELETED', 'USER_ACTIVATED', 'USER_DEACTIVATED', 'USER_PASSWORD_RESET',
            'SYSTEM_INFO', 'SYSTEM_WARNING', 'SYSTEM_ERROR', 'STATS_UPDATE',
            name='notificationtype'
        ), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='notificationpriority'), nullable=False, server_default='MEDIUM'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('data', postgresql.JSONB, nullable=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('read_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )
    
    # Créer les index
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_user_unread', 'notifications', ['user_id', 'is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_type_created', 'notifications', ['type', 'created_at'])


def downgrade() -> None:
    """Supprimer la table notifications et les enums."""
    
    op.drop_table('notifications')
    
    # Supprimer les enums
    op.execute('DROP TYPE IF EXISTS notificationpriority')
    op.execute('DROP TYPE IF EXISTS notificationtype')
