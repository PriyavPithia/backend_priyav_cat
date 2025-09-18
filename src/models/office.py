from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..config.database import Base
import uuid

class Office(Base):
    __tablename__ = "offices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)  # e.g., "Citizens Advice Tadley"
    code = Column(String(10), unique=True, nullable=True)  # e.g., "CAT"
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # New field for default office

    auto_logout_minutes = Column(String, default="30")
    max_login_attempts = Column(String, default="5")
    
    # Privacy statement and terms
    privacy_statement_url = Column(String(500), nullable=True)
    terms_url = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="office", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="office", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="office", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Office {self.code}: {self.name}>"
