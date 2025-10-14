"""
Azure Blob Storage connector implementation.
"""
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import (
    ResourceNotFoundError,
    ClientAuthenticationError,
    HttpResponseError,
    AzureError
)
import structlog

from .base import (
    CloudStorageConnector, 
    CloudProvider, 
    FileInfo, 
    TransferResult,
    AuthenticationError,
    ConnectionError,
    FileNotFoundError,
    PermissionError,
    CloudStorageError
)
from config import config
from utils import with_retry, format_bytes
from logger import log_operation_start, log_operation_success, log_operation_error

logger = structlog.get_logger()

class AzureBlobConnector(CloudStorageConnector):
    """Azure Blob Storage connector."""
    
    def __init__(self):
        super().__init__(CloudProvider.AZURE_BLOB)
        self._blob_service_client = None
    
    def authenticate(self) -> bool:
        """Authenticate with Azure Blob Storage."""
        try:
            if not config.validate_azure_config():
                raise AuthenticationError("Azure Blob Storage credentials not configured properly")
            
            # Create BlobServiceClient using connection string or account key
            if config.azure_storage_connection_string:
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    config.azure_storage_connection_string
                )
            else:
                account_url = f"https://{config.azure_storage_account_name}.blob.core.windows.net"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=config.azure_storage_account_key
                )
            
            # Test authentication by listing containers
            containers_iter = self._blob_service_client.list_containers()
            containers = []
            # Get only first container for testing
            for i, container in enumerate(containers_iter):
                if i >= 1:  # Limit to 1 container for testing
                    break
                containers.append(container)
            
            logger.info("Azure Blob Storage authentication successful")
            return True
            
        except ClientAuthenticationError as e:
            raise AuthenticationError(f"Azure authentication failed: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Azure connection failed: {str(e)}")
    
    @with_retry()
    def list_files(self, container: str, prefix: str = "") -> List[FileInfo]:
        """List files in an Azure Blob container."""
        if not self._blob_service_client:
            self.authenticate()
        
        try:
            container_client = self._blob_service_client.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            
            files = []
            for blob in blobs:
                file_info = FileInfo(
                    name=blob.name,
                    size=blob.size,
                    last_modified=blob.last_modified.isoformat(),
                    etag=blob.etag.strip('"') if blob.etag else None,
                    content_type=blob.content_settings.content_type if blob.content_settings else None,
                    metadata=blob.metadata or {}
                )
                files.append(file_info)
            
            logger.info(f"Listed {len(files)} files from Azure container", container=container, prefix=prefix)
            return files
            
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Azure container '{container}' not found")
        except HttpResponseError as e:
            if e.status_code == 403:
                raise PermissionError(f"Access denied to Azure container '{container}'")
            else:
                raise CloudStorageError(f"Azure list error: {str(e)}")
    
    @with_retry()
    def upload_file(self, local_path: str, container: str, remote_path: str, **kwargs) -> TransferResult:
        """Upload a file to Azure Blob Storage."""
        if not self._blob_service_client:
            self.authenticate()
        
        start_time = time.time()
        local_file = Path(local_path)
        
        if not local_file.exists():
            raise FileNotFoundError(f"Local file '{local_path}' not found")
        
        file_size = local_file.stat().st_size
        
        log_operation_start(
            "azure_upload",
            local_path=local_path,
            container=container,
            remote_path=remote_path,
            size_bytes=file_size
        )
        
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=container,
                blob=remote_path
            )
            
            # Upload with additional options from kwargs
            blob_properties = kwargs.get('blob_properties', {})
            metadata = kwargs.get('metadata', {})
            
            with open(local_path, 'rb') as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    metadata=metadata,
                    **blob_properties
                )
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=local_path,
                destination_path=f"azure://{container}/{remote_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "azure_upload",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Azure upload failed: {str(e)}"
            log_operation_error("azure_upload", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=local_path,
                destination_path=f"azure://{container}/{remote_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def download_file(self, container: str, remote_path: str, local_path: str, **kwargs) -> TransferResult:
        """Download a file from Azure Blob Storage."""
        if not self._blob_service_client:
            self.authenticate()
        
        start_time = time.time()
        
        # Create local directory if it doesn't exist
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_operation_start(
            "azure_download",
            container=container,
            remote_path=remote_path,
            local_path=local_path
        )
        
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=container,
                blob=remote_path
            )
            
            # Get blob properties for size
            properties = blob_client.get_blob_properties()
            file_size = properties.size
            
            # Download blob
            with open(local_path, 'wb') as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"azure://{container}/{remote_path}",
                destination_path=local_path,
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "azure_download",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except ResourceNotFoundError:
            error_msg = f"File 'azure://{container}/{remote_path}' not found"
            log_operation_error("azure_download", FileNotFoundError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"azure://{container}/{remote_path}",
                destination_path=local_path,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Azure download failed: {str(e)}"
            log_operation_error("azure_download", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"azure://{container}/{remote_path}",
                destination_path=local_path,
                error_message=error_msg
            )
    
    @with_retry()
    def copy_file(self, source_container: str, source_path: str, 
                 dest_container: str, dest_path: str, **kwargs) -> TransferResult:
        """Copy a blob within Azure or between containers."""
        if not self._blob_service_client:
            self.authenticate()
        
        start_time = time.time()
        
        log_operation_start(
            "azure_copy",
            source_container=source_container,
            source_path=source_path,
            dest_container=dest_container,
            dest_path=dest_path
        )
        
        try:
            # Get source blob client
            source_blob_client = self._blob_service_client.get_blob_client(
                container=source_container,
                blob=source_path
            )
            
            # Get source blob properties for size
            source_properties = source_blob_client.get_blob_properties()
            file_size = source_properties.size
            
            # Get destination blob client
            dest_blob_client = self._blob_service_client.get_blob_client(
                container=dest_container,
                blob=dest_path
            )
            
            # Copy blob
            source_url = source_blob_client.url
            dest_blob_client.start_copy_from_url(source_url)
            
            # Wait for copy to complete
            copy_properties = dest_blob_client.get_blob_properties()
            while copy_properties.copy.status == 'pending':
                time.sleep(1)
                copy_properties = dest_blob_client.get_blob_properties()
            
            if copy_properties.copy.status != 'success':
                raise CloudStorageError(f"Copy failed with status: {copy_properties.copy.status}")
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"azure://{source_container}/{source_path}",
                destination_path=f"azure://{dest_container}/{dest_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success("azure_copy", duration=duration, bytes_transferred=file_size)
            return result
            
        except Exception as e:
            error_msg = f"Azure copy failed: {str(e)}"
            log_operation_error("azure_copy", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"azure://{source_container}/{source_path}",
                destination_path=f"azure://{dest_container}/{dest_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def delete_file(self, container: str, remote_path: str) -> bool:
        """Delete a blob from Azure Blob Storage."""
        if not self._blob_service_client:
            self.authenticate()
        
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=container,
                blob=remote_path
            )
            blob_client.delete_blob()
            logger.info("File deleted from Azure", container=container, blob=remote_path)
            return True
            
        except Exception as e:
            logger.error("Azure delete failed", error=str(e), container=container, blob=remote_path)
            return False
    
    def file_exists(self, container: str, remote_path: str) -> bool:
        """Check if a blob exists in Azure Blob Storage."""
        if not self._blob_service_client:
            self.authenticate()
        
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=container,
                blob=remote_path
            )
            return blob_client.exists()
        except Exception:
            return False
    
    def get_file_info(self, container: str, remote_path: str) -> FileInfo:
        """Get information about a blob in Azure Blob Storage."""
        if not self._blob_service_client:
            self.authenticate()
        
        try:
            blob_client = self._blob_service_client.get_blob_client(
                container=container,
                blob=remote_path
            )
            properties = blob_client.get_blob_properties()
            
            return FileInfo(
                name=remote_path,
                size=properties.size,
                last_modified=properties.last_modified.isoformat(),
                etag=properties.etag.strip('"') if properties.etag else None,
                content_type=properties.content_settings.content_type if properties.content_settings else None,
                metadata=properties.metadata or {}
            )
            
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File 'azure://{container}/{remote_path}' not found")
        except Exception as e:
            raise CloudStorageError(f"Azure error: {str(e)}")
