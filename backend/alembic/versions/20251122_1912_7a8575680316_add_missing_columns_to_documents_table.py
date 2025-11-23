"""Add missing columns to documents table

Revision ID: 7a8575680316
Revises: 2f7c73886625
Create Date: 2025-11-22 19:12:18.662755

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7a8575680316'
down_revision = '2f7c73886625'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema."""
    
    # 1. Créer l'enum ProcessingStage
    processing_stage_enum = postgresql.ENUM(
        'VALIDATION',
        'EXTRACTION',
        'CHUNKING',
        'EMBEDDING',
        'INDEXING',
        name='processingstage',
        create_type=True
    )
    processing_stage_enum.create(op.get_bind(), checkfirst=True)
    
    # 2. Ajouter la colonne file_hash
    op.add_column(
        'documents',
        sa.Column('file_hash', sa.String(64), nullable=True)
    )
    
    # 3. Ajouter la colonne processing_stage
    op.add_column(
        'documents',
        sa.Column(
            'processing_stage',
            sa.Enum('VALIDATION', 'EXTRACTION', 'CHUNKING', 'EMBEDDING', 'INDEXING', name='processingstage'),
            nullable=True
        )
    )
    
    # 4. Ajouter la colonne retry_count
    op.add_column(
        'documents',
        sa.Column('retry_count', sa.Integer, nullable=True, default=0)
    )
    
    # 5. Mettre à jour les valeurs par défaut pour les documents existants
    op.execute("UPDATE documents SET file_hash = '' WHERE file_hash IS NULL")
    op.execute("UPDATE documents SET retry_count = 0 WHERE retry_count IS NULL")
    
    # 6. Rendre file_hash non nullable après avoir mis à jour les valeurs
    op.alter_column('documents', 'file_hash', nullable=False)
    op.alter_column('documents', 'retry_count', nullable=False)
    
    # 7. Créer les index
    op.create_index('ix_documents_file_hash', 'documents', ['file_hash'])
    op.create_index('ix_documents_processing_stage', 'documents', ['processing_stage'])


def downgrade():
    """Downgrade database schema."""
    
    # 1. Supprimer les index
    op.drop_index('ix_documents_processing_stage', table_name='documents')
    op.drop_index('ix_documents_file_hash', table_name='documents')
    
    # 2. Supprimer les colonnes
    op.drop_column('documents', 'retry_count')
    op.drop_column('documents', 'processing_stage')
    op.drop_column('documents', 'file_hash')
    
    # 3. Supprimer l'enum ProcessingStage
    processing_stage_enum = postgresql.ENUM(
        'VALIDATION',
        'EXTRACTION',
        'CHUNKING',
        'EMBEDDING',
        'INDEXING',
        name='processingstage'
    )
    processing_stage_enum.drop(op.get_bind(), checkfirst=True)