import os
import uuid
import hashlib
try:
    import magic  # Requires libmagic; may be unavailable on Windows
    _MAGIC_AVAILABLE = True
except Exception:
    magic = None  # type: ignore
    _MAGIC_AVAILABLE = False
import aiofiles
import io
import zipfile
from typing import Optional, Tuple, List
import mimetypes
import asyncio
from cryptography.fernet import Fernet
from fastapi import UploadFile
from PIL import Image
try:
    import pillow_heif
    _HEIF_AVAILABLE = True
except ImportError:
    pillow_heif = None
    _HEIF_AVAILABLE = False
from ..config.settings import settings
from ..config.logging import get_logger

# Initialize logger for this module
logger = get_logger('file_utils')

# Register HEIC opener with Pillow if available
if _HEIF_AVAILABLE:
    pillow_heif.register_heif_opener()

# File encryption
def generate_encryption_key() -> bytes:
    """Generate encryption key for file encryption"""
    return Fernet.generate_key()

def encrypt_file_content(content: bytes, key: bytes) -> bytes:
    """Encrypt file content"""
    f = Fernet(key)
    return f.encrypt(content)

def decrypt_file_content(encrypted_content: bytes, key: bytes) -> bytes:
    """Decrypt file content"""
    f = Fernet(key)
    return f.decrypt(encrypted_content)

def get_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def get_file_mime_type(content: bytes) -> str:
    """Best-effort MIME type detection.

    Prefers libmagic when available; otherwise falls back to Pillow image probing
    and generic binary type.
    """
    # libmagic path (best accuracy)
    if _MAGIC_AVAILABLE:
        try:
            return magic.from_buffer(content, mime=True)
        except Exception:
            pass

    # Pillow-based probe for common images
    try:
        img = Image.open(io.BytesIO(content))
        fmt = (img.format or '').upper()
        mapping = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'GIF': 'image/gif',
            'TIFF': 'image/tiff',
            'HEIF': 'image/heic',  # pre-conversion case
            'WEBP': 'image/webp',
        }
        if fmt in mapping:
            return mapping[fmt]
    except Exception:
        pass

    # Fallback
    return "application/octet-stream"

def generate_secure_filename(original_filename: str, client_id: Optional[str] = None) -> str:
    """Generate secure filename with client ID prefix"""
    ext = os.path.splitext(original_filename)[1].lower()
    base_filename = os.path.splitext(original_filename)[0]
    uuid_part = uuid.uuid4().hex[:8]  # Use shorter UUID for uniqueness
    
    logger.debug(f"generate_secure_filename called with:")
    logger.debug(f"  - original_filename: {original_filename}")
    logger.debug(f"  - client_id: {client_id}")
    logger.debug(f"  - ext: {ext}")
    logger.debug(f"  - base_filename: {base_filename}")
    
    if client_id:
        # Check if filename already starts with client ID to avoid duplication
        if base_filename.startswith(f"{client_id}-"):
            # Filename already has client prefix, use as-is
            secure_filename = f"{base_filename}{ext}"
            logger.debug(f"  - Filename already has client prefix, using as-is: {secure_filename}")
        else:
            # Format: CL-0001-bob.jpg (client ID + original filename)
            secure_filename = f"{client_id}-{base_filename}{ext}"
            logger.debug(f"  - Generated secure filename: {secure_filename}")
        return secure_filename
    else:
        # Fallback format with UUID for uniqueness
        secure_filename = f"{uuid_part}-{base_filename}{ext}"
        logger.debug(f"  - Generated fallback filename: {secure_filename}")
        return secure_filename

def is_allowed_file_type(filename: str) -> Tuple[bool, str]:
    """Check if file type is allowed based on extension. Returns (is_allowed, message)"""
    allowed_extensions = {
        '.doc', '.docx', '.gif', '.html', '.jpeg', '.jpg', '.heic',
        '.lgb', '.msg', '.pdf', '.png', '.qb1', '.rtf', '.tiff', '.xml'
    }
    ext = os.path.splitext(filename.lower())[1]
    
    if ext in allowed_extensions:
        return True, "File type allowed"
    else:
        allowed_list = ", ".join(sorted(allowed_extensions))
        return False, f"File type '{ext}' is not allowed. Allowed types are: {allowed_list}"

