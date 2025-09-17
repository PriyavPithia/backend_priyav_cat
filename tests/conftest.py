"""
Test configuration and fixtures for the CA Tadley Debt Tool backend tests.
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import your app and database models
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from database import get_db, Base
from config.settings import Settings

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    """Create a test database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Create a test client with database dependency override."""
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
def test_settings():
    """Test settings with safe defaults."""
    return Settings(
        secret_key="test-secret-key",
        debug=True,
        database_url=SQLALCHEMY_DATABASE_URL,
        allowed_origins=["http://localhost:3000", "http://localhost:5173"]
    )
