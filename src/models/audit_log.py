from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid

class AuditAction(PyEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    PASSWORD_CHANGED = "password_changed"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_ACTIVATED = "account_activated"
    
    # 2FA related
    TOTP_ENABLED = "totp_enabled"
    TOTP_DISABLED = "totp_disabled"
    TOTP_VERIFIED = "totp_verified"
    TOTP_FAILED = "totp_failed"
    
    # File operations
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_VIEWED = "file_viewed"
    FILE_DELETED = "file_deleted"
    
    # Case operations
    CASE_CREATED = "case_created"
    CASE_UPDATED = "case_updated"
    CASE_SUBMITTED = "case_submitted"
    CASE_STATUS_CHANGED = "case_status_changed"
    CASE_ASSIGNED = "case_assigned"
    CASE_VIEWED = "case_viewed"
    
    # Data operations
    DEBT_ADDED = "debt_added"
    DEBT_UPDATED = "debt_updated"
    DEBT_DELETED = "debt_deleted"
    ASSET_ADDED = "asset_added"
    ASSET_UPDATED = "asset_updated"
    ASSET_DELETED = "asset_deleted"
    INCOME_ADDED = "income_added"
    INCOME_UPDATED = "income_updated"
    INCOME_DELETED = "income_deleted"
    EXPENDITURE_ADDED = "expenditure_added"
    EXPENDITURE_UPDATED = "expenditure_updated"
    EXPENDITURE_DELETED = "expenditure_deleted"
    
    # Admin operations
    USER_INVITED = "user_invited"
    USER_ROLE_CHANGED = "user_role_changed"
    SUPERUSER_ACCESS_GRANTED = "superuser_access_granted"
    SUPERUSER_ACCESS_REVOKED = "superuser_access_revoked"
    
    # System operations
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    SYSTEM_MAINTENANCE = "system_maintenance"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Who performed the action
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Can be null for system actions
    office_id = Column(String, ForeignKey("offices.id"), nullable=True)  # Can be null for superusers
    
    # What action was performed
    action = Column(String(50), nullable=False)  # Temporarily use String instead of Enum to avoid validation issues
    resource_type = Column(String(50), nullable=True)  # e.g., "case", "user", "file"
    resource_id = Column(String, nullable=True)  # ID of the resource that was affected
    
    # Context information
    description = Column(Text, nullable=True)  # Human-readable description
    details = Column(JSON, nullable=True)  # Additional structured data
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)
    
    # Result information
    success = Column(String, nullable=False, default=True)  # Boolean as string for compatibility
    error_message = Column(Text, nullable=True)
    response_status = Column(String, nullable=True)
    
    # File-specific information (when action involves files)
    file_id = Column(String, ForeignKey("file_uploads.id"), nullable=True)
    filename = Column(String(255), nullable=True)
    
    # Case-specific information
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_ms = Column(String, nullable=True)  # How long the action took
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    office = relationship("Office", back_populates="audit_logs")
    file = relationship("FileUpload")
    case = relationship("Case")
    
    @property
    def formatted_timestamp(self):
        """Get formatted timestamp for display"""
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    @property
    def action_display(self):
        """Get human-readable action name"""
        display_names = {
            AuditAction.LOGIN: "User Login",
            AuditAction.LOGOUT: "User Logout",
            AuditAction.LOGIN_FAILED: "Login Failed",
            AuditAction.PASSWORD_RESET_REQUESTED: "Password Reset Requested",
            AuditAction.PASSWORD_RESET_COMPLETED: "Password Reset Completed",
            AuditAction.PASSWORD_CHANGED: "Password Changed",
            AuditAction.ACCOUNT_LOCKED: "Account Locked",
            AuditAction.ACCOUNT_UNLOCKED: "Account Unlocked",
            AuditAction.ACCOUNT_CREATED: "Account Created",
            AuditAction.ACCOUNT_UPDATED: "Account Updated",
            AuditAction.ACCOUNT_DELETED: "Account Deleted",
            AuditAction.ACCOUNT_SUSPENDED: "Account Suspended",
            AuditAction.ACCOUNT_ACTIVATED: "Account Activated",
            AuditAction.TOTP_ENABLED: "2FA Enabled",
            AuditAction.TOTP_DISABLED: "2FA Disabled",
            AuditAction.TOTP_VERIFIED: "2FA Verified",
            AuditAction.TOTP_FAILED: "2FA Failed",
            AuditAction.FILE_UPLOADED: "File Uploaded",
            AuditAction.FILE_DOWNLOADED: "File Downloaded",
            AuditAction.FILE_VIEWED: "File Viewed",
            AuditAction.FILE_DELETED: "File Deleted",
            AuditAction.CASE_CREATED: "Case Created",
            AuditAction.CASE_UPDATED: "Case Updated",
            AuditAction.CASE_SUBMITTED: "Case Submitted",
            AuditAction.CASE_STATUS_CHANGED: "Case Status Changed",
            AuditAction.CASE_ASSIGNED: "Case Assigned",
            AuditAction.CASE_VIEWED: "Case Viewed",
            AuditAction.USER_INVITED: "User Invited",
            AuditAction.USER_ROLE_CHANGED: "User Role Changed",
            AuditAction.SUPERUSER_ACCESS_GRANTED: "Superuser Access Granted",
            AuditAction.SUPERUSER_ACCESS_REVOKED: "Superuser Access Revoked",
            AuditAction.DATA_EXPORT: "Data Export",
            AuditAction.DATA_IMPORT: "Data Import"
        }
        return display_names.get(self.action, self.action.replace('_', ' ').title())
    
    @property
    def is_security_event(self):
        """Check if this is a security-related event"""
        security_actions = [
            AuditAction.LOGIN_FAILED, AuditAction.ACCOUNT_LOCKED, AuditAction.ACCOUNT_UNLOCKED,
            AuditAction.PASSWORD_RESET_REQUESTED, AuditAction.PASSWORD_RESET_COMPLETED,
            AuditAction.TOTP_FAILED, AuditAction.SUPERUSER_ACCESS_GRANTED,
            AuditAction.SUPERUSER_ACCESS_REVOKED, AuditAction.ACCOUNT_DELETED
        ]
        return self.action in security_actions
    
    @classmethod
    def log_action(cls, session, action, user_id=None, office_id=None, resource_type=None,
                   resource_id=None, description=None, details=None, ip_address=None,
                   user_agent=None, success=True, error_message=None, **kwargs):
        """Helper method to create audit log entries"""
        log_entry = cls(
            user_id=user_id,
            office_id=office_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=str(success),
            error_message=error_message,
            **kwargs
        )
        session.add(log_entry)
        return log_entry
    
    def __repr__(self):
        username = self.user.email if self.user else "System"
        return f"<AuditLog {self.action_display} by {username} at {self.formatted_timestamp}>"
