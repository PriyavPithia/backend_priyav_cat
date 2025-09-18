from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class UserRole(PyEnum):
    CLIENT = "client"
    ADVISER = "adviser" 
    SUPERUSER = "superuser"

class UserStatus(PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Client-specific fields
    ca_client_number = Column(String(50), nullable=True)  # For clients only
    
    # Additional contact details (mainly for clients)
    title = Column(String(10), nullable=True)
    home_phone = Column(String(50), nullable=True)
    mobile_phone = Column(String(50), nullable=True)
    home_address = Column(Text, nullable=True)
    postcode = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)  # Store as string for flexibility
    gender = Column(String(50), nullable=True)
    
    # Optional demographic information
    ethnicity = Column(String(100), nullable=True)
    ethnicity_prefer_not_to_say = Column(Boolean, default=False)
    nationality = Column(String(100), nullable=True)
    nationality_prefer_not_to_say = Column(Boolean, default=False)
    preferred_language = Column(String(100), nullable=True)
    preferred_language_prefer_not_to_say = Column(Boolean, default=False)
    religion = Column(String(100), nullable=True)
    religion_prefer_not_to_say = Column(Boolean, default=False)
    gender_identity = Column(String(100), nullable=True)
    gender_identity_prefer_not_to_say = Column(Boolean, default=False)
    sexual_orientation = Column(String(100), nullable=True)
    sexual_orientation_prefer_not_to_say = Column(Boolean, default=False)
    disability_status = Column(String(100), nullable=True)
    marital_status = Column(String(50), nullable=True)
    marital_status_prefer_not_to_say = Column(Boolean, default=False)
    household_type = Column(String(100), nullable=True)
    household_type_prefer_not_to_say = Column(Boolean, default=False)
    occupation = Column(String(100), nullable=True)
    occupation_prefer_not_to_say = Column(Boolean, default=False)
    housing_tenure = Column(String(100), nullable=True)
    housing_tenure_prefer_not_to_say = Column(Boolean, default=False)
    
    # Optional information tracking
    optional_info_completed = Column(Boolean, default=False)
    optional_info_skipped = Column(Boolean, default=False)
    optional_info_never_show = Column(Boolean, default=False)
    
    # Role and status
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING_VERIFICATION)
    
    # Office admin rights (for advisers to manage users in their office)
    is_office_admin = Column(Boolean, default=False)
    
    # Office association (multi-tenant)
    # Superusers don't need to be assigned to an office (nullable=True)
    office_id = Column(String, ForeignKey("offices.id"), nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    first_failed_attempt = Column(DateTime, nullable=True)  # Track when first failed attempt occurred
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    
    # Two-Factor Authentication
    totp_secret = Column(String(32), nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Invitation system
    invitation_token = Column(String, nullable=True, unique=True)
    invitation_expires_at = Column(DateTime, nullable=True)
    invited_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    invitation_details = Column(Text, nullable=True)  # JSON string of additional details for prefilling
    
    # User preferences (JSON string)
    preferences = Column(Text, nullable=True, default='{}')
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    office = relationship("Office", back_populates="users")
    invited_by = relationship("User", remote_side=[id], backref="invitations")
    cases = relationship("Case", back_populates="client", foreign_keys="Case.client_id")
    managed_cases = relationship("Case", back_populates="assigned_adviser", foreign_keys="Case.assigned_adviser_id")
    
    def get_preferences(self):
        """Get user preferences as a dictionary"""
        import json
        if not self.preferences:
            return {}
        try:
            return json.loads(self.preferences)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_preferences(self, preferences_dict):
        """Set user preferences from a dictionary"""
        import json
        self.preferences = json.dumps(preferences_dict)
    
    def update_preferences(self, preferences_dict):
        """Update user preferences, merging with existing ones"""
        current_prefs = self.get_preferences()
        current_prefs.update(preferences_dict)
        self.set_preferences(current_prefs)
    audit_logs = relationship("AuditLog", back_populates="user")
    client_details = relationship("ClientDetails", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    @property
    def is_client(self):
        return self.role == UserRole.CLIENT
    
    @property
    def is_adviser(self):
        return self.role == UserRole.ADVISER
    
    @property
    def is_superuser(self):
        return self.role == UserRole.SUPERUSER
    
    @property
    def is_admin(self):
        return self.role in [UserRole.ADVISER, UserRole.SUPERUSER]
    
    @property
    def can_manage_users(self):
        """Check if user can manage other users (superuser or office admin)"""
        return self.is_superuser or (self.is_adviser and self.is_office_admin)
    
    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
