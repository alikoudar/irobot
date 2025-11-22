"""Script to seed initial categories."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.category import Category
from app.models.user import User, UserRole
import uuid
from datetime import datetime


# Catégories initiales selon le plan de développement
INITIAL_CATEGORIES = [
    {
        "name": "Lettres Circulaires",
        "description": "Lettres circulaires de la BEAC",
        "color": "#005CA9"  # Bleu BEAC
    },
    {
        "name": "Décisions du Gouverneur",
        "description": "Décisions officielles prises par le Gouverneur de la BEAC",
        "color": "#C2A712"  # Or BEAC
    },
    {
        "name": "Procédures et Modes Opératoires",
        "description": "Procédures internes et modes opératoires de la BEAC",
        "color": "#4A90E2"  # Bleu clair
    },
    {
        "name": "Clauses et Conditions Générales",
        "description": "Clauses contractuelles et conditions générales applicables",
        "color": "#50C878"  # Vert émeraude
    }
]


def seed_categories():
    """Seed initial categories into database."""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("SEED DES CATÉGORIES INITIALES")
        print("=" * 70)
        print()
        
        # Get admin user to assign as creator
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        
        if not admin:
            print("❌ ERREUR: Aucun utilisateur admin trouvé!")
            print("   Veuillez d'abord créer un utilisateur admin avec:")
            print("   python scripts/init_db.py")
            return False
        
        print(f"✅ Admin trouvé: {admin.matricule} ({admin.nom} {admin.prenom})")
        print()
        
        # Check existing categories
        existing_categories = db.query(Category).all()
        existing_names = {cat.name for cat in existing_categories}
        
        if existing_names:
            print(f"📋 {len(existing_categories)} catégorie(s) existante(s):")
            for cat in existing_categories:
                print(f"   - {cat.name}")
            print()
        
        # Seed categories
        created_count = 0
        skipped_count = 0
        
        for cat_data in INITIAL_CATEGORIES:
            if cat_data["name"] in existing_names:
                print(f"⏭️  SKIP: '{cat_data['name']}' existe déjà")
                skipped_count += 1
                continue
            
            # Create category
            category = Category(
                id=uuid.uuid4(),
                name=cat_data["name"],
                description=cat_data["description"],
                color=cat_data["color"],
                created_by=admin.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(category)
            print(f"✅ CRÉÉ: '{cat_data['name']}' ({cat_data['color']})")
            created_count += 1
        
        # Commit changes
        if created_count > 0:
            db.commit()
            print()
            print("=" * 70)
            print(f"✅ SUCCÈS: {created_count} catégorie(s) créée(s)")
            if skipped_count > 0:
                print(f"⏭️  {skipped_count} catégorie(s) ignorée(s) (déjà existante(s))")
            print("=" * 70)
        else:
            print()
            print("=" * 70)
            print("ℹ️  Aucune catégorie à créer (toutes existent déjà)")
            print("=" * 70)
        
        # Display final state
        print()
        print("📊 ÉTAT FINAL DES CATÉGORIES:")
        print("-" * 70)
        
        all_categories = db.query(Category).order_by(Category.name).all()
        for i, cat in enumerate(all_categories, 1):
            creator = db.query(User).filter(User.id == cat.created_by).first()
            creator_name = f"{creator.nom} {creator.prenom}" if creator else "N/A"
            print(f"{i}. {cat.name}")
            print(f"   Description: {cat.description}")
            print(f"   Couleur: {cat.color}")
            print(f"   Créé par: {creator_name}")
            print(f"   Date: {cat.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        print("=" * 70)
        print("✅ SEED DES CATÉGORIES TERMINÉ")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERREUR lors du seed: {e}")
        print("=" * 70)
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_categories()
    sys.exit(0 if success else 1)