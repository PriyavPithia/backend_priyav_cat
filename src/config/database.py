from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import settings

# Normalize DATABASE_URL for Postgres on managed platforms (e.g., Railway)
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://") and "+" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Create database engine with robust pooling
is_sqlite = "sqlite" in database_url
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True,
    pool_recycle=1800,  # recycle connections every 30 minutes
    pool_size=10 if not is_sqlite else 5,
    max_overflow=20 if not is_sqlite else 10,
    pool_timeout=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base model class
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
