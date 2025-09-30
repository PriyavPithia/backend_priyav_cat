"""
Optimized S3-First File Storage System
"""
import os
import uuid
from typing import Optional, BinaryIO, Tuple
import logging
from ..config.s3 import s3_config
from .s3_utils import s3_handler
from .file_utils import (
    generate_secure_filename, 
    get_file_hash,
    encrypt_file_content,
    decrypt_file_content,
    generate_encryption_key,
    get_file_mime_type
)
from ..config.settings import settings

logger = logging.getLogger(__name__)


class S3FirstFileStorage:
    """S3-first file storage with optional local backup only when needed"""
    
    def __init__(self):
        self.use_s3 = s3_handler and s3_handler.config.is_available
        self.backup_to_local = os.getenv("BACKUP_TO_LOCAL", "false").lower() == "true"
        
        if self.use_s3:
            logger.info("File storage mode: S3 Primary")
            if self.backup_to_local:
                logger.info("Local backup: Enabled")
            else:
                logger.info("Local backup: Disabled (S3-only)")
        else:
            logger.info("File storage mode: Local only (S3 unavailable)")
    
    async def save_file(
        self, 
        file, 
        case_id: str,
        uploaded_by_id: str,
        client_id: Optional[str] = None,
        encrypt: bool = True,
        category: str = "other"
    ) -> Tuple[bool, Optional[str], Optional[str], dict]:
        """
        Save file with S3-first approach
        
        Returns:
            tuple: (success, local_path, s3_key, metadata)
        """
        # Read file content once
        content = await file.read()
        original_filename = file.filename
        
        # Generate metadata
        file_hash = get_file_hash(content)
        secure_filename = generate_secure_filename(original_filename, client_id)
        
        # Handle encryption if required
        encryption_key = None
        if encrypt:
            encryption_key = generate_encryption_key()
            encrypted_content = encrypt_file_content(content, encryption_key)
        else:
            encrypted_content = content
        
        metadata = {
            'original_filename': original_filename,
            'stored_filename': secure_filename,
            'file_size': len(content),
            'file_extension': os.path.splitext(original_filename)[1].lower(),
            'mime_type': get_file_mime_type(content),
            'file_hash': file_hash,
            'is_encrypted': encrypt,
            'encryption_key': encryption_key.decode() if encryption_key else None,
            'category': category,
            'was_converted': False
        }
        
        s3_key = None
        local_path = None
        
        # Try S3 first (primary storage)
        if self.use_s3:
            try:
                import io
                s3_key = s3_handler.generate_s3_key(
                    client_id or case_id, 
                    original_filename, 
                    category
                )
                
                file_obj = io.BytesIO(encrypted_content)
                s3_success = s3_handler.upload_file(
                    file_obj, 
                    s3_key, 
                    metadata['mime_type']
                )
                
                if s3_success:
                    logger.info(f"File saved to S3: {original_filename}")
                    metadata['storage_type'] = 's3'
                    metadata['s3_key'] = s3_key
                    metadata['file_path'] = s3_key  
                    
                    # Only save locally if backup is enabled
                    if self.backup_to_local:
                        try:
                            local_path = await self._save_local_backup(
                                encrypted_content, case_id, secure_filename, metadata
                            )
                            logger.info(f"Local backup saved: {local_path}")
                        except Exception as e:
                            logger.warning(f"Local backup failed: {e}")
                    
                    return True, local_path, s3_key, metadata
                
            except Exception as e:
                logger.error(f"S3 upload failed: {e}")
        
        # Fallback to local storage only if S3 failed
        try:
            local_path = await self._save_local_fallback(
                encrypted_content, case_id, secure_filename, metadata
            )
            metadata['storage_type'] = 'local'
            metadata['file_path'] = os.path.relpath(local_path, settings.upload_dir)
            logger.info(f"File saved locally (fallback): {original_filename}")
            return True, local_path, None, metadata
            
        except Exception as e:
            logger.error(f"Both S3 and local storage failed: {e}")
            return False, None, None, metadata
    
    async def _save_local_backup(self, content: bytes, case_id: str, filename: str, metadata: dict) -> str:
        """Save local backup copy"""
        backup_dir = os.path.join(settings.upload_dir, "backup", case_id)
        os.makedirs(backup_dir, exist_ok=True)
        
        file_path = os.path.join(backup_dir, filename)
        
        import aiofiles
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return file_path
    
    async def _save_local_fallback(self, content: bytes, case_id: str, filename: str, metadata: dict) -> str:
        """Save to local storage as primary (fallback mode)"""
        case_dir = os.path.join(settings.upload_dir, case_id)
        os.makedirs(case_dir, exist_ok=True)
        
        file_path = os.path.join(case_dir, filename)
        
        import aiofiles
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return file_path
    
    def get_file(self, local_path: Optional[str], s3_key: Optional[str]) -> Optional[bytes]:
        """
        Get file content - S3-only storage
        """
        if not self.use_s3 or not s3_key:
            logger.error("S3 is not available or no S3 key provided")
            return None
            
        try:
            content = s3_handler.download_file(s3_key)
            if content:
                logger.debug(f"File retrieved from S3: {s3_key}")
                return content
            else:
                logger.error(f"Failed to download file from S3: {s3_key}")
                return None
        except Exception as e:
            logger.error(f"S3 download failed for {s3_key}: {e}")
            return None
    
    def delete_file(self, local_path: Optional[str], s3_key: Optional[str]) -> bool:
        """
        Delete file from storage(s)
        """
        success = True
        
        # Delete from S3 if exists
        if self.use_s3 and s3_key:
            try:
                s3_success = s3_handler.delete_file(s3_key)
                if not s3_success:
                    success = False
                    logger.warning(f"Failed to delete from S3: {s3_key}")
            except Exception as e:
                logger.error(f"S3 deletion error: {e}")
                success = False
        
        # Delete local file if exists (backup or fallback)
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Local file deleted: {local_path}")
            except Exception as e:
                logger.error(f"Local deletion failed: {e}")
                success = False
        
        return success
    
    def get_download_url(self, local_path: Optional[str], s3_key: Optional[str]) -> Optional[str]:
        """
        Get download URL - S3-only presigned URLs
        """
        if not self.use_s3 or not s3_key:
            logger.error("S3 is not available or no S3 key provided")
            return None
            
        try:
            logger.info(f"Checking S3 file existence for key: {s3_key}")
            if s3_handler.file_exists(s3_key):
                logger.info(f"S3 file exists, generating presigned URL for: {s3_key}")
                return s3_handler.generate_presigned_url(s3_key)
            else:
                logger.error(f"S3 file does not exist at key: {s3_key}")
                return None
        except Exception as e:
            logger.error(f"Error checking S3 file existence or generating presigned URL for {s3_key}: {e}")
            return None


# Create optimized storage instance
s3_first_storage = S3FirstFileStorage()