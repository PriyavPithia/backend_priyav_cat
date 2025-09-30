from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, timedelta
import secrets
from slowapi import Limiter
from slowapi.util import get_remote_address
# CSRF protection removed due to compatibility issues

from ..config.database import get_db
from ..config.settings import settings
from ..config.logging import log_client_setup, get_logger
from ..models import User, Office, AuditLog, UserStatus, UserRole
from ..utils.auth import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, verify_token,
    generate_reset_token, generate_verification_token, generate_invitation_token,
    generate_totp_secret, generate_totp_qr_code, verify_totp_code,
    generate_backup_codes, verify_backup_code,
    is_account_locked, calculate_lockout_time, get_remaining_attempts,
    get_lockout_remaining_time, should_reset_failed_attempts, get_attempts_reset_time, is_valid_email,
    is_session_expired, get_session_remaining_time, get_session_warning_threshold,
    get_client_ip_address
)
from ..services.email_service import (
    send_registration_notice_to_office,
    send_verification_code_email,
    send_verification_code_email_extended,
)

router = APIRouter()
security = HTTPBearer()
logger = get_logger('auth')

# Simple in-memory OTP store for registration flow (debug/staging)
OTP_STORE = {}

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Pydantic models for request/response


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    office_code: Optional[str] = None
    invitation_token: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        validation = validate_password_strength(v)
        if not validation['valid']:
            raise ValueError('; '.join(validation['errors']))
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        validation = validate_password_strength(v)
        if not validation['valid']:
            raise ValueError('; '.join(validation['errors']))
        return v


class Enable2FAResponse(BaseModel):
    qr_code: str
    secret: str
    backup_codes: list


class Verify2FARequest(BaseModel):
    totp_code: str

class VerifyEmailOtpRequest(BaseModel):
    email: EmailStr
    code: str
    otp_session_token: str
    reg_token: Optional[str] = None

class ResendEmailOtpRequest(BaseModel):
    email: EmailStr
    reg_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    status: str
    is_2fa_enabled: bool
    ca_client_number: Optional[str]
    office_id: Optional[str]
    office_code: Optional[str] = None
    office_name: Optional[str]
    is_office_admin: Optional[bool] = False
    created_at: datetime
    # Optional information fields
    ethnicity: Optional[str] = None
    nationality: Optional[str] = None
    preferred_language: Optional[str] = None
    religion: Optional[str] = None
    gender_identity: Optional[str] = None
    sexual_orientation: Optional[str] = None
    disability_status: Optional[str] = None
    marital_status: Optional[str] = None
    household_type: Optional[str] = None
    occupation: Optional[str] = None
    housing_tenure: Optional[str] = None
    optional_info_completed: Optional[bool] = False
    optional_info_skipped: Optional[bool] = False
    optional_info_never_show: Optional[bool] = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# Dependency to get current user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client not found"
        )

    if user.status != UserStatus.ACTIVE:
        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account has been suspended."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )

    # Check if session has expired due to inactivity
    from ..models import SessionSettings
    session_settings = SessionSettings.get_or_create_default(db)

    # Only check session expiry if session management is enabled
    if session_settings.enable_session_management:
        # Use role-based session timeout configuration
        if is_session_expired(user.last_activity, False, db, user.role):
            # Log session expiration
            AuditLog.log_action(
                db,
                action="session_expired",
                user_id=user.id,
                office_id=user.office_id,
                description=f"Session expired due to inactivity for {user.email} (role: {user.role.value})",
                success=False
            )
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity. Please log in again."
            )

    # Update last activity
    user.last_activity = datetime.utcnow()
    db.commit()

    return user


