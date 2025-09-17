from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class CaseStatus(PyEnum):
    PENDING = "pending"       # Awaiting more information from client
    SUBMITTED = "submitted"   # Client has submitted, no additional info expected
    CLOSED = "closed"        # Adviser has downloaded info and stored in casebook

class CasePriority(PyEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    URGENT = "URGENT"

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Associations
    client_id = Column(String, ForeignKey("users.id"), nullable=False)
    office_id = Column(String, ForeignKey("offices.id"), nullable=False)
    assigned_adviser_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Status
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING, nullable=False)
    priority = Column(Enum(CasePriority), default=CasePriority.NORMAL, nullable=False)
    
    # Emergency check
    has_debt_emergency = Column(Boolean, nullable=True)
    emergency_acknowledged = Column(Boolean, default=False)
    
    # Progress tracking
    debts_completed = Column(Boolean, default=False)
    assets_completed = Column(Boolean, default=False)
    income_completed = Column(Boolean, default=False)
    expenditure_completed = Column(Boolean, default=False)
    
    # Summary data (calculated)
    total_priority_debt = Column(String, nullable=True)  # Store as string to avoid float precision issues
    total_non_priority_debt = Column(String, nullable=True)
    total_assets_value = Column(String, nullable=True)
    total_monthly_income = Column(String, nullable=True)
    total_monthly_expenditure = Column(String, nullable=True)
    monthly_surplus_deficit = Column(String, nullable=True)
    
    # Additional client information
    additional_notes = Column(Text, nullable=True)
    client_comments = Column(Text, nullable=True)
    
    # Submission tracking
    submitted_at = Column(DateTime, nullable=True)
    last_reminder_sent = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Server-side persisted last visited step (0..5)
    last_step = Column(Integer, nullable=True)
    
    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="cases")
    office = relationship("Office", back_populates="cases")
    assigned_adviser = relationship("User", foreign_keys=[assigned_adviser_id], back_populates="managed_cases")
    
    debts = relationship("Debt", back_populates="case", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="case", cascade="all, delete-orphan")
    incomes = relationship("Income", back_populates="case", cascade="all, delete-orphan")
    expenditures = relationship("Expenditure", back_populates="case", cascade="all, delete-orphan")
    files = relationship("FileUpload", back_populates="case", cascade="all, delete-orphan")
    
    @property
    def completion_percentage(self):
        """Calculate case completion percentage"""
        # Include emergency check as the first step
        completed_sections = sum([
            bool(self.has_debt_emergency is not None),  # Emergency check completed
            bool(self.debts_completed),
            bool(self.assets_completed),
            bool(self.income_completed),
            bool(self.expenditure_completed)
        ])
        return (completed_sections / 5) * 100  # 5 total steps
    
    @property
    def is_complete(self):
        """Check if case is ready for submission"""
        # Assets are optional for submission, but required sections must be complete
        return all([
            bool(self.debts_completed),
            bool(self.income_completed),
            bool(self.expenditure_completed)
        ])
    
    def __repr__(self):
        return f"<Case {self.id} - {self.client.ca_client_number} ({self.status.value})>"
