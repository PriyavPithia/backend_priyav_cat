from sqlalchemy import Column, String, Integer, Boolean, DateTime
from datetime import datetime
from ..config.database import Base

class SessionSettings(Base):
    __tablename__ = "session_settings"
    
    id = Column(String, primary_key=True, default="singleton")  # Single row table
    
    # Client session settings (7-minute timeout: 2 mins inactivity + 5-min timer)
    client_session_timeout_seconds = Column(Integer, default=420, nullable=False)  # 7 minutes
    client_session_warning_seconds = Column(Integer, default=300, nullable=False)  # 5 minutes warning
    client_inactivity_threshold_seconds = Column(Integer, default=120, nullable=False)  # 2 minutes inactivity
    
    # Adviser session settings (2.5-minute timeout: 30s inactivity + 2-min timer)
    adviser_session_timeout_seconds = Column(Integer, default=150, nullable=False)  # 2.5 minutes
    adviser_session_warning_seconds = Column(Integer, default=120, nullable=False)  # 2 minutes warning
    adviser_inactivity_threshold_seconds = Column(Integer, default=30, nullable=False)  # 30 seconds inactivity
    
    # Admin & Super-admin session settings (100-second timeout: 10s inactivity + 90s timer)
    admin_session_timeout_seconds = Column(Integer, default=100, nullable=False)  # 100 seconds
    admin_session_warning_seconds = Column(Integer, default=90, nullable=False)  # 90 seconds warning
    admin_inactivity_threshold_seconds = Column(Integer, default=10, nullable=False)  # 10 seconds inactivity
    
    # Legacy fields for backward compatibility (will use client settings as default)
    session_timeout_seconds = Column(Integer, default=420, nullable=False)  # Default to client settings
    session_warning_seconds = Column(Integer, default=300, nullable=False)  # Default to client settings
    inactivity_threshold_seconds = Column(Integer, default=120, nullable=False)  # Default to client settings
    
    # Feature toggles
    enable_session_management = Column(Boolean, default=True, nullable=False)  # Master toggle
    enable_session_debugger = Column(Boolean, default=True, nullable=False)  # Debug widget toggle
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=True)  # User ID who made the change
    
    def __repr__(self):
        return f"<SessionSettings(timeout={self.session_timeout_minutes}min, debug_enabled={self.enable_debug_mode})>"
    
    @classmethod
    def get_or_create_default(cls, db):
        """Get existing settings or create default settings"""
        try:
            settings = db.query(cls).filter(cls.id == "singleton").first()
            if not settings:
                settings = cls(id="singleton")
                db.add(settings)
                db.commit()
                db.refresh(settings)
            return settings
        except Exception as e:
            # If there's any error (like table doesn't exist), return default settings
            print(f"Error getting session settings: {str(e)}")
            return cls(
                id="singleton",
                session_timeout_minutes=5,
                session_timeout_test_seconds=30,
                session_warning_seconds=60,
                session_warning_test_seconds=10,
                enable_session_management=True,
                enable_session_debugger=True,
                enable_debug_mode=True
            )
    
    def get_settings_for_role(self, user_role):
        """Get session settings for a specific user role"""
        from .user import UserRole
        
        if user_role == UserRole.CLIENT:
            return {
                "session_timeout_seconds": self.client_session_timeout_seconds,
                "session_warning_seconds": self.client_session_warning_seconds,
                "inactivity_threshold_seconds": self.client_inactivity_threshold_seconds
            }
        elif user_role == UserRole.ADVISER:
            return {
                "session_timeout_seconds": self.adviser_session_timeout_seconds,
                "session_warning_seconds": self.adviser_session_warning_seconds,
                "inactivity_threshold_seconds": self.adviser_inactivity_threshold_seconds
            }
        elif user_role == UserRole.SUPERUSER:
            return {
                "session_timeout_seconds": self.admin_session_timeout_seconds,
                "session_warning_seconds": self.admin_session_warning_seconds,
                "inactivity_threshold_seconds": self.admin_inactivity_threshold_seconds
            }
        else:
            # Default to client settings
            return {
                "session_timeout_seconds": self.client_session_timeout_seconds,
                "session_warning_seconds": self.client_session_warning_seconds,
                "inactivity_threshold_seconds": self.client_inactivity_threshold_seconds
            }
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            # Legacy fields (for backward compatibility)
            "session_timeout_seconds": self.session_timeout_seconds,
            "session_warning_seconds": self.session_warning_seconds,
            "inactivity_threshold_seconds": self.inactivity_threshold_seconds,
            
            # Role-specific settings
            "client_session_timeout_seconds": self.client_session_timeout_seconds,
            "client_session_warning_seconds": self.client_session_warning_seconds,
            "client_inactivity_threshold_seconds": self.client_inactivity_threshold_seconds,
            
            "adviser_session_timeout_seconds": self.adviser_session_timeout_seconds,
            "adviser_session_warning_seconds": self.adviser_session_warning_seconds,
            "adviser_inactivity_threshold_seconds": self.adviser_inactivity_threshold_seconds,
            
            "admin_session_timeout_seconds": self.admin_session_timeout_seconds,
            "admin_session_warning_seconds": self.admin_session_warning_seconds,
            "admin_inactivity_threshold_seconds": self.admin_inactivity_threshold_seconds,
            
            # Feature toggles
            "enable_session_management": self.enable_session_management,
            "enable_session_debugger": self.enable_session_debugger,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by
        }
