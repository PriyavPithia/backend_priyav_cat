from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from ..config.database import Base
import uuid
import os

class FileCategory(PyEnum):
    DEBT_DOCUMENT = "debt_document"
    ASSET_DOCUMENT = "asset_document"
    INCOME_DOCUMENT = "income_document"
    EXPENDITURE_DOCUMENT = "expenditure_document"
    IDENTITY_DOCUMENT = "identity_document"
    OTHER = "other"

class FileStatus(PyEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
    DELETED = "deleted"

class FileUpload(Base):
    __tablename__ = "file_uploads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Associations
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    debt_id = Column(String, ForeignKey("debts.id"), nullable=True)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=True)
    income_id = Column(String, ForeignKey("incomes.id"), nullable=True)
    expenditure_id = Column(String, ForeignKey("expenditures.id"), nullable=True)
    
    # File details
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)  # UUID-based filename for security
    file_path = Column(String(500), nullable=False)  # Local file path
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_extension = Column(String(10), nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # S3 Storage fields
    s3_key = Column(String(500), nullable=True)  # S3 object key
    storage_type = Column(String(10), default="local")  # "local", "s3", or "hybrid"
    
    # File categorization
    category = Column(Enum(FileCategory), nullable=False, default=FileCategory.OTHER)
    status = Column(Enum(FileStatus), nullable=False, default=FileStatus.UPLOADED)
    
    # Type information for filtering (when not linked to specific records)
    debt_type = Column(String(50), nullable=True)
    asset_type = Column(String(50), nullable=True)
    income_type = Column(String(50), nullable=True)
    expenditure_type = Column(String(50), nullable=True)
    
    # Security and validation
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash for integrity checking
    is_encrypted = Column(Boolean, default=True)
    encryption_key_id = Column(String(255), nullable=True)
    
    # Virus scanning (if implemented)
    virus_scan_status = Column(String(20), nullable=True)  # "clean", "infected", "pending"
    virus_scan_date = Column(DateTime, nullable=True)
    
    # Processing information
    description = Column(Text, nullable=True)  # User-provided description
    processing_notes = Column(Text, nullable=True)  # System processing notes
    error_message = Column(Text, nullable=True)
    was_converted = Column(Boolean, default=False)  # Track if file was converted (e.g., HEIC to PNG)
    
    # Access tracking
    download_count = Column(Integer, default=0)
    last_downloaded = Column(DateTime, nullable=True)
    downloaded_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Metadata
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="files")
    debt = relationship("Debt", back_populates="files")
    asset = relationship("Asset", back_populates="files")
    income = relationship("Income", back_populates="files")
    expenditure = relationship("Expenditure", back_populates="files")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    downloaded_by = relationship("User", foreign_keys=[downloaded_by_id])
    
    @property
    def file_size_formatted(self):
        """Return human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    @property
    def is_image(self):
        """Check if file is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.tiff']
        return self.file_extension.lower() in image_extensions
    
    @property
    def is_document(self):
        """Check if file is a document"""
        document_extensions = ['.pdf', '.doc', '.docx', '.rtf', '.html', '.xml']
        return self.file_extension.lower() in document_extensions
    
    @property
    def display_name(self):
        """Get display name for the file"""
        if self.description:
            return f"{self.description} ({self.original_filename})"
        return self.original_filename
    
    @classmethod
    def is_allowed_extension(cls, filename):
        """Check if file extension is allowed"""
        allowed_extensions = [
            '.doc', '.docx', '.gif', '.html', '.jpeg', '.jpg', '.heic',
            '.lgb', '.msg', '.pdf', '.png', '.qb1', '.rtf', '.tiff', '.xml'
        ]
        ext = os.path.splitext(filename.lower())[1]
        return ext in allowed_extensions
    
    @classmethod
    def get_max_file_size(cls):
        """Get maximum allowed file size (50MB)"""
        return 50 * 1024 * 1024  # 50MB in bytes
    
    def __repr__(self):
        return f"<FileUpload {self.original_filename} ({self.file_size_formatted})>"