def is_file_size_allowed(size: int) -> Tuple[bool, str]:
    """Check if file size is within allowed limits (50MB). Returns (is_allowed, message)"""
    max_size = settings.max_file_size
    if size <= max_size:
        return True, "File size acceptable"
    else:
        max_mb = max_size / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        return False, f"File size ({actual_mb:.1f}MB) exceeds maximum allowed size of {max_mb:.0f}MB"

def convert_heic_to_png(content: bytes, max_dimension: int = 2048, quality: int = 85) -> Tuple[bytes, str]:
    """Convert HEIC image to PNG format with optimizations for speed. Returns (png_content, new_extension)"""
    logger.debug(f"convert_heic_to_png called with content size: {len(content)} bytes")
    logger.debug(f"pillow-heif available: {_HEIF_AVAILABLE}")
    logger.debug(f"Max dimension: {max_dimension}, Quality: {quality}")
    
    if not _HEIF_AVAILABLE:
        logger.debug("pillow-heif not available, returning original content")
        # If pillow-heif is not available, return original content
        return content, '.heic'
    
    try:
        logger.debug("Opening HEIC image with Pillow...")
        # Open HEIC image using pillow-heif
        image = Image.open(io.BytesIO(content))
        original_size = image.size
        logger.debug(f"Image opened successfully - mode: {image.mode}, size: {original_size}")
        
        # Resize if image is too large (major speed improvement)
        if max(original_size) > max_dimension:
            logger.debug(f"Resizing image from {original_size} to max {max_dimension}px")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            logger.debug(f"Resized to: {image.size}")
        
        # Convert to RGB if necessary (HEIC can be in different color spaces)
        if image.mode != 'RGB':
            logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert('RGB')
        
        # Save as PNG with optimized settings for speed
        logger.debug("Saving image as PNG with optimized settings...")
        png_buffer = io.BytesIO()
        
        # Use optimized PNG settings for speed vs quality balance
        png_settings = {
            'format': 'PNG',
            'optimize': False,  # Disable optimization for speed
            'compress_level': 1,  # Fast compression (1-9, 1=fastest)
        }
        
        image.save(png_buffer, **png_settings)
        png_content = png_buffer.getvalue()
        
        compression_ratio = len(content) / len(png_content) if len(png_content) > 0 else 1
        logger.debug(f"PNG conversion successful - output size: {len(png_content)} bytes")
        logger.debug(f"Compression ratio: {compression_ratio:.2f}x")
        return png_content, '.png'
    except Exception as e:
        logger.error(f"HEIC conversion failed with error: {str(e)}")
        # If conversion fails, return original content
        return content, '.heic'

def convert_heic_to_jpeg(content: bytes, max_dimension: int = 2048, quality: int = 85) -> Tuple[bytes, str]:
    """Convert HEIC image to JPEG format with optimizations for maximum speed. Returns (jpeg_content, new_extension)"""
    logger.debug(f"convert_heic_to_jpeg called with content size: {len(content)} bytes")
    logger.debug(f"pillow-heif available: {_HEIF_AVAILABLE}")
    logger.debug(f"Max dimension: {max_dimension}, Quality: {quality}")
    
    if not _HEIF_AVAILABLE:
        logger.debug("pillow-heif not available, returning original content")
        return content, '.heic'
    
    try:
        logger.debug("Opening HEIC image with Pillow...")
        image = Image.open(io.BytesIO(content))
        original_size = image.size
        logger.debug(f"Image opened successfully - mode: {image.mode}, size: {original_size}")
        
        # Resize if image is too large (major speed improvement)
        if max(original_size) > max_dimension:
            logger.debug(f"Resizing image from {original_size} to max {max_dimension}px")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            logger.debug(f"Resized to: {image.size}")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert('RGB')
        
        # Save as JPEG with optimized settings for maximum speed
        logger.debug("Saving image as JPEG with optimized settings...")
        jpeg_buffer = io.BytesIO()
        
        # Use optimized JPEG settings for speed
        jpeg_settings = {
            'format': 'JPEG',
            'quality': quality,  # 85 is good balance of speed/quality
            'optimize': False,   # Disable optimization for speed
            'progressive': False, # Disable progressive for speed
        }
        
        image.save(jpeg_buffer, **jpeg_settings)
        jpeg_content = jpeg_buffer.getvalue()
        
        compression_ratio = len(content) / len(jpeg_content) if len(jpeg_content) > 0 else 1
        logger.debug(f"JPEG conversion successful - output size: {len(jpeg_content)} bytes")
        logger.debug(f"Compression ratio: {compression_ratio:.2f}x")
        return jpeg_content, '.jpg'
    except Exception as e:
        logger.error(f"HEIC conversion failed with error: {str(e)}")
        return content, '.heic'