def generate_next_client_number(db: Session) -> str:
    """Generate the next CA client number in format CL-XXXXX or CL-XXXXXX for numbers > 99999"""
    # Get the highest existing client number
    result = db.query(func.max(User.ca_client_number)).filter(
        User.ca_client_number.like('CL-%')
    ).scalar()

    if result is None:
        # No existing client numbers, start with CL-00001
        return "CL-00001"

    # Extract the number part and increment
    try:
        number_part = int(result.split('-')[1])
        next_number = number_part + 1

        # Format based on number size
        if next_number <= 99999:
            # Use 5-digit format for numbers up to 99999
            return f"CL-{next_number:05d}"
        else:
            # Use 6-digit format for numbers 100000 and beyond
            return f"CL-{next_number:06d}"

    except (IndexError, ValueError):
        # If parsing fails, start with CL-00001
        return "CL-00001"


def find_next_available_client_number(db: Session) -> str:
    """Find the next available client number by looking for gaps in the sequence"""
    # Get all existing client numbers and sort them
    existing_numbers = db.query(User.ca_client_number).filter(
        User.ca_client_number.like('CL-%')
    ).all()

    # Extract and sort the numeric parts
    number_list = []
    for row in existing_numbers:
        try:
            number_part = int(row[0].split('-')[1])
            number_list.append(number_part)
        except (IndexError, ValueError):
            continue

    number_list.sort()

    # Find the first gap in the sequence
    expected_number = 1
    for existing_number in number_list:
        if existing_number > expected_number:
            # Found a gap, use this number
            if expected_number <= 99999:
                return f"CL-{expected_number:05d}"
            else:
                return f"CL-{expected_number:06d}"
        expected_number = existing_number + 1

    # If no gaps found, use the next sequential number
    if expected_number <= 99999:
        return f"CL-{expected_number:05d}"
    else:
        return f"CL-{expected_number:06d}"

