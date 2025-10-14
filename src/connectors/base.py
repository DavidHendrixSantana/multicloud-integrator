"""
Base classes and exceptions for cloud storage connectors.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GCP_STORAGE = "gcp_storage"

@dataclass
class FileInfo:
    """Information about a file in cloud storage."""
    name: str
    size: int
    last_modified: str
    etag: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TransferResult:
    """Result of a file transfer operation."""
    success: bool
    source_path: str
    destination_path: str
    bytes_transferred: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None

class CloudStorageError(Exception):
    """Base exception for cloud storage operations."""
    pass

class AuthenticationError(CloudStorageError):
    """Exception raised when authentication fails."""
    pass

class ConnectionError(CloudStorageError):
    """Exception raised when connection fails."""
    pass

class FileNotFoundError(CloudStorageError):
    """Exception raised when file is not found."""
    pass

class PermissionError(CloudStorageError):
    """Exception raised when permission is denied."""
    pass

class CloudStorageConnector(ABC):
    """Abstract base class for cloud storage connectors."""
    
    def __init__(self, provider: CloudProvider):
        self.provider = provider
        self._client = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the cloud provider."""
        pass
    
    @abstractmethod
    def list_files(self, container: str, prefix: str = "") -> List[FileInfo]:
        """List files in a container/bucket."""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, container: str, remote_path: str, **kwargs) -> TransferResult:
        """Upload a file to cloud storage."""
        pass
    
    @abstractmethod
    def download_file(self, container: str, remote_path: str, local_path: str, **kwargs) -> TransferResult:
        """Download a file from cloud storage."""
        pass
    
    @abstractmethod
    def copy_file(self, source_container: str, source_path: str, 
                 dest_container: str, dest_path: str, **kwargs) -> TransferResult:
        """Copy a file within the same cloud provider."""
        pass
    
    @abstractmethod
    def delete_file(self, container: str, remote_path: str) -> bool:
        """Delete a file from cloud storage."""
        pass
    
    @abstractmethod
    def file_exists(self, container: str, remote_path: str) -> bool:
        """Check if a file exists in cloud storage."""
        pass
    
    @abstractmethod
    def get_file_info(self, container: str, remote_path: str) -> FileInfo:
        """Get information about a file."""
        pass
    
    def test_connection(self) -> bool:
        """Test the connection to the cloud provider."""
        try:
            return self.authenticate()
        except Exception:
            return False
