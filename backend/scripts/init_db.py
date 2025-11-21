"""Script to initialize database with admin user."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import uuid

def init_db():
    """Initialize database with tables and admin user."""
    print("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created")
    
    # Create admin user
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()

        print("FOUND ADMIN:", admin)
        
        if not admin:
            print("Creating default admin user...")
            admin = User(
                id=uuid.uuid4(),
                matricule="ADMIN001",
                email="admin@beac.int",
                nom="Admin",
                prenom="System",
                hashed_password=get_password_hash("Admin123!"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            db.commit()
            print("✅ Admin user created")
            print(f"   Matricule: ADMIN001")
            print(f"   Email: admin@beac.int")
            print(f"   Password: Admin123!")
        else:
            print("✅ Admin user already exists")
    
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n✅ Database initialization complete!")

if __name__ == "__main__":
    init_db()