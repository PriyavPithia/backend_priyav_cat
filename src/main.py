from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from contextlib import asynccontextmanager
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# CSRF protection removed due to compatibility issues

from .config.settings import settings
from .config.logging import setup_logging, get_logger
from .models import create_tables
from .routes import auth, cases, admin, offices, client_details, profile, notifications, session_settings, files
# Import other routes as we create them

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# CSRF protection will be configured after app creation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger = setup_logging()
    logger.info("Starting CA Tadley Debt Advice Tool...")
    
    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info(f"Upload directory created: {settings.upload_dir}")
    
    # Create other database tables
    create_tables()
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CA Tadley Debt Advice Tool...")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Citizens Advice Tadley Debt Advice Tool - Secure debt data collection and management system",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CSRF protection removed due to compatibility issues with newer FastAPI versions

# Security middleware
if not settings.debug:
    # Include Railway and your custom domains. Override via ALLOWED_HOSTS env in prod.
    allowed_hosts = os.getenv(
        "ALLOWED_HOSTS",
        "*.citizensadvicetadley.org.uk,*.up.railway.app,web-production-dd1a.up.railway.app"
    ).split(",")
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=allowed_hosts
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "Access-Control-Request-Method", "Access-Control-Request-Headers"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers for production
    if not settings.debug:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # HSTS header (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy - Strict for production
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self'; "  # Remove unsafe-inline and unsafe-eval
            "style-src 'self'; "  # Remove unsafe-inline
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://catadley-hhz5h.ondigitalocean.app; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
    
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for security audit"""
    import time
    from .config.logging import log_api_request
    
    start_time = time.time()
    
    # Get user ID from request if available
    user_id = None
    if hasattr(request.state, 'user') and request.state.user:
        user_id = str(request.state.user.id)
    
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log the request
    log_api_request(
        method=request.method,
        path=str(request.url.path),
        user_id=user_id,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2)
    )
    
    return response

# Include API routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(offices.router, prefix="/api/admin/offices", tags=["Office Management"])
app.include_router(client_details.router, prefix="/api", tags=["Client Details"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile Management"])
app.include_router(files.router, prefix="/api/files", tags=["File Uploads"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(session_settings.router, prefix="/api", tags=["Session Settings"])

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name
    }

# Public office lookup endpoint for registration
@app.get("/api/offices/public")
async def get_office_by_code_public(code: str):
    """Get office information by code (public endpoint for registration)"""
    from sqlalchemy.orm import Session
    from .config.database import get_db
    from .models import Office
    from fastapi import HTTPException, status
    
    db = next(get_db())
    office = db.query(Office).filter(Office.code == code, Office.is_active == True).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found or inactive"
        )
    
    return {
        "offices": [{
            "id": office.id,
            "name": office.name,
            "code": office.code,
            "address": office.address,
            "contact_phone": office.contact_phone,
            "contact_email": office.contact_email,
            "is_active": office.is_active
        }]
    }

# Serve static files (for production)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "CA Tadley Debt Advice Tool API",
        "version": settings.app_version,
        "docs": "/api/docs" if settings.debug else "Contact administrator for API documentation"
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