async def convert_heic_async(content: bytes, max_dimension: int = 2048, quality: int = 85, use_jpeg: bool = True) -> Tuple[bytes, str]:
    """Async wrapper for HEIC conversion to prevent blocking the main thread"""
    logger.debug("Starting async HEIC conversion...")
    
    # Run the conversion in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    
    if use_jpeg:
        result = await loop.run_in_executor(
            None, 
            convert_heic_to_jpeg, 
            content, 
            max_dimension, 
            quality
        )
    else:
        result = await loop.run_in_executor(
            None, 
            convert_heic_to_png, 
            content, 
            max_dimension, 
            quality
        )
    
    logger.debug("Async HEIC conversion completed")
    return result

def get_file_category_from_context(debt_type: Optional[str] = None, 
                                 asset_type: Optional[str] = None,
                                 income_type: Optional[str] = None,
                                 expenditure_type: Optional[str] = None) -> str:
    """Determine file category based on context"""
    if debt_type:
        return "debt_document"
    elif asset_type:
        return "asset_document"
    elif income_type:
        return "income_document"
    elif expenditure_type:
        return "expenditure_document"
    else:
        return "other"

async def save_uploaded_file(
    file: UploadFile,
    case_id: str,
    uploaded_by_id: str,
    client_id: Optional[str] = None,
    encrypt: bool = True,
    category: str = "other"
) -> Tuple[str, dict]:
    """
    Save uploaded file securely with HEIC conversion and client ID prefixing
    Returns (file_path, file_metadata)
    """
    logger.debug(f"save_uploaded_file called with:")
    logger.debug(f"  - original_filename: {file.filename}")
    logger.debug(f"  - case_id: {case_id}")
    logger.debug(f"  - client_id: {client_id}")
    logger.debug(f"  - category: {category}")
    
    # Read file content
    content = await file.read()
    original_filename = file.filename
    logger.debug(f"File content read - size: {len(content)} bytes")
    
    # Validate file type
    is_allowed, type_message = is_allowed_file_type(original_filename)
    logger.debug(f"File type validation: {is_allowed} - {type_message}")
    if not is_allowed:
        raise ValueError(type_message)
    
    # Validate file size
    is_size_ok, size_message = is_file_size_allowed(len(content))
    logger.debug(f"File size validation: {is_size_ok} - {size_message}")
    if not is_size_ok:
        raise ValueError(size_message)
    
    # Handle HEIC conversion
    file_extension = os.path.splitext(original_filename)[1].lower()
    logger.debug(f"File extension detected: {file_extension}")
    
    if file_extension == '.heic':
        logger.debug("HEIC file detected, starting conversion...")
        try:
            # Use async conversion for large files to prevent blocking
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > 5:  # Use async for files larger than 5MB
                logger.debug(f"Large file detected ({file_size_mb:.1f}MB), using async conversion...")
                content, file_extension = await convert_heic_async(
                    content,
                    max_dimension=settings.heic_max_dimension,
                    quality=settings.heic_quality,
                    use_jpeg=settings.heic_use_jpeg
                )
            else:
                logger.debug(f"Small file ({file_size_mb:.1f}MB), using sync conversion...")
                # Use configurable conversion settings for speed optimization
                if settings.heic_use_jpeg:
                    # Use JPEG for maximum speed (much faster than PNG)
                    content, file_extension = convert_heic_to_jpeg(
                        content, 
                        max_dimension=settings.heic_max_dimension, 
                        quality=settings.heic_quality
                    )
                else:
                    # Use PNG for quality (slower but lossless)
                    content, file_extension = convert_heic_to_png(
                        content, 
                        max_dimension=settings.heic_max_dimension, 
                        quality=settings.heic_quality
                    )
            
            # Determine converted extension
            converted_ext = '.jpg' if settings.heic_use_jpeg else '.png'
            
            # Update filename to reflect conversion
            base_name = os.path.splitext(original_filename)[0]
            converted_filename = f"{base_name}{converted_ext}"
            logger.debug(f"HEIC conversion completed, new filename: {converted_filename}")
            logger.debug(f"Conversion settings - Max dimension: {settings.heic_max_dimension}, Quality: {settings.heic_quality}, Format: {'JPEG' if settings.heic_use_jpeg else 'PNG'}")
        except ValueError as e:
            logger.error(f"HEIC conversion failed: {str(e)}")
            raise ValueError(f"HEIC conversion failed: {str(e)}")
    else:
        converted_filename = original_filename
        logger.debug(f"No conversion needed, using original filename: {converted_filename}")
    
    # Generate secure filename with client ID prefix
    logger.debug("Generating secure filename...")
    secure_filename = generate_secure_filename(converted_filename, client_id)
    
    # Create directory structure: uploads/case_id/
    relative_path = os.path.join(case_id[:2], case_id)  # Use first 2 chars for distribution
    full_dir = os.path.join(settings.upload_dir, relative_path)
    logger.debug(f"Creating directory structure: {full_dir}")
    os.makedirs(full_dir, exist_ok=True)
    
    file_path = os.path.join(full_dir, secure_filename)
    logger.debug(f"Full file path: {file_path}")
    
    # Get file hash before encryption
    file_hash = get_file_hash(content)
    logger.debug(f"File hash generated: {file_hash[:16]}...")
    
    # Encrypt content if required
    encryption_key = None
    if encrypt:
        logger.debug("Encrypting file content...")
        encryption_key = generate_encryption_key()
        content = encrypt_file_content(content, encryption_key)
        logger.debug(f"File encrypted, new size: {len(content)} bytes")
    
    # Save file
    logger.debug("Writing file to disk...")
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    logger.debug("File saved successfully")
    
    metadata = {
        'original_filename': original_filename,
        'stored_filename': secure_filename,
        'file_path': os.path.join(relative_path, secure_filename),
        'file_size': len(content),
        'file_extension': file_extension,
        'mime_type': get_file_mime_type(content) if not encrypt else 'application/octet-stream',
        'file_hash': file_hash,
        'is_encrypted': encrypt,
        'encryption_key': encryption_key.decode() if encryption_key else None,
        'category': category,
        'was_converted': file_extension in ['.png', '.jpg'] and original_filename.lower().endswith('.heic')
    }
    
    logger.info(f"File upload completed successfully:")
    logger.info(f"  - Original filename: {metadata['original_filename']}")
    logger.info(f"  - Stored filename: {metadata['stored_filename']}")
    logger.info(f"  - File size: {metadata['file_size']} bytes")
    logger.info(f"  - Was converted: {metadata['was_converted']}")
    
    return file_path, metadata

