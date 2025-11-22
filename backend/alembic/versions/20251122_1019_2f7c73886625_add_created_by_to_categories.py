"""Add created_by to categories

Revision ID: 2f7c73886625
Revises: c42dca1179ea
Create Date: 2025-11-22 10:19:25.154909

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '2f7c73886625'
down_revision = 'c42dca1179ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add created_by column to categories table."""
    # Add created_by column
    op.add_column('categories', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create foreign key
    op.create_foreign_key(
        'fk_categories_created_by_users',
        'categories',
        'users',
        ['created_by'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index on created_by
    op.create_index(
        'ix_categories_created_by',
        'categories',
        ['created_by']
    )


def downgrade() -> None:
    """Remove created_by column from categories table."""
    # Drop index
    op.drop_index('ix_categories_created_by', table_name='categories')
    
    # Drop foreign key
    op.drop_constraint('fk_categories_created_by_users', 'categories', type_='foreignkey')
    
    # Drop column
    op.drop_column('categories', 'created_by')