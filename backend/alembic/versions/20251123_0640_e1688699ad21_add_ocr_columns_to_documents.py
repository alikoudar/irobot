"""Add_ocr_columns_to_documents

Revision ID: e1688699ad21
Revises: 7a8575680316
Create Date: 2025-11-23 06:40:50.700853

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1688699ad21'
down_revision = '7a8575680316'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajout des colonnes OCR (si pas déjà présentes).
    
    Colonnes ajoutées :
    - has_images: BOOLEAN DEFAULT FALSE
    - image_count: INTEGER DEFAULT 0
    - ocr_completed: BOOLEAN DEFAULT FALSE
    - extraction_method: VARCHAR(20) DEFAULT 'TEXT'
    """
    # Vérifier et ajouter has_images
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'has_images'
            ) THEN
                ALTER TABLE documents ADD COLUMN has_images BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;
        END $$;
    """)
    
    # Vérifier et ajouter image_count
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'image_count'
            ) THEN
                ALTER TABLE documents ADD COLUMN image_count INTEGER DEFAULT 0 NOT NULL;
            END IF;
        END $$;
    """)
    
    # Vérifier et ajouter ocr_completed
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'ocr_completed'
            ) THEN
                ALTER TABLE documents ADD COLUMN ocr_completed BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;
        END $$;
    """)
    
    # Vérifier et ajouter extraction_method
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'extraction_method'
            ) THEN
                ALTER TABLE documents ADD COLUMN extraction_method VARCHAR(20) DEFAULT 'TEXT' NOT NULL;
            END IF;
        END $$;
    """)
    
    # Créer les index s'ils n'existent pas
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_extraction_method 
        ON documents(extraction_method);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_has_images 
        ON documents(has_images);
    """)


def downgrade() -> None:
    """Retirer les colonnes OCR."""
    # Supprimer les index
    op.execute("DROP INDEX IF EXISTS ix_documents_has_images;")
    op.execute("DROP INDEX IF EXISTS ix_documents_extraction_method;")
    
    # Supprimer les colonnes
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS extraction_method;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS ocr_completed;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS image_count;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS has_images;")