async def read_uploaded_file(file_path: str, encryption_key: Optional[str] = None) -> bytes:
    """Read and decrypt uploaded file if necessary"""
    async with aiofiles.open(file_path, 'rb') as f:
        content = await f.read()
    
    if encryption_key:
        content = decrypt_file_content(content, encryption_key.encode())
    
    return content

def delete_file(file_path: str) -> bool:
    """Safely delete file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

def get_upload_requirements() -> dict:
    """Get file upload requirements for frontend"""
    return {
        'max_file_size': settings.max_file_size,
        'max_file_size_mb': settings.max_file_size / (1024 * 1024),
        'allowed_extensions': settings.allowed_extensions,
        'allowed_mime_types': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/heic',
            'image/tiff',
            'text/html',
            'text/rtf',
            'application/xml',
            'text/xml'
        ]
    }

# File validation utilities
def validate_file_content(content: bytes, expected_mime: str) -> bool:
    """Validate file content matches expected MIME type"""
    actual_mime = get_file_mime_type(content)
    return actual_mime == expected_mime

def scan_file_for_threats(content: bytes) -> dict:
    """
    Enhanced file threat scanning with additional security checks
    In production, this would integrate with antivirus API
    """
    threats = []
    
    # Check for executable content in uploads
    if b'MZ' in content[:100]:  # PE header
        threats.append("Executable file detected")
    
    if b'#!/' in content[:100]:  # Script shebangs
        threats.append("Script file detected")
    
    # Check for suspicious patterns
    suspicious_patterns = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'<?php',
        b'<%',
        b'eval(',
        b'exec(',
        b'system(',
        b'shell_exec(',
        b'base64_decode(',
        b'gzinflate(',
        b'str_rot13('
    ]
    
    for pattern in suspicious_patterns:
        if pattern in content.lower():
            threats.append(f"Suspicious pattern detected: {pattern.decode()}")
    
    # Check for embedded objects that could be malicious
    if b'<object' in content.lower() or b'<embed' in content.lower():
        threats.append("Embedded object detected")
    
    # Check for macro content in Office documents
    if b'VBA' in content or b'Macro' in content:
        threats.append("Macro content detected")
    
    # Check file size for potential DoS
    if len(content) > 100 * 1024 * 1024:  # 100MB
        threats.append("File size exceeds safe limit")
    
    return {
        'clean': len(threats) == 0,
        'threats': threats,
        'status': 'clean' if len(threats) == 0 else 'suspicious'
    }

def get_upload_requirements():
    """Get file upload requirements for frontend validation"""
    return {
        'allowed_extensions': [
            '.doc', '.docx', '.gif', '.html', '.jpeg', '.jpg', '.heic',
            '.lgb', '.msg', '.pdf', '.png', '.qb1', '.rtf', '.tiff', '.xml'
        ],
        'max_file_size': 50 * 1024 * 1024,  # 50MB
        'max_file_size_formatted': '50 MB',
        'allowed_mime_types': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/tiff',
            'image/heic',
            'text/html',
            'text/rtf',
            'text/xml',
            'application/rtf'
        ]
    }

async def create_files_zip(file_records: List, upload_dir: str) -> bytes:
    """
    Create a ZIP file containing all specified files
    Returns ZIP file content as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_record in file_records:
            try:
                full_file_path = os.path.join(upload_dir, file_record.file_path)
                
                if os.path.exists(full_file_path):
                    # Read file content (decrypt if necessary)
                    file_content = await read_uploaded_file(
                        full_file_path, 
                        file_record.encryption_key_id if file_record.is_encrypted else None
                    )
                    
                    # Add to ZIP with stored filename (includes client prefix and proper naming)
                    display_filename = file_record.original_filename
                    if file_record.was_converted and file_record.original_filename.lower().endswith('.heic'):
                        # Show converted extension for HEIC files, but keep the client prefix from stored_filename
                        if file_record.stored_filename:
                            # Use the stored filename which already includes client prefix, just change the extension
                            base_name = os.path.splitext(file_record.stored_filename)[0]
                            converted_ext = os.path.splitext(file_record.stored_filename)[1] if file_record.stored_filename else '.jpg'
                            display_filename = f"{base_name}{converted_ext}"
                        else:
                            # Fallback to original filename if no stored filename
                            base_name = os.path.splitext(file_record.original_filename)[0]
                            display_filename = f"{base_name}.jpg"
                    elif file_record.stored_filename:
                        # Use stored filename which includes client prefix
                        display_filename = file_record.stored_filename
                    
                    zip_file.writestr(display_filename, file_content)
                else:
                    # Add placeholder for missing files
                    display_filename = file_record.stored_filename or file_record.original_filename
                    zip_file.writestr(
                        f"MISSING_{display_filename}.txt", 
                        f"File '{display_filename}' was not found on disk."
                    )
            except Exception as e:
                # Add error info for failed files
                display_filename = file_record.stored_filename or file_record.original_filename
                zip_file.writestr(
                    f"ERROR_{display_filename}.txt",
                    f"Failed to process '{display_filename}': {str(e)}"
                )
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def get_client_id_from_user(user) -> Optional[str]:
    """Extract client ID from user object for file naming"""
    logger.debug(f"get_client_id_from_user called for user: {user.email if hasattr(user, 'email') else 'unknown'}")
    logger.debug(f"User role: {user.role if hasattr(user, 'role') else 'unknown'}")
    logger.debug(f"User ca_client_number: {user.ca_client_number if hasattr(user, 'ca_client_number') else 'None'}")
    
    # Check if user has a client number and is a client
    # Handle both string and enum role values
    user_role = None
    if hasattr(user, 'role'):
        if hasattr(user.role, 'value'):  # It's an enum
            user_role = user.role.value
        else:  # It's a string
            user_role = str(user.role)
    
    logger.debug(f"User role as string: {user_role}")
    logger.debug(f"Role comparison: {user_role and user_role.upper() == 'CLIENT'}")
    
    if (hasattr(user, 'ca_client_number') and user.ca_client_number and 
        user_role and user_role.upper() == 'CLIENT'):
        logger.debug(f"Using ca_client_number: {user.ca_client_number}")
        return user.ca_client_number
    elif hasattr(user, 'id'):
        # Fallback to user ID if no client number or not a client
        fallback_id = f"USER-{user.id}"
        logger.debug(f"Using fallback USER-ID: {fallback_id}")
        return fallback_id
    logger.debug("No valid client ID found")
    return None

