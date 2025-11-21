"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base
from app.main import app
from app.db.session import get_db
from app.models import User, Category, Document


# Test database URL (in-memory SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Create admin user for testing."""
    from app.core.security import get_password_hash
    
    user = User(
        id="00000000-0000-0000-0000-000000000001",  # String UUID pour SQLite
        matricule="ADMIN001",
        email="admin@test.com",
        nom="Admin",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="admin",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session):
    """Create manager user for testing."""
    from app.core.security import get_password_hash
    
    user = User(
        id="00000000-0000-0000-0000-000000000002",  # String UUID pour SQLite
        matricule="MGR001",
        email="manager@test.com",
        nom="Manager",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="manager",
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
    from app.core.security import get_password_hash
    
    user = User(
        id="00000000-0000-0000-0000-000000000003",  # String UUID pour SQLite
        matricule="USR001",
        email="user@test.com",
        nom="User",
        prenom="Test",
        hashed_password=get_password_hash("TestPassword123!"),
        role="user",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_category(db_session):
    """Create test category."""
    
    category = Category(
        id="00000000-0000-0000-0000-000000000010",  # String UUID pour SQLite
        name="Test Category",
        description="A test category",
        color="#FF0000"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category