# Authentication routes


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_register_request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new client account"""

    # If invitation token is provided, validate it and update existing user
    if user_register_request.invitation_token:
        invited_user = db.query(User).filter(
            User.invitation_token == user_register_request.invitation_token,
            User.status == UserStatus.PENDING_VERIFICATION
        ).first()

        if not invited_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation token"
            )

        if invited_user.invitation_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token has expired"
            )

        # Update the invited user with the provided information
        invited_user.email = user_register_request.email
        invited_user.password_hash = hash_password(
            user_register_request.password)
        invited_user.first_name = user_register_request.first_name
        invited_user.last_name = user_register_request.last_name
        invited_user.status = UserStatus.ACTIVE
        invited_user.invitation_token = None  # Clear the token
        invited_user.invitation_expires_at = None

        # Update last_login and last_activity since this is effectively a login
        invited_user.last_login = datetime.utcnow()
        invited_user.last_activity = datetime.utcnow()

        # Create ClientDetails record only for client users
        if invited_user.role.value == "client":
            from ..models.client_details import ClientDetails
            from datetime import date
            existing_client_details = db.query(ClientDetails).filter(
                ClientDetails.user_id == invited_user.id).first()
            if not existing_client_details:
                client_details = ClientDetails(
                    user_id=invited_user.id,
                    first_name=invited_user.first_name or "",
                    surname=invited_user.last_name or "",
                    home_address="",  # Will be filled later
                    postcode="",      # Will be filled later
                    # Temporary placeholder - will be updated later
                    date_of_birth=date(1900, 1, 1),
                    # Set default communication preferences
                    happy_voicemail=True,
                    happy_text_messages=True,
                    preferred_contact_email=True,
                    preferred_contact_mobile=True,
                    preferred_contact_home_phone=False,
                    preferred_contact_address=False,
                    do_not_contact_methods="",
                    agree_to_feedback=True,
                    do_not_contact_feedback_methods=""
                )
                db.add(client_details)

        db.commit()
        db.refresh(invited_user)
        
        # Log the registration with role-specific description
        role_display = "adviser" if invited_user.role.value == "adviser" else "client"
        AuditLog.log_action(
            db,
            action="invitation_accepted",
            user_id=invited_user.id,
            office_id=invited_user.office_id,
            description=f"Invited {role_display} registered: {invited_user.email}",
            ip_address=get_client_ip_address(request)
        )
        db.commit()

        # Create tokens
        access_token = create_access_token(
            {"sub": invited_user.id, "role": invited_user.role.value})
        refresh_token = create_refresh_token({"sub": invited_user.id})

        # Get office info
        office = db.query(Office).filter(
            Office.id == invited_user.office_id).first()

        user_response = UserResponse(
            id=invited_user.id,
            email=invited_user.email,
            first_name=invited_user.first_name,
            last_name=invited_user.last_name,
            role=invited_user.role.value,
            status=invited_user.status.value,
            is_2fa_enabled=invited_user.is_2fa_enabled,
            ca_client_number=invited_user.ca_client_number,
            office_id=invited_user.office_id,
            office_code=office.code if office else "DEFAULT",
            office_name=office.name if office else None,
            is_office_admin=invited_user.is_office_admin,
            created_at=invited_user.created_at
        )

        # Send registration notice to office email (FROM_EMAIL)
        office_name = office.name if office else "CA Tadley"
        try:
            send_registration_notice_to_office(
                office_name=office_name,
                ca_client_number=invited_user.ca_client_number,
                registration_date=datetime.utcnow(),
                role=invited_user.role.value,
                user_email=invited_user.email
            )
        except Exception:
            pass

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )

    # Regular registration flow (no invitation token)
    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == user_register_request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Find office by code (handle case where code might be None)
    office = None
    if user_register_request.office_code:
        office = db.query(Office).filter(
            Office.code == user_register_request.office_code).first()

    # If no office found by code, use the default office
    if not office:
        office = db.query(Office).filter(Office.is_default ==
                                         True, Office.is_active == True).first()

    # If no default office, fall back to the first active office
    if not office:
        office = db.query(Office).filter(Office.is_active == True).first()

    if not office:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active office available for registration"
        )

    # Generate the next CA client number
    ca_client_number = generate_next_client_number(db)

    # Check if the generated client number already exists (shouldn't happen, but safety check)
    existing_client = db.query(User).filter(
        User.ca_client_number == ca_client_number
    ).first()
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating client number. Please try again."
        )

    # Do NOT create DB user yet; stage registration in a signed token
    import json, secrets
    staged_payload = {
        "email": user_register_request.email,
        "password_hash": hash_password(user_register_request.password),
        "first_name": user_register_request.first_name,
        "last_name": user_register_request.last_name,
        "ca_client_number": ca_client_number,
        "role": UserRole.CLIENT.value,
        "office_id": office.id,
    }
    # Generate OTP (debug: 30 seconds)
    otp_code = f"{secrets.randbelow(1000000):06d}"
    otp_exp_dt = datetime.utcnow() + timedelta(minutes=10)
    otp_exp = otp_exp_dt.isoformat()
    staged_payload.update({"otp": otp_code, "otp_exp": otp_exp})
    reg_token = create_access_token({"reg": staged_payload}, expires_delta=timedelta(minutes=15))

    # Defer creating ClientDetails until after OTP verification when user exists

    # No user yet, so skip client details; write an audit entry without user_id

    # Also save comprehensive default preferences to user table
    import json
    default_user_preferences = {
        # Communication Preferences
        "happy_voicemail": True,
        "happy_text_messages": True,

        # Preferred Contact Methods
        "preferred_contact_email": True,
        "preferred_contact_mobile": True,
        "preferred_contact_home_phone": False,
        "preferred_contact_address": False,

        # Research & Feedback
        "agree_to_feedback": True,

        # Do Not Contact Methods
        "do_not_contact_methods": [],
        "do_not_contact_feedback_methods": [],

        # Additional metadata
        "preferences_created_at": datetime.utcnow().isoformat(),
        "preferences_source": "auth_registration_defaults"
    }
    # Will save default preferences to user table after OTP verification

    # Log the registration
    AuditLog.log_action(
        db,
        action="account_registration_initiated",
        user_id=None,
        office_id=office.id,
        description=f"Manual registration initiated: {user_register_request.email}",
        ip_address=get_client_ip_address(request)
    )
    db.commit()

    # Initiate email OTP for manual registration (account not yet created)
    try:
        import secrets
        otp_session_token = secrets.token_urlsafe(16)
        # Send OTP email to the provided address (purpose registration, 30s)
        send_verification_code_email_extended(
            email=user_register_request.email,
            code=otp_code,
            user_name=user_register_request.first_name or user_register_request.email.split('@')[0],
            purpose="registration"
        )
    except Exception as e:
        logger.error(f"Failed to initiate email OTP: {e}")

    # Save to in-memory store for fallback verification
    OTP_STORE[otp_session_token] = {
        "email": user_register_request.email,
        "code": otp_code,
        "expires_at": otp_exp_dt,
        "reg_token": reg_token,
    }

    return JSONResponse({
        "otp_required": True,
        "otp_session_token": otp_session_token,
        "email": user_register_request.email,
        "reg_token": reg_token,
        "expires_in_seconds": 600
    })


@router.post("/login", response_model=TokenResponse)
@limiter.limit("50/minute")
async def login(
    request: Request,
    user_login_request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """Login with email and password, with optional 2FA"""

    user = db.query(User).filter(
        User.email == user_login_request.email).first()

    # Check if account is suspended or locked FIRST (before password validation)
    if user and user.status != UserStatus.ACTIVE:
        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account has been suspended."
            )
        elif user.status == UserStatus.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your account has been locked. Please contact admin@catadley.com for assistance."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )

    # Always hash the password even if user doesn't exist (timing attack prevention)
    if user:
        password_valid = verify_password(
            user_login_request.password, user.password_hash)
    else:
        hash_password("dummy_password")  # Prevent timing attacks
        password_valid = False

    if not user or not password_valid:
        # Log failed login attempt
        if user:
            # Check if user is a superuser - superusers have unlimited attempts
            if user.role == UserRole.SUPERUSER:
                # For superusers, just log the failed attempt but don't count attempts
                AuditLog.log_action(
                    db,
                    action="login_failed",
                    user_id=user.id,
                    office_id=user.office_id,
                    description=f"Superuser {user.email} failed login attempt (unlimited attempts)",
                    ip_address=get_client_ip_address(request),
                    success=False
                )
                db.commit()

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            else:
                # Regular users - apply attempt counting and suspension logic
                # Check if attempts should be reset first
                if should_reset_failed_attempts(user.first_failed_attempt):
                    user.failed_login_attempts = 0
                    user.first_failed_attempt = None
                    user.locked_until = None
                    db.commit()

                # Set first failed attempt timestamp if this is the first failure
                if user.failed_login_attempts == 0:
                    user.first_failed_attempt = datetime.utcnow()

                user.failed_login_attempts += 1
                remaining_attempts = get_remaining_attempts(
                    user.failed_login_attempts)

                if user.failed_login_attempts >= settings.max_login_attempts:
                    # Suspend the account without a time-based lockout; requires admin reactivation
                    user.status = UserStatus.SUSPENDED
                    user.locked_until = None

                    AuditLog.log_action(
                        db,
                        action="account_suspended",
                        user_id=user.id,
                        office_id=user.office_id,
                        description=f"Account suspended due to {user.failed_login_attempts} failed attempts for {user.email}",
                        ip_address=get_client_ip_address(request),
                        success=False
                    )
                    db.commit()

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Your account has been suspended."
                    )
                else:
                    AuditLog.log_action(
                        db,
                        action="login_failed",
                        user_id=user.id,
                        office_id=user.office_id,
                        description=f"Failed login attempt for {user.email}",
                        ip_address=get_client_ip_address(request),
                        success=False
                    )
                    db.commit()

                    # Get reset time information for regular users
                    reset_time = get_attempts_reset_time(
                        user.first_failed_attempt)
                    reset_info = f" Attempts will reset in {reset_time} minutes." if reset_time and reset_time > 0 else ""

                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Invalid email or password. {remaining_attempts} attempts remaining before account lockout.{reset_info}"
                    )
        else:
            # User doesn't exist, but don't reveal this
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    # For ACTIVE users with valid credentials, clear any stale lock state
    if user.status == UserStatus.ACTIVE:
        # Check if failed attempts should be reset based on time
        if should_reset_failed_attempts(user.first_failed_attempt):
            user.failed_login_attempts = 0
            user.first_failed_attempt = None
            user.locked_until = None
            db.commit()
        elif user.locked_until or user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.locked_until = None
            db.commit()

    # Removed time-based 423 lock check for ACTIVE users. Lock/suspension is enforced via status checks above.

    # Check 2FA if enabled
    if user.is_2fa_enabled:
        if not user_login_request.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA code required"
            )

        # Verify TOTP code or backup code
        totp_valid = verify_totp_code(
            user.totp_secret, user_login_request.totp_code)
        backup_valid = False

        if not totp_valid and user.backup_codes:
            backup_codes = eval(user.backup_codes) if user.backup_codes else []
            backup_valid, updated_codes = verify_backup_code(
                backup_codes, user_login_request.totp_code)
            if backup_valid:
                user.backup_codes = str(updated_codes)
                db.commit()

        if not totp_valid and not backup_valid:
            AuditLog.log_action(
                db,
                action="totp_failed",
                user_id=user.id,
                office_id=user.office_id,
                description=f"Invalid 2FA code for {user.email}",
                ip_address=get_client_ip_address(request),
                success=False
            )
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )

    # Successful login - reset failed attempts and optional info skip
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    user.optional_info_skipped = False  # Reset skip flag on each login

    if user.status == UserStatus.LOCKED:
        user.status = UserStatus.ACTIVE

    # Log successful login
    AuditLog.log_action(
        db,
        action="login",
        user_id=user.id,
        office_id=user.office_id,
        description=f"Successful login for {user.email}",
        ip_address=get_client_ip_address(request)
    )

    db.commit()

    # Create tokens
    access_token = create_access_token(
        {"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        status=user.status.value,
        is_2fa_enabled=user.is_2fa_enabled,
        ca_client_number=user.ca_client_number,
        office_id=user.office_id,
        office_code=user.office.code if user.office else None,
        office_name=user.office.name if user.office else None,
        is_office_admin=user.is_office_admin,
        created_at=user.created_at,
        # Optional information fields
        ethnicity=user.ethnicity,
        nationality=user.nationality,
        preferred_language=user.preferred_language,
        religion=user.religion,
        gender_identity=user.gender_identity,
        sexual_orientation=user.sexual_orientation,
        disability_status=user.disability_status,
        marital_status=user.marital_status,
        household_type=user.household_type,
        occupation=user.occupation,
        housing_tenure=user.housing_tenure,
        optional_info_completed=user.optional_info_completed,
        optional_info_skipped=user.optional_info_skipped,
        optional_info_never_show=user.optional_info_never_show
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """Logout user"""

    # Log logout
    AuditLog.log_action(
        db,
        action="logout",
        user_id=current_user.id,
        office_id=current_user.office_id,
        description=f"User logout: {current_user.email}",
        ip_address=req.client.host if req else None
    )
    db.commit()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role.value,
        status=current_user.status.value,
        is_2fa_enabled=current_user.is_2fa_enabled,
        ca_client_number=current_user.ca_client_number,
        office_id=current_user.office_id,
        office_code=current_user.office.code if current_user.office else None,
        office_name=current_user.office.name if current_user.office else None,
        is_office_admin=current_user.is_office_admin,
        created_at=current_user.created_at,
        # Optional information fields
        ethnicity=current_user.ethnicity,
        nationality=current_user.nationality,
        preferred_language=current_user.preferred_language,
        religion=current_user.religion,
        gender_identity=current_user.gender_identity,
        sexual_orientation=current_user.sexual_orientation,
        disability_status=current_user.disability_status,
        marital_status=current_user.marital_status,
        household_type=current_user.household_type,
        occupation=current_user.occupation,
        housing_tenure=current_user.housing_tenure,
        optional_info_completed=current_user.optional_info_completed,
        optional_info_skipped=current_user.optional_info_skipped,
        optional_info_never_show=current_user.optional_info_never_show
    )


class SessionInfoResponse(BaseModel):
    remaining_seconds: int
    warning_threshold: int
    inactivity_threshold_seconds: int
    is_testing: bool


@router.get("/session-info", response_model=SessionInfoResponse)
async def get_session_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current session information for frontend countdown"""
    from ..models import SessionSettings
    session_settings = SessionSettings.get_or_create_default(db)
    
    # Get role-specific settings for the current user
    role_settings = session_settings.get_settings_for_role(current_user.role)
    
    # If session management is disabled, return high values
    if not session_settings.enable_session_management:
        return SessionInfoResponse(
            remaining_seconds=999999,  # High value to prevent warnings
            warning_threshold=role_settings["session_warning_seconds"],
            inactivity_threshold_seconds=role_settings["inactivity_threshold_seconds"],
            is_testing=False
        )
    
    # Use role-specific session timeout configuration
    remaining_seconds = get_session_remaining_time(current_user.last_activity, False, db, current_user.role)
    warning_threshold = get_session_warning_threshold(False, db, current_user.role)
    
    return SessionInfoResponse(
        remaining_seconds=remaining_seconds,
        warning_threshold=warning_threshold,
        inactivity_threshold_seconds=role_settings["inactivity_threshold_seconds"],
        is_testing=False
    )


