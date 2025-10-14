"""
Configuration management for the multi-cloud CLI tool.
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    """Application configuration class."""
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    
    # Azure Configuration
    azure_storage_account_name: Optional[str] = None
    azure_storage_account_key: Optional[str] = None
    azure_storage_connection_string: Optional[str] = None
    
    # Google Cloud Configuration
    google_application_credentials: Optional[str] = None
    google_cloud_project_id: Optional[str] = None
    
    # Application Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    max_retries: int = 3
    retry_delay: int = 2
    chunk_size: int = 8 * 1024 * 1024  # 8MB
    timeout: int = 300  # 5 minutes
    
    # Optional encryption
    encryption_key: Optional[str] = None
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        # Load .env file if it exists
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
        
        # AWS Configuration
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", self.aws_access_key_id)
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", self.aws_secret_access_key)
        self.aws_default_region = os.getenv("AWS_DEFAULT_REGION", self.aws_default_region)
        
        # Azure Configuration
        self.azure_storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", self.azure_storage_account_name)
        self.azure_storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", self.azure_storage_account_key)
        self.azure_storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", self.azure_storage_connection_string)
        
        # Google Cloud Configuration
        self.google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", self.google_application_credentials)
        self.google_cloud_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", self.google_cloud_project_id)
        
        # Application Configuration
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_format = os.getenv("LOG_FORMAT", self.log_format)
        self.max_retries = int(os.getenv("MAX_RETRIES", str(self.max_retries)))
        self.retry_delay = int(os.getenv("RETRY_DELAY", str(self.retry_delay)))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", str(self.chunk_size)))
        self.timeout = int(os.getenv("TIMEOUT", str(self.timeout)))
        
        # Optional encryption
        self.encryption_key = os.getenv("ENCRYPTION_KEY", self.encryption_key)
    
    def validate_aws_config(self) -> bool:
        """Validate AWS configuration."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)
    
    def validate_azure_config(self) -> bool:
        """Validate Azure configuration."""
        return bool(
            self.azure_storage_connection_string or 
            (self.azure_storage_account_name and self.azure_storage_account_key)
        )
    
    def validate_gcp_config(self) -> bool:
        """Validate Google Cloud configuration."""
        return bool(
            self.google_application_credentials and 
            self.google_cloud_project_id and
            Path(self.google_application_credentials).exists()
        )

# Global configuration instance
config = Config()
