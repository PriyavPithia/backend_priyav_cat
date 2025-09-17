from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional

from ..config.database import get_db
from ..models import User, SessionSettings, AuditLog
from .auth import get_current_user

router = APIRouter(prefix="/session-settings", tags=["session-settings"])

# Pydantic models for request/response
class SessionSettingsRequest(BaseModel):
    # Legacy fields for backward compatibility
    session_timeout_seconds: int
    session_warning_seconds: int
    inactivity_threshold_seconds: int
    
    # Role-specific settings
    client_session_timeout_seconds: int
    client_session_warning_seconds: int
    client_inactivity_threshold_seconds: int
    
    adviser_session_timeout_seconds: int
    adviser_session_warning_seconds: int
    adviser_inactivity_threshold_seconds: int
    
    admin_session_timeout_seconds: int
    admin_session_warning_seconds: int
    admin_inactivity_threshold_seconds: int
    
    enable_session_management: bool
    enable_session_debugger: bool
    
    @field_validator(
        'session_timeout_seconds',
        'client_session_timeout_seconds',
        'adviser_session_timeout_seconds',
        'admin_session_timeout_seconds',
        mode='before'
    )
    def validate_timeout_seconds(cls, v):
        v_int = int(v)
        if v_int < 60 or v_int > 7200:  # 1 minute to 2 hours
            raise ValueError('Session timeout must be between 60 and 7200 seconds')
        return v_int

    @field_validator(
        'session_warning_seconds',
        'client_session_warning_seconds',
        'adviser_session_warning_seconds',
        'admin_session_warning_seconds',
        mode='before'
    )
    def validate_warning_seconds(cls, v):
        v_int = int(v)
        if v_int < 10 or v_int > 7200:  # Extended range for role-based settings
            raise ValueError('Session warning must be between 10 and 7200 seconds')
        return v_int

    @field_validator(
        'inactivity_threshold_seconds',
        'client_inactivity_threshold_seconds',
        'adviser_inactivity_threshold_seconds',
        'admin_inactivity_threshold_seconds',
        mode='before'
    )
    def validate_inactivity_threshold(cls, v):
        v_int = int(v)
        if v_int < 5 or v_int > 300:
            raise ValueError('Inactivity threshold must be between 5 and 300 seconds')
        return v_int

class SessionSettingsResponse(BaseModel):
    # Legacy fields for backward compatibility
    session_timeout_seconds: int
    session_warning_seconds: int
    inactivity_threshold_seconds: int
    
    # Role-specific settings
    client_session_timeout_seconds: int
    client_session_warning_seconds: int
    client_inactivity_threshold_seconds: int
    
    adviser_session_timeout_seconds: int
    adviser_session_warning_seconds: int
    adviser_inactivity_threshold_seconds: int
    
    admin_session_timeout_seconds: int
    admin_session_warning_seconds: int
    admin_inactivity_threshold_seconds: int
    
    enable_session_management: bool
    enable_session_debugger: bool
    updated_at: Optional[str]
    updated_by: Optional[str]

class PublicSessionSettingsResponse(BaseModel):
    enable_session_management: bool
    enable_session_debugger: bool
    inactivity_threshold_seconds: int
    session_timeout_seconds: int
    session_warning_seconds: int

def require_superuser_access(current_user: User):
    """Ensure user has superuser access"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )

@router.get("/", response_model=SessionSettingsResponse)
async def get_session_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current session settings"""
    require_superuser_access(current_user)
    
    settings = SessionSettings.get_or_create_default(db)
    return SessionSettingsResponse(**settings.to_dict())

