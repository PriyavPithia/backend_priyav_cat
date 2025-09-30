"""
AWS S3 utilities for file operations
"""
import os
import uuid
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
import logging
from ..config.s3 import s3_config

logger = logging.getLogger(__name__)


class S3FileHandler:
    """Handle S3 file operations"""
    
    def __init__(self):
        self.config = s3_config
    
    def generate_s3_key(
            self, 
            client_id: str, 
            filename: str, 
            category: str = "general"
    ) -> str:
        """Generate S3 object key with proper structure"""
        # Create a unique filename to avoid conflicts
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Structure: client_id/category/unique_filename
        return f"{client_id}/{category}/{unique_filename}"
    
    def upload_file(
        self, 
        file_obj: BinaryIO, 
        s3_key: str, 
        content_type: str = 'application/octet-stream'
    ) -> bool:
        """
        Upload file to S3
        
        Args:
            file_obj: File object to upload
            s3_key: S3 object key
            content_type: MIME type of the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config.is_available:
            logger.error("S3 is not available for upload")
            return False
        
        try:
            # Reset file pointer to beginning
            file_obj.seek(0)
            
            # Upload with proper metadata
            self.config.client.upload_fileobj(
                file_obj,
                self.config.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256',  # Encrypt at rest
                    'Metadata': {
                        'uploaded-by': 'ca-tadley-debt-tool'
                    }
                }
            )
            
            logger.info(f"File uploaded to S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False
    
    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bytes: File content if successful, None otherwise
        """
        if not self.config.is_available:
            logger.error("S3 is not available for download")
            return None
        
        try:
            response = self.config.client.get_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read()
            logger.info(f"File downloaded from S3: {s3_key}")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return None
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config.is_available:
            logger.error("S3 is not available for deletion")
            return False
        
        try:
            self.config.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"File deleted from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3: {e}")
            return False
    
    def generate_presigned_url(
            self, 
            s3_key: str, 
            expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary file access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL if successful, None otherwise
        """
        if not self.config.is_available:
            logger.error(
                "S3 is not available for presigned URL generation"
            )
            return None
        
        try:
            # Generate presigned URL with regional client
            url = self.config.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.config.bucket_name, 
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            if url and 's3.amazonaws.com' in url and f's3.{self.config.aws_region}.amazonaws.com' not in url:
                regional_endpoint = f"s3.{self.config.aws_region}.amazonaws.com"
                url = url.replace('s3.amazonaws.com', regional_endpoint)
                logger.info(f"Forced regional endpoint in presigned URL: {regional_endpoint}")
            
            logger.info(f"Presigned URL generated for: {s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bool: True if file exists, False otherwise
        """
        if not self.config.is_available:
            return False
        
        try:
            self.config.client.head_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {e}")
            return False


# Global S3 file handler instance
s3_handler = S3FileHandler()