"""Script to verify categories and database state."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.category import Category
from app.models.user import User
from app.models.document import Document
from sqlalchemy import func


def verify_categories():
    """Verify categories state in database."""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("VÉRIFICATION DES CATÉGORIES")
        print("=" * 70)
        print()
        
        # Count categories
        total_categories = db.query(func.count(Category.id)).scalar()
        
        if total_categories == 0:
            print("❌ Aucune catégorie trouvée dans la base de données!")
            print()
            print("💡 Pour créer les catégories initiales, exécutez:")
            print("   python scripts/seed_categories.py")
            print("=" * 70)
            return False
        
        print(f"✅ {total_categories} catégorie(s) trouvée(s)")
        print()
        
        # List all categories with stats
        print("📋 LISTE DES CATÉGORIES:")
        print("-" * 70)
        
        categories = db.query(Category).order_by(Category.name).all()
        
        for i, category in enumerate(categories, 1):
            # Get creator info
            creator = None
            if category.created_by:
                creator = db.query(User).filter(User.id == category.created_by).first()
            
            # Count documents in this category
            doc_count = db.query(func.count(Document.id)).filter(
                Document.category_id == category.id
            ).scalar()
            
            print(f"\n{i}. {category.name}")
            print(f"   ID: {category.id}")
            print(f"   Description: {category.description or 'N/A'}")
            print(f"   Couleur: {category.color or 'N/A'}")
            
            if creator:
                print(f"   Créé par: {creator.nom} {creator.prenom} ({creator.matricule})")
            else:
                print(f"   Créé par: N/A")
            
            print(f"   Date création: {category.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Dernière MAJ: {category.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📄 Documents: {doc_count}")
        
        print()
        print("-" * 70)
        
        # Summary statistics
        print()
        print("📊 STATISTIQUES GLOBALES:")
        print("-" * 70)
        print(f"Nombre total de catégories: {total_categories}")
        
        # Categories with/without documents
        categories_with_docs = db.query(Category.id).join(
            Document, Category.id == Document.category_id
        ).distinct().count()
        
        categories_without_docs = total_categories - categories_with_docs
        
        print(f"Catégories avec documents: {categories_with_docs}")
        print(f"Catégories sans documents: {categories_without_docs}")
        
        # Total documents
        total_documents = db.query(func.count(Document.id)).scalar()
        print(f"Nombre total de documents: {total_documents}")
        
        # Documents without category
        docs_without_category = db.query(func.count(Document.id)).filter(
            Document.category_id.is_(None)
        ).scalar()
        
        if docs_without_category > 0:
            print(f"⚠️  Documents sans catégorie: {docs_without_category}")
        
        print()
        print("=" * 70)
        print("✅ VÉRIFICATION TERMINÉE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERREUR lors de la vérification: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


def verify_database_structure():
    """Verify that categories table has all required columns."""
    db = SessionLocal()
    
    try:
        print()
        print("=" * 70)
        print("VÉRIFICATION DE LA STRUCTURE DE LA TABLE CATEGORIES")
        print("=" * 70)
        print()
        
        # Try to query with all expected columns
        from sqlalchemy import inspect
        
        inspector = inspect(db.bind)
        columns = inspector.get_columns('categories')
        
        expected_columns = [
            'id',
            'created_by',
            'name',
            'description',
            'color',
            'created_at',
            'updated_at'
        ]
        
        column_names = [col['name'] for col in columns]
        
        print("📋 Colonnes trouvées:")
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"   - {col['name']}: {col_type} ({nullable})")
        
        print()
        print("🔍 Vérification des colonnes attendues:")
        
        all_present = True
        for expected_col in expected_columns:
            if expected_col in column_names:
                print(f"   ✅ {expected_col}")
            else:
                print(f"   ❌ {expected_col} - MANQUANTE!")
                all_present = False
        
        print()
        
        if all_present:
            print("✅ Structure de la table OK")
        else:
            print("❌ Structure de la table incomplète!")
            print()
            print("💡 Pour mettre à jour la structure, exécutez:")
            print("   alembic upgrade head")
        
        print("=" * 70)
        
        return all_present
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    # Verify database structure
    structure_ok = verify_database_structure()
    
    # Verify categories
    categories_ok = verify_categories()
    
    # Exit with appropriate code
    sys.exit(0 if (structure_ok and categories_ok) else 1)