@router.post("/enable-2fa", response_model=Enable2FAResponse)
async def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA for current user"""

    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )

    # Generate TOTP secret and backup codes
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()

    # Generate QR code
    qr_code = generate_totp_qr_code(
        secret,
        current_user.email,
        current_user.office.name
    )

    # Save to user (but don't enable until verified)
    current_user.totp_secret = secret
    current_user.backup_codes = str(backup_codes)
    db.commit()

    return Enable2FAResponse(
        qr_code=qr_code,
        secret=secret,
        backup_codes=backup_codes
    )


@router.post("/verify-2fa")
async def verify_2fa_setup(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA setup and enable it"""

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated"
        )

    if not verify_totp_code(current_user.totp_secret, request.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )

    # Enable 2FA
    current_user.is_2fa_enabled = True

    # Log 2FA enablement
    AuditLog.log_action(
        db,
        action="totp_enabled",
        user_id=current_user.id,
        office_id=current_user.office_id,
        description=f"2FA enabled for {current_user.email}"
    )

    db.commit()

    return {"message": "2FA successfully enabled"}


@router.post("/verify-email-otp", response_model=TokenResponse)
async def verify_email_otp(
    request: VerifyEmailOtpRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """Verify email OTP for manual registration and issue tokens"""
    # Basic request validation
    if not request.otp_session_token or not request.code or not request.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")

    # Require registration token to construct the pending user safely
    reg_token = request.reg_token or req.query_params.get('reg_token')
    if not reg_token:
        # Backwards compatibility: reject if no reg token present
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing registration token")

    from ..utils.auth import verify_token
    reg = None
    payload = verify_token(reg_token) if reg_token else None
    if payload and 'reg' in payload and payload['reg'].get('email') == request.email:
        reg = payload['reg']
        # Validate OTP from token
        otp_expected = reg.get('otp')
        otp_exp = reg.get('otp_exp')
        if not otp_expected or not otp_exp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
        try:
            if datetime.fromisoformat(otp_exp) <= datetime.utcnow():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
        if request.code != otp_expected:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    else:
        # Fallback: validate against in-memory store by session
        store_entry = OTP_STORE.get(request.otp_session_token)
        if not store_entry or store_entry.get('email') != request.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
        if store_entry['expires_at'] <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
        if request.code != store_entry.get('code'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
        # Decode reg from the stored reg_token
        payload2 = verify_token(store_entry.get('reg_token') or '')
        if not payload2 or 'reg' not in payload2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid registration token")
        reg = payload2['reg']

    # Create user now
    user = User(
        email=reg['email'],
        password_hash=reg['password_hash'],
        first_name=reg.get('first_name'),
        last_name=reg.get('last_name'),
        ca_client_number=reg.get('ca_client_number'),
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        office_id=reg.get('office_id'),
        last_login=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Issue tokens
    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    office = db.query(Office).filter(Office.id == user.office_id).first()
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        status=user.status.value,
        is_2fa_enabled=user.is_2fa_enabled,
        ca_client_number=user.ca_client_number,
        office_id=user.office_id,
        office_code=office.code if office else "DEFAULT",
        office_name=office.name if office else None,
        is_office_admin=user.is_office_admin,
        created_at=user.created_at
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.post("/resend-email-otp")
async def resend_email_otp(
    request: ResendEmailOtpRequest
):
    """Resend a new OTP and return updated reg_token and session token."""
    from ..utils.auth import verify_token, create_access_token
    import secrets
    payload = verify_token(request.reg_token)
    if not payload or 'reg' not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid registration token")
    reg = payload['reg']
    if reg.get('email') != request.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email mismatch")
    # Generate new OTP (10 minutes)
    otp_code = f"{secrets.randbelow(1000000):06d}"
    otp_exp_dt = datetime.utcnow() + timedelta(minutes=10)
    otp_exp = otp_exp_dt.isoformat()
    reg.update({"otp": otp_code, "otp_exp": otp_exp})
    new_reg_token = create_access_token({"reg": reg}, expires_delta=timedelta(minutes=15))
    otp_session_token = secrets.token_urlsafe(16)
    # Persist to in-memory store so fallback verification works after refresh
    OTP_STORE[otp_session_token] = {
        "email": request.email,
        "code": otp_code,
        "expires_at": otp_exp_dt,
        "reg_token": new_reg_token,
    }
    # Send email again
    try:
        send_verification_code_email_extended(email=request.email, code=otp_code, purpose="registration")
    except Exception:
        pass
    return JSONResponse({
        "otp_session_token": otp_session_token,
        "reg_token": new_reg_token,
        "expires_in_seconds": 600
    })


@router.post("/disable-2fa")
async def disable_2fa(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA (requires verification)"""

    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    if not verify_totp_code(current_user.totp_secret, request.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )

    # Disable 2FA
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None

    # Log 2FA disablement
    AuditLog.log_action(
        db,
        action="totp_disabled",
        user_id=current_user.id,
        office_id=current_user.office_id,
        description=f"2FA disabled for {current_user.email}"
    )

    db.commit()

    return {"message": "2FA successfully disabled"}


@router.post("/request-password-reset")
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    password_reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""

    user = db.query(User).filter(
        User.email == password_reset_request.email).first()

    # Always return success to prevent email enumeration
    if user:
        # Generate reset token
        reset_token = generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow(
        ) + timedelta(hours=settings.password_reset_expire_hours)

        # Log password reset request
        AuditLog.log_action(
            db,
            action="password_reset_requested",
            user_id=user.id,
            office_id=user.office_id,
            description=f"Password reset requested for {user.email}"
        )

        db.commit()

        # Send password reset email
        try:
            from ..services.email_service import send_password_reset_email
            user_name = f"{user.first_name} {user.last_name}".strip(
            ) or user.email.split('@')[0]
            send_password_reset_email(user.email, reset_token, user_name)
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {user.email}: {e}")
            # Don't fail the request if email sending fails

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    password_reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password with token"""

    user = db.query(User).filter(
        User.reset_token == password_reset_confirm.token,
        User.reset_token_expires > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password
    user.password_hash = hash_password(password_reset_confirm.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None

    if user.status == UserStatus.LOCKED:
        user.status = UserStatus.ACTIVE

    # Log password reset completion
    AuditLog.log_action(
        db,
        action="password_reset_completed",
        user_id=user.id,
        office_id=user.office_id,
        description=f"Password reset completed for {user.email}"
    )

    db.commit()

    return {"message": "Password successfully reset"}

# CSRF token endpoint removed due to compatibility issues
