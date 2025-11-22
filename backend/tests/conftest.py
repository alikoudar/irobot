"""Pytest configuration and fixtures."""
import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy import TypeDecorator, String

from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.models.user import User
from app.models.category import Category
from app.core.security import get_password_hash, create_access_token


# ============================================================================
# UUID SUPPORT FOR SQLITE
# ============================================================================

# Forcer SQLite à accepter les foreign keys
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key support for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine (SQLite in-memory)."""
    # Utiliser SQLite avec support UUID as string
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with overridden database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def admin_user(db_session):
    """Create admin user for testing."""
    # Générer un UUID réel mais le stocker en string pour SQLite
    user_uuid = uuid.uuid4()
    
    user = User(
        matricule="ADMIN001",
        email="admin@test.com",
        nom="Admin",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="ADMIN",
        is_active=True,
        is_verified=True
    )
    # Ne pas définir l'ID manuellement, laisser SQLAlchemy le générer
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session):
    """Create manager user for testing."""
    user = User(
        matricule="MGR001",
        email="manager@test.com",
        nom="Manager",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="MANAGER",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """Create regular user for testing."""
    user = User(
        matricule="USR001",
        email="user@test.com",
        nom="User",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="USER",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# AUTH FIXTURES
# ============================================================================

@pytest.fixture
def admin_token(admin_user):
    """Create access token for admin user."""
    token_data = {
        "sub": str(admin_user.id),
        "matricule": admin_user.matricule,
        "role": admin_user.role
    }
    return create_access_token(token_data)


@pytest.fixture
def admin_headers(admin_token):
    """Create authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_token(manager_user):
    """Create access token for manager user."""
    token_data = {
        "sub": str(manager_user.id),
        "matricule": manager_user.matricule,
        "role": manager_user.role
    }
    return create_access_token(token_data)


@pytest.fixture
def manager_headers(manager_token):
    """Create authorization headers for manager user."""
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture
def user_token(regular_user):
    """Create access token for regular user."""
    token_data = {
        "sub": str(regular_user.id),
        "matricule": regular_user.matricule,
        "role": regular_user.role
    }
    return create_access_token(token_data)


@pytest.fixture
def user_headers(user_token):
    """Create authorization headers for regular user."""
    return {"Authorization": f"Bearer {user_token}"}


# ============================================================================
# CATEGORY FIXTURES (pour tests futurs)
# ============================================================================

@pytest.fixture
def test_category(db_session):
    """Create test category."""
    category = Category(
        name="Test Category",
        description="A test category",
        color="#FF0000"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


# ============================================================================
# PYTEST MARKERS
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "users: User management tests")