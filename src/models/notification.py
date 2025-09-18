from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class NotificationType(PyEnum):
    CASE_CLOSED = "case_closed"
    CASE_UPDATED = "case_updated"
    CASE_ASSIGNED = "case_assigned"
    MENTION = "mention"
    SYSTEM = "system"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Recipient
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related case (if applicable)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    
    # Additional data
    data = Column(JSON, nullable=True)  # Store additional structured data
    
    # Read status
    read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    case = relationship("Case")
    
    def __repr__(self):
        return f"<Notification {self.id}: {self.type.value} for {self.user_id}>"