async def delete_case_files(case_id: str, db_session) -> dict:
    """
    Delete all files associated with a case from both database and storage.
    Returns a summary of the deletion operation.
    """
    from ..models.file_upload import FileUpload
    
    deletion_summary = {
        "files_found": 0,
        "files_deleted": 0,
        "files_failed": 0,
        "storage_errors": [],
        "deleted_files": []
    }
    
    try:
        # Get all file records for this case
        file_records = db_session.query(FileUpload).filter(
            FileUpload.case_id == case_id
        ).all()
        
        deletion_summary["files_found"] = len(file_records)
        
        for file_record in file_records:
            try:
                # Construct full file path
                full_file_path = os.path.join(settings.upload_dir, file_record.file_path)
                
                # Delete file from storage
                if os.path.exists(full_file_path):
                    if delete_file(full_file_path):
                        deletion_summary["files_deleted"] += 1
                        deletion_summary["deleted_files"].append({
                            "id": file_record.id,
                            "original_filename": file_record.original_filename,
                            "file_path": file_record.file_path
                        })
                    else:
                        deletion_summary["files_failed"] += 1
                        deletion_summary["storage_errors"].append(
                            f"Failed to delete file: {file_record.original_filename}"
                        )
                else:
                    # File doesn't exist in storage, but record exists in DB
                    deletion_summary["files_deleted"] += 1
                    deletion_summary["deleted_files"].append({
                        "id": file_record.id,
                        "original_filename": file_record.original_filename,
                        "file_path": file_record.file_path,
                        "note": "File not found in storage"
                    })
                
                # Delete database record
                db_session.delete(file_record)
                
            except Exception as e:
                deletion_summary["files_failed"] += 1
                deletion_summary["storage_errors"].append(
                    f"Error processing file {file_record.original_filename}: {str(e)}"
                )
        
        # Try to remove the case directory and parent directories if they're empty
        try:
            case_dir = os.path.join(settings.upload_dir, case_id[:2], case_id)
            parent_dir = os.path.join(settings.upload_dir, case_id[:2])
            
            # Remove case directory if it exists and is empty
            if os.path.exists(case_dir):
                if not os.listdir(case_dir):
                    os.rmdir(case_dir)
                    deletion_summary["case_directory_removed"] = True
                    logger.debug(f"Removed empty case directory: {case_dir}")
                else:
                    deletion_summary["case_directory_removed"] = False
                    deletion_summary["case_directory_note"] = "Directory not empty, left in place"
                    logger.debug(f"Case directory not empty, left in place: {case_dir}")
            else:
                deletion_summary["case_directory_removed"] = False
                deletion_summary["case_directory_note"] = "Case directory does not exist"
                logger.debug(f"Case directory does not exist: {case_dir}")
            
            # Remove parent directory if it exists and is empty (but never delete the uploads folder itself)
            if os.path.exists(parent_dir) and parent_dir != settings.upload_dir:
                if not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    deletion_summary["parent_directory_removed"] = True
                    logger.debug(f"Removed empty parent directory: {parent_dir}")
                else:
                    deletion_summary["parent_directory_removed"] = False
                    deletion_summary["parent_directory_note"] = "Parent directory not empty, left in place"
                    logger.debug(f"Parent directory not empty, left in place: {parent_dir}")
            elif parent_dir == settings.upload_dir:
                deletion_summary["parent_directory_removed"] = False
                deletion_summary["parent_directory_note"] = "Skipped - uploads root directory should not be deleted"
                logger.debug(f"Skipped deletion of uploads root directory: {parent_dir}")
            else:
                deletion_summary["parent_directory_removed"] = False
                deletion_summary["parent_directory_note"] = "Parent directory does not exist"
                logger.debug(f"Parent directory does not exist: {parent_dir}")
                
        except Exception as e:
            deletion_summary["case_directory_removed"] = False
            deletion_summary["parent_directory_removed"] = False
            deletion_summary["directory_cleanup_error"] = str(e)
            logger.error(f"Error during directory cleanup: {str(e)}")
        
        return deletion_summary
        
    except Exception as e:
        deletion_summary["error"] = f"Failed to delete case files: {str(e)}"
        return deletion_summary
