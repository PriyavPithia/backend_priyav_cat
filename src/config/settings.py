from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Application
    app_name: str = os.getenv("APP_NAME", "CA Tadley Debt Advice Tool")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ca_tadley_debt_tool.db")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Only enforce SECRET_KEY requirement in production
        if not self.secret_key and not self.debug:
            raise ValueError("SECRET_KEY environment variable is required in production")
        elif not self.secret_key and self.debug:
            # Generate a temporary secret key for development
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
            print("⚠️  WARNING: Using temporary SECRET_KEY for development. Set SECRET_KEY environment variable for production!")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    password_reset_expire_hours: int = int(os.getenv("PASSWORD_RESET_EXPIRE_HOURS", "24"))
    
    # File Upload
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB default
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    allowed_extensions: List[str] = [
        "doc", "docx", "gif", "html", "jpeg", "jpg", "heic",
        "lgb", "msg", "pdf", "png", "qb1", "rtf", "tiff", "xml"
    ]
    
    # HEIC Conversion Settings (for speed optimization)
    heic_max_dimension: int = 2048  # Max width/height for converted images
    heic_quality: int = 85  # JPEG quality (1-100, 85 is good balance)
    heic_use_jpeg: bool = True  # Use JPEG for speed (True) or PNG for quality (False)
    
    # Email (for 2FA and notifications)
    # SMTP Configuration (legacy)
    smtp_server: Optional[str] = os.getenv("SMTP_SERVER")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    from_email: str = os.getenv("FROM_EMAIL", "noreply@citizensadvicetadley.org.uk")
    
    # AWS SES Configuration
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region: str = os.getenv("AWS_REGION", "eu-west-2")  # Default to London region
    ses_from_email: str = os.getenv("SES_FROM_EMAIL", "noreply@citizensadvicetadley.org.uk")
    ses_reply_to_email: Optional[str] = os.getenv("SES_REPLY_TO_EMAIL")
    use_ses: bool = os.getenv("USE_SES", "false").lower() == "true"
    ses_configuration_set: Optional[str] = os.getenv("SES_CONFIGURATION_SET")  # For tracking
    
    # Security Settings
    auto_logout_minutes: int = int(os.getenv("AUTO_LOGOUT_MINUTES", "30"))
    # Session timeout settings - configurable for testing vs production
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    session_timeout_test_minutes: int = int(os.getenv("SESSION_TIMEOUT_TEST_MINUTES", "1"))
    session_warning_seconds: int = int(os.getenv("SESSION_WARNING_SECONDS", "60"))
    session_warning_test_seconds: int = int(os.getenv("SESSION_WARNING_TEST_SECONDS", "10"))
    # For testing: override to 30 seconds when debug mode is enabled
    session_timeout_test_seconds: int = int(os.getenv("SESSION_TIMEOUT_TEST_SECONDS", "30"))
    max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    lockout_duration_minutes: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    
    # CORS
    # Include production frontend by default; override via ALLOWED_ORIGINS env
    allowed_origins: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "app.log")
    
    class Config:
        # env_file = ".env"  # Temporarily disabled due to encoding issues
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables

settings = Settings()
