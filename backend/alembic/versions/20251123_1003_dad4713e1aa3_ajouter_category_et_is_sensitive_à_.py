"""Ajouter category et is_sensitive à system_configs

Revision ID: dad4713e1aa3
Revises: 1f0e6c6176fa
Create Date: 2025-11-23 10:03:31.048184

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dad4713e1aa3'
down_revision = '1f0e6c6176fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajouter les colonnes category et is_sensitive."""
    
    # Ajouter la colonne category
    op.add_column(
        'system_configs',
        sa.Column('category', sa.String(50), nullable=True)
    )
    
    # Ajouter la colonne is_sensitive
    op.add_column(
        'system_configs',
        sa.Column('is_sensitive', sa.Boolean(), nullable=True, default=False)
    )
    
    # Mettre à jour les valeurs par défaut pour les lignes existantes
    op.execute("UPDATE system_configs SET category = 'other' WHERE category IS NULL")
    op.execute("UPDATE system_configs SET is_sensitive = false WHERE is_sensitive IS NULL")
    
    # Rendre les colonnes NOT NULL après avoir défini les valeurs par défaut
    op.alter_column('system_configs', 'category', nullable=False)
    op.alter_column('system_configs', 'is_sensitive', nullable=False)
    
    # Créer un index sur category pour les requêtes par catégorie
    op.create_index('idx_system_configs_category', 'system_configs', ['category'])


def downgrade() -> None:
    """Supprimer les colonnes category et is_sensitive."""
    
    # Supprimer l'index
    op.drop_index('idx_system_configs_category', table_name='system_configs')
    
    # Supprimer les colonnes
    op.drop_column('system_configs', 'is_sensitive')
    op.drop_column('system_configs', 'category')
