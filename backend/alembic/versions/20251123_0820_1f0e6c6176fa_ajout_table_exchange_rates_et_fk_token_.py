"""Ajout table exchange_rates et FK token_usages

Revision ID: 1f0e6c6176fa
Revises: e1688699ad21
Create Date: 2025-11-23 08:20:49.391516

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1f0e6c6176fa'
down_revision = 'e1688699ad21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # 1. Créer la table exchange_rates
    # ========================================
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('currency_from', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('currency_to', sa.String(3), nullable=False, server_default='XAF'),
        sa.Column('rate', sa.Numeric(20, 6), nullable=False),
        sa.Column('fetched_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Index primaire
    op.create_index('ix_exchange_rates_id', 'exchange_rates', ['id'])
    
    # Index composite pour recherche du dernier taux par paire de devises
    op.create_index(
        'ix_exchange_rates_currencies_fetched', 
        'exchange_rates', 
        ['currency_from', 'currency_to', 'fetched_at']
    )
    
    # ========================================
    # 2. Ajouter les FK à token_usages
    # ========================================
    
    # Ajouter colonne user_id
    op.add_column(
        'token_usages',
        sa.Column(
            'user_id', 
            postgresql.UUID(as_uuid=True), 
            nullable=True
        )
    )
    
    # Ajouter colonne document_id
    op.add_column(
        'token_usages',
        sa.Column(
            'document_id', 
            postgresql.UUID(as_uuid=True), 
            nullable=True
        )
    )
    
    # Ajouter colonne message_id
    op.add_column(
        'token_usages',
        sa.Column(
            'message_id', 
            postgresql.UUID(as_uuid=True), 
            nullable=True
        )
    )
    
    # Créer les contraintes FK
    op.create_foreign_key(
        'fk_token_usages_user_id',
        'token_usages',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_token_usages_document_id',
        'token_usages',
        'documents',
        ['document_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_token_usages_message_id',
        'token_usages',
        'messages',
        ['message_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Créer les index pour les nouvelles colonnes
    op.create_index('ix_token_usages_user_id', 'token_usages', ['user_id'])
    op.create_index('ix_token_usages_document_id', 'token_usages', ['document_id'])
    op.create_index('ix_token_usages_message_id', 'token_usages', ['message_id'])
    
    # ========================================
    # 3. Ajouter OCR au type OperationType
    # ========================================
    # Note: PostgreSQL ENUM nécessite ALTER TYPE pour ajouter une valeur
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'OCR'")


def downgrade() -> None:
    # ========================================
    # 1. Supprimer les FK et colonnes de token_usages
    # ========================================
    
    # Supprimer les index
    op.drop_index('ix_token_usages_message_id', table_name='token_usages')
    op.drop_index('ix_token_usages_document_id', table_name='token_usages')
    op.drop_index('ix_token_usages_user_id', table_name='token_usages')
    
    # Supprimer les FK
    op.drop_constraint('fk_token_usages_message_id', 'token_usages', type_='foreignkey')
    op.drop_constraint('fk_token_usages_document_id', 'token_usages', type_='foreignkey')
    op.drop_constraint('fk_token_usages_user_id', 'token_usages', type_='foreignkey')
    
    # Supprimer les colonnes
    op.drop_column('token_usages', 'message_id')
    op.drop_column('token_usages', 'document_id')
    op.drop_column('token_usages', 'user_id')
    
    # ========================================
    # 2. Supprimer la table exchange_rates
    # ========================================
    op.drop_index('ix_exchange_rates_currencies_fetched', table_name='exchange_rates')
    op.drop_index('ix_exchange_rates_id', table_name='exchange_rates')
    op.drop_table('exchange_rates')
    
    # Note: On ne peut pas supprimer une valeur d'ENUM en PostgreSQL facilement
    # Le type OCR restera dans l'enum après downgrade
