from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import pyotp
import qrcode
from io import BytesIO
import base64
from fastapi import Request
from ..config.settings import settings

# Password hashing (use pbkdf2_sha256 to avoid platform bcrypt issues)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password meets requirements:
    - Minimum 10 characters
    - Contains uppercase, lowercase, and numbers
    """
    errors = []
    
    if len(password) < 10:
        errors.append("Password must be at least 10 characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

def generate_reset_token() -> str:
    """Generate secure password reset token"""
    return secrets.token_urlsafe(32)

def generate_verification_token() -> str:
    """Generate email verification token"""
    return secrets.token_urlsafe(32)

def generate_invitation_token() -> str:
    """Generate user invitation token"""
    return secrets.token_urlsafe(32)

# Two-Factor Authentication (TOTP)
def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA"""
    return pyotp.random_base32()

def generate_totp_qr_code(secret: str, email: str, office_name: str) -> str:
    """Generate QR code for TOTP setup"""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=f"CA {office_name} - Debt Advice Tool"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 string
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{qr_code_data}"

def verify_totp_code(secret: str, code: str) -> bool:
    """Verify TOTP code"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 1 window of tolerance

def generate_backup_codes(count: int = 8) -> list:
    """Generate backup codes for 2FA recovery"""
    return [secrets.token_hex(4).upper() for _ in range(count)]

def verify_backup_code(backup_codes: list, code: str) -> tuple[bool, list]:
    """
    Verify backup code and remove it from the list
    Returns (is_valid, updated_codes_list)
    """
    code_upper = code.upper()
    if code_upper in backup_codes:
        updated_codes = [c for c in backup_codes if c != code_upper]
        return True, updated_codes
    return False, backup_codes

# Rate limiting helpers
def is_account_locked(failed_attempts: int, locked_until: Optional[datetime]) -> bool:
    """Check if account is locked due to failed login attempts"""
    # Check if account is locked by time
    if locked_until and locked_until > datetime.utcnow():
        return True
    # Check if account should be locked by failed attempts (but only if not already reactivated)
    if failed_attempts >= settings.max_login_attempts and locked_until is None:
        return True
    return False

def calculate_lockout_time() -> datetime:
    """Calculate when account lockout expires"""
    return datetime.utcnow() + timedelta(minutes=settings.lockout_duration_minutes)

def get_remaining_attempts(failed_attempts: int) -> int:
    """Get remaining login attempts before lockout"""
    return max(0, settings.max_login_attempts - failed_attempts)

def get_lockout_remaining_time(locked_until: Optional[datetime]) -> Optional[int]:
    """Get remaining lockout time in minutes"""
    if not locked_until or locked_until <= datetime.utcnow():
        return None
    remaining = locked_until - datetime.utcnow()
    return max(0, int(remaining.total_seconds() / 60))

def should_reset_failed_attempts(first_failed_attempt: Optional[datetime]) -> bool:
    """Check if failed attempts should be reset based on time elapsed"""
    if not first_failed_attempt:
        return False
    
    # For testing: 1 minute, for production: 30 minutes
    reset_after_minutes = 1 if settings.debug else 30
    reset_time = first_failed_attempt + timedelta(minutes=reset_after_minutes)
    
    return datetime.utcnow() >= reset_time

def get_attempts_reset_time(first_failed_attempt: Optional[datetime]) -> Optional[int]:
    """Get remaining time until attempts reset in minutes"""
    if not first_failed_attempt:
        return None
    
    # For testing: 1 minute, for production: 30 minutes
    reset_after_minutes = 1 if settings.debug else 30
    reset_time = first_failed_attempt + timedelta(minutes=reset_after_minutes)
    
    if datetime.utcnow() >= reset_time:
        return 0
    
    remaining = reset_time - datetime.utcnow()
    return max(0, int(remaining.total_seconds() / 60))

def should_send_reminder(last_reminder: Optional[datetime], reminder_count: int) -> bool:
    """
    Check if a reminder email should be sent
    Weekly reminders for up to 6 weeks
    """
    if reminder_count >= 6:
        return False
    
    if not last_reminder:
        return True
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    return last_reminder < week_ago

# Email validation
def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Session management
def get_session_settings(db):
    """Get session settings from database"""
    try:
        from ..models import SessionSettings
        return SessionSettings.get_or_create_default(db)
    except Exception as e:
        print(f"Error getting session settings: {str(e)}")
        # Return default settings object if database access fails
        return type('SessionSettings', (), {
            'enable_session_management': True,
            'session_timeout_seconds': 300,
            'session_warning_seconds': 60
        })()

def is_session_expired(last_activity: Optional[datetime], is_testing: bool = False, db=None, user_role=None) -> bool:
    """Check if user session has expired based on last activity"""
    if not last_activity:
        return True
    
    # Get dynamic settings if database is available, otherwise use static settings
    if db:
        session_settings = get_session_settings(db)
        if not session_settings.enable_session_management:
            return False  # Session management disabled
        
        # Get role-specific settings if user_role is provided
        if user_role:
            role_settings = session_settings.get_settings_for_role(user_role)
            timeout_delta = timedelta(seconds=role_settings["session_timeout_seconds"])
        else:
            # Fallback to legacy settings
            timeout_delta = timedelta(seconds=session_settings.session_timeout_seconds)
    else:
        # Fallback to static settings if no database connection
        timeout_delta = timedelta(minutes=7)  # 7 minutes default (client settings)
    
    return datetime.utcnow() - last_activity > timeout_delta

def get_session_remaining_time(last_activity: Optional[datetime], is_testing: bool = False, db=None, user_role=None) -> int:
    """Get remaining session time in seconds"""
    if not last_activity:
        return 0
    
    # Get dynamic settings if database is available, otherwise use static settings
    if db:
        session_settings = get_session_settings(db)
        if not session_settings.enable_session_management:
            return 999999  # Return high value if session management disabled
        
        # Get role-specific settings if user_role is provided
        if user_role:
            role_settings = session_settings.get_settings_for_role(user_role)
            timeout_delta = timedelta(seconds=role_settings["session_timeout_seconds"])
        else:
            # Fallback to legacy settings
            timeout_delta = timedelta(seconds=session_settings.session_timeout_seconds)
    else:
        # Fallback to static settings if no database connection
        timeout_delta = timedelta(minutes=7)  # 7 minutes default (client settings)
    
    session_expires_at = last_activity + timeout_delta
    remaining = session_expires_at - datetime.utcnow()
    
    return max(0, int(remaining.total_seconds()))

def get_session_warning_threshold(is_testing: bool = False, db=None, user_role=None) -> int:
    """Get session warning threshold in seconds"""
    # Get dynamic settings if database is available, otherwise use static settings
    if db:
        session_settings = get_session_settings(db)
        # Get role-specific settings if user_role is provided
        if user_role:
            role_settings = session_settings.get_settings_for_role(user_role)
            return role_settings["session_warning_seconds"]
        else:
            # Fallback to legacy settings
            return session_settings.session_warning_seconds
    else:
        # Fallback to static settings if no database connection
        return 300  # 5 minutes default (client settings)

def get_client_ip_address(request: Request) -> Optional[str]:
    """Get the real client IP address from request headers, accounting for proxies and load balancers"""
    if not request:
        return None
    
    # Check for forwarded IP addresses (common in proxy/load balancer setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header (used by some proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Check for client IP header (used by some load balancers)
    client_ip = request.headers.get("X-Client-IP")
    if client_ip:
        return client_ip.strip()
    
    # Check for CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    
    # Fallback to direct client host
    if request.client:
        return request.client.host
    
    return None
