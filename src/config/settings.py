from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = os.getenv(
        "APP_NAME", "CA Tadley Debt Advice Tool")  # .env: APP_NAME
    app_version: str = os.getenv("APP_VERSION", "1.0.0")  # .env: APP_VERSION
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"  # .env: DEBUG

    # Database (RDS PostgreSQL)
    database_url: str = os.getenv(
        "LOCAL_DATABASE_URL",
        "postgresql://cat_local_db:pr7tz123@localhost:5432/cat_database"
    )  # .env: DATABASE_URL

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "")  # .env: SECRET_KEY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize allowed_origins from environment (avoiding JSON parsing)
        origins_str = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,"
            "http://127.0.0.1:3000,http://127.0.0.1:5173,"
            "http://stage-case.sattva-ai.com,https://stage-case.sattva-ai.com"
        )
        object.__setattr__(self, 'allowed_origins', [
            origin.strip() for origin in origins_str.split(",")
        ])

        # Only enforce SECRET_KEY requirement in production
        if not self.secret_key and not self.debug:
            raise ValueError(
                "SECRET_KEY environment variable is required in production")
        elif not self.secret_key and self.debug:
            # Generate a temporary secret key for development
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
            print("⚠️  WARNING: Using temporary SECRET_KEY for development. Set SECRET_KEY environment variable for production!")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # .env: ACCESS_TOKEN_EXPIRE_MINUTES
    refresh_token_expire_days: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # .env: REFRESH_TOKEN_EXPIRE_DAYS
    password_reset_expire_hours: int = int(
        os.getenv("PASSWORD_RESET_EXPIRE_HOURS", "24"))  # .env: PASSWORD_RESET_EXPIRE_HOURS

    # File Upload
    max_file_size: int = int(
        os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # .env: MAX_FILE_SIZE
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")  # .env: UPLOAD_DIR
    allowed_extensions: List[str] = [
        "doc", "docx", "gif", "html", "jpeg", "jpg", "heic",
        "lgb", "msg", "pdf", "png", "qb1", "rtf", "tiff", "xml"
    ]
    
    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = os.getenv(
        "AWS_ACCESS_KEY_ID")  # .env: AWS_ACCESS_KEY_ID
    aws_secret_access_key: Optional[str] = os.getenv(
        "AWS_SECRET_ACCESS_KEY")  # .env: AWS_SECRET_ACCESS_KEY
    aws_region: str = os.getenv(
        "AWS_REGION", "eu-west-2")  # .env: AWS_REGION
    s3_bucket_name: str = os.getenv(
        "S3_BUCKET_NAME", "ca-tadley-debt-tool-files")  # .env: S3_BUCKET_NAME
    s3_endpoint_url: Optional[str] = os.getenv(
        "S3_ENDPOINT_URL")  # .env: S3_ENDPOINT_URL
    use_s3_storage: bool = os.getenv(
        "USE_S3_STORAGE", "true").lower() == "true"  # .env: USE_S3_STORAGE

    # HEIC Conversion Settings (for speed optimization)
    heic_max_dimension: int = 2048  # Max width/height for converted images.
    heic_quality: int = 85  # JPEG quality (1-100, 85 is good balance)
    # Use JPEG for speed (True) or PNG for quality (False)
    heic_use_jpeg: bool = True

    # Email (for 2FA and notifications)
    smtp_server: Optional[str] = os.getenv("SMTP_SERVER")  # .env: SMTP_SERVER
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))  # .env: SMTP_PORT
    smtp_username: Optional[str] = os.getenv(
        "SMTP_USERNAME")  # .env: SMTP_USERNAME
    smtp_password: Optional[str] = os.getenv(
        "SMTP_PASSWORD")  # .env: SMTP_PASSWORD
    smtp_use_tls: bool = os.getenv(
        "SMTP_USE_TLS", "true").lower() == "true"  # .env: SMTP_USE_TLS
    from_email: str = os.getenv(
        "FROM_EMAIL", "dev@sattva-ai.com")  # .env: FROM_EMAIL

    # Frontend URL for email links
    frontend_url: str = os.getenv(
        "FRONTEND_URL", "http://localhost:3000")  # .env: FRONTEND_URL.

    # Password reset settings
    password_reset_expire_hours: int = int(os.getenv(
        "PASSWORD_RESET_EXPIRE_HOURS", "24"))  # .env: PASSWORD_RESET_EXPIRE_HOURS

    # Security Settings
    auto_logout_minutes: int = int(
        os.getenv("AUTO_LOGOUT_MINUTES", "30"))  # .env: AUTO_LOGOUT_MINUTES
    # Session timeout settings - configurable for testing vs production
    session_timeout_minutes: int = int(
        os.getenv("SESSION_TIMEOUT_MINUTES", "30"))  # .env: SESSION_TIMEOUT_MINUTES
    session_timeout_test_minutes: int = int(
        os.getenv("SESSION_TIMEOUT_TEST_MINUTES", "1"))  # .env: SESSION_TIMEOUT_TEST_MINUTES
    session_warning_seconds: int = int(
        os.getenv("SESSION_WARNING_SECONDS", "60"))  # .env: SESSION_WARNING_SECONDS
    session_warning_test_seconds: int = int(
        os.getenv("SESSION_WARNING_TEST_SECONDS", "10"))  # .env: SESSION_WARNING_TEST_SECONDS
    # For testing: override to 30 seconds when debug mode is enabled
    session_timeout_test_seconds: int = int(
        os.getenv("SESSION_TIMEOUT_TEST_SECONDS", "30"))  # .env: SESSION_TIMEOUT_TEST_SECONDS
    max_login_attempts: int = int(
        os.getenv("MAX_LOGIN_ATTEMPTS", "5"))  # .env: MAX_LOGIN_ATTEMPTS
    lockout_duration_minutes: int = int(
        os.getenv("LOCKOUT_DURATION_MINUTES", "15"))  # .env: LOCKOUT_DURATION_MINUTES

    # CORS - set manually to avoid JSON parsing issues

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")  # .env: LOG_LEVEL
    log_file: str = os.getenv("LOG_FILE", "app.log")  # .env: LOG_FILE

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env file
        env_ignore={"allowed_origins"}  # Don't auto-parse from env
    )


settings = Settings()