@router.put("/", response_model=SessionSettingsResponse)
async def update_session_settings(
    settings_data: SessionSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update session settings (superuser only)"""
    require_superuser_access(current_user)
    
    settings = SessionSettings.get_or_create_default(db)
    
    # Store old values for audit log
    old_values = settings.to_dict()
    
    # Update settings
    # Legacy fields
    settings.session_timeout_seconds = settings_data.session_timeout_seconds
    settings.session_warning_seconds = settings_data.session_warning_seconds
    settings.inactivity_threshold_seconds = settings_data.inactivity_threshold_seconds
    
    # Role-specific settings
    settings.client_session_timeout_seconds = settings_data.client_session_timeout_seconds
    settings.client_session_warning_seconds = settings_data.client_session_warning_seconds
    settings.client_inactivity_threshold_seconds = settings_data.client_inactivity_threshold_seconds
    
    settings.adviser_session_timeout_seconds = settings_data.adviser_session_timeout_seconds
    settings.adviser_session_warning_seconds = settings_data.adviser_session_warning_seconds
    settings.adviser_inactivity_threshold_seconds = settings_data.adviser_inactivity_threshold_seconds
    
    settings.admin_session_timeout_seconds = settings_data.admin_session_timeout_seconds
    settings.admin_session_warning_seconds = settings_data.admin_session_warning_seconds
    settings.admin_inactivity_threshold_seconds = settings_data.admin_inactivity_threshold_seconds
    
    settings.enable_session_management = settings_data.enable_session_management
    settings.enable_session_debugger = settings_data.enable_session_debugger
    settings.updated_by = current_user.id
    
    try:
        db.commit()
        db.refresh(settings)
        
        # Create audit log
        changes = []
        new_values = settings.to_dict()
        for key, new_value in new_values.items():
            if key in old_values and old_values[key] != new_value:
                changes.append(f"{key}: {old_values[key]} → {new_value}")
        
        AuditLog.log_action(
            db,
            action="session_settings_updated",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Session settings updated by {current_user.email}. Changes: {', '.join(changes)}",
            success=True
        )
        db.commit()
        
        return SessionSettingsResponse(**settings.to_dict())
        
    except Exception as e:
        db.rollback()
        
        # Log failed attempt
        AuditLog.log_action(
            db,
            action="session_settings_update_failed",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Failed to update session settings: {str(e)}",
            success=False
        )
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session settings"
        )

@router.post("/reset", response_model=SessionSettingsResponse)
async def reset_session_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset session settings to defaults (superuser only)"""
    require_superuser_access(current_user)
    
    settings = SessionSettings.get_or_create_default(db)
    
    # Store old values for audit log
    old_values = settings.to_dict()
    
    # Reset to defaults
    # Legacy fields (use client defaults)
    settings.session_timeout_seconds = 420  # 7 minutes (client default)
    settings.session_warning_seconds = 300   # 5 minutes (client default)
    settings.inactivity_threshold_seconds = 120  # 2 minutes (client default)
    
    # Role-specific defaults
    # Clients: 7-minute timeout (2 mins inactivity + 5-min timer)
    settings.client_session_timeout_seconds = 420  # 7 minutes
    settings.client_session_warning_seconds = 300  # 5 minutes warning
    settings.client_inactivity_threshold_seconds = 120  # 2 minutes inactivity
    
    # Advisers: 2.5-minute timeout (30s inactivity + 2-min timer)
    settings.adviser_session_timeout_seconds = 150  # 2.5 minutes
    settings.adviser_session_warning_seconds = 120  # 2 minutes warning
    settings.adviser_inactivity_threshold_seconds = 30  # 30 seconds inactivity
    
    # Admins & Super-admins: 100-second timeout (10s inactivity + 90s timer)
    settings.admin_session_timeout_seconds = 100  # 100 seconds
    settings.admin_session_warning_seconds = 90  # 90 seconds warning
    settings.admin_inactivity_threshold_seconds = 10  # 10 seconds inactivity
    
    settings.enable_session_management = True
    settings.enable_session_debugger = True
    settings.updated_by = current_user.id
    
    try:
        db.commit()
        db.refresh(settings)
        
        # Create audit log
        AuditLog.log_action(
            db,
            action="session_settings_reset",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Session settings reset to defaults by {current_user.email}",
            success=True
        )
        db.commit()
        
        return SessionSettingsResponse(**settings.to_dict())
        
    except Exception as e:
        db.rollback()
        
        # Log failed attempt
        AuditLog.log_action(
            db,
            action="session_settings_reset_failed",
            user_id=current_user.id,
            office_id=current_user.office_id,
            description=f"Failed to reset session settings: {str(e)}",
            success=False
        )
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset session settings"
        )

@router.get("/public", response_model=PublicSessionSettingsResponse)
async def get_public_session_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public session settings for frontend (any authenticated user)"""
    settings = SessionSettings.get_or_create_default(db)
    
    # Get role-specific settings for the current user
    role_settings = settings.get_settings_for_role(current_user.role)
    
    return PublicSessionSettingsResponse(
        enable_session_management=settings.enable_session_management,
        enable_session_debugger=settings.enable_session_debugger if current_user.is_superuser else False,
        inactivity_threshold_seconds=role_settings["inactivity_threshold_seconds"],
        session_timeout_seconds=role_settings["session_timeout_seconds"],
        session_warning_seconds=role_settings["session_warning_seconds"]
    )
