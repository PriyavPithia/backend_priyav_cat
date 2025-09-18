import logging
import sys
import os
from datetime import datetime
from .settings import settings

def setup_logging():
    """Setup structured logging for the application"""
    
    # Determine log level based on debug mode
    log_level = logging.DEBUG if settings.debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create handlers
    handlers = []
    
    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler (only in production)
    if not settings.debug:
        # Ensure logs directory exists
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler with rotation
        # Configure for 1-year retention minimum as per data logging requirements
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=50*1024*1024,  # 50MB per file (increased for better retention)
            backupCount=50  # Keep 50 backup files (~2.5GB total, enough for 1+ years)
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Set specific loggers to appropriate levels
    if not settings.debug:
        # Reduce noise from third-party libraries in production
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
        logging.getLogger('fastapi').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Create application logger
    logger = logging.getLogger('ca_tadley_debt_tool')
    logger.info("Logging system initialized")
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance for a specific module"""
    if name:
        return logging.getLogger(f'ca_tadley_debt_tool.{name}')
    return logging.getLogger('ca_tadley_debt_tool')

# Security logging functions
def log_security_event(event_type: str, user_id: str = None, details: str = None, ip_address: str = None):
    """Log security-related events"""
    logger = get_logger('security')
    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'details': details,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    logger.warning(f"Security Event: {log_data}")

def log_authentication_attempt(email: str, success: bool, ip_address: str = None, details: str = None):
    """Log authentication attempts"""
    event_type = "login_success" if success else "login_failed"
    log_security_event(event_type, details=f"Email: {email}, Details: {details}", ip_address=ip_address)

def log_file_operation(operation: str, file_id: str = None, user_id: str = None, details: str = None, ip_address: str = None):
    """Log file operations"""
    logger = get_logger('files')
    log_data = {
        'operation': operation,
        'file_id': file_id,
        'user_id': user_id,
        'details': details,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    logger.info(f"File Operation: {log_data}")

def log_case_operation(operation: str, case_id: str = None, user_id: str = None, details: str = None, ip_address: str = None):
    """Log case operations"""
    logger = get_logger('cases')
    log_data = {
        'operation': operation,
        'case_id': case_id,
        'user_id': user_id,
        'details': details,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    logger.info(f"Case Operation: {log_data}")

def log_client_setup(operation: str, user_id: str = None, details: str = None, ip_address: str = None):
    """Log client account setup operations"""
    logger = get_logger('client_setup')
    log_data = {
        'operation': operation,
        'user_id': user_id,
        'details': details,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    logger.info(f"Client Setup: {log_data}")

def log_api_request(method: str, path: str, user_id: str = None, status_code: int = None, duration_ms: float = None):
    """Log API requests"""
    logger = get_logger('api')
    log_data = {
        'method': method,
        'path': path,
        'user_id': user_id,
        'status_code': status_code,
        'duration_ms': duration_ms,
        'timestamp': datetime.utcnow().isoformat()
    }
    logger.info(f"API Request: {log_data}")
