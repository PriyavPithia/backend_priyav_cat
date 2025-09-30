"""
AWS S3 configuration for file storage
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)


class S3Config:
    """S3 configuration and client management."""
    
    def __init__(self):
        from .settings import settings
        
        self.aws_access_key_id = settings.aws_access_key_id
        self.aws_secret_access_key = settings.aws_secret_access_key
        self.aws_region = settings.aws_region
        self.bucket_name = settings.s3_bucket_name
        self.endpoint_url = settings.s3_endpoint_url
        self.use_s3_storage = settings.use_s3_storage
        
        self._client = None
        self._is_available = None
    
    @property
    def client(self):
        """Get or create S3 client"""
        if self._client is None:
            try:
                from botocore.config import Config
                
                # Force regional endpoint and disable global endpoint usage
                s3_config = Config(
                    region_name=self.aws_region,
                    s3={
                        'addressing_style': 'virtual',
                        'signature_version': 's3v4',
                        'use_accelerate_endpoint': False,
                        'use_dualstack_endpoint': False
                    },
                    # Disable global endpoint fallback
                    parameter_validation=True
                )
                
                # Use regional endpoint URL explicitly
                regional_endpoint = f"https://s3.{self.aws_region}.amazonaws.com"
                
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region,
                    endpoint_url=regional_endpoint,  # Force regional endpoint
                    config=s3_config
                )
                
                logger.info(f"S3 client configured with regional endpoint: {regional_endpoint}")
                
            except Exception as e:
                logger.error(f"Failed to create S3 client: {e}")
                raise
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if S3 is available and properly configured"""
        if not self.use_s3_storage:
            logger.info("S3 storage is disabled via USE_S3_STORAGE setting")
            return False
            
        if self._is_available is None:
            try:
                if not all([self.aws_access_key_id,
                           self.aws_secret_access_key,
                           self.bucket_name]):
                    self._is_available = False
                    logger.warning(
                        "S3 credentials or bucket name not configured"
                    )
                else:
                    # Test connection by listing bucket
                    self.client.head_bucket(Bucket=self.bucket_name)
                    self._is_available = True
                    logger.info(
                        f"S3 bucket '{self.bucket_name}' is accessible"
                    )
            except NoCredentialsError:
                self._is_available = False
                logger.error("AWS credentials not found")
            except ClientError as e:
                self._is_available = False
                logger.error(
                    f"S3 bucket '{self.bucket_name}' not accessible: {e}"
                )
            except Exception as e:
                self._is_available = False
                logger.error(f"S3 availability check failed: {e}")
        
        return self._is_available


# Global S3 configuration instance
s3_config = S3Config()