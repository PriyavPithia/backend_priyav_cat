from sqlalchemy import create_engine, event, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import DisconnectionError
from .settings import settings
import logging
import time

logger = logging.getLogger(__name__)

# Create database engine with enhanced connection handling
is_sqlite = "sqlite" in settings.database_url
print(settings.database_url)

# PostgreSQL specific connection args for better stability
postgres_connect_args = {
    "connect_timeout": 10,
    "application_name": "ca_tadley_debt_tool",
    "keepalives_idle": 600,
    "keepalives_interval": 30,
    "keepalives_count": 3,
} if not is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite else postgres_connect_args,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30 minutes
    pool_size=3,  # Smaller pool for SSH tunnel stability
    max_overflow=2,  # Limited overflow for tunnel constraints
    pool_timeout=20,  # Shorter timeout to fail fast
    echo=False,
    poolclass=StaticPool if is_sqlite else None,
)

# Add simple SQLite pragma listener if needed
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance"""
    if is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base model class
Base = declarative_base()

# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
