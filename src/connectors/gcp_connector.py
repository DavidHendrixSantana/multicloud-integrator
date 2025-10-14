"""
Google Cloud Storage connector implementation.
"""
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from google.cloud import storage
from google.cloud.exceptions import (
    NotFound,
    Forbidden,
    GoogleCloudError
)
from google.auth.exceptions import DefaultCredentialsError
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

class GCPStorageConnector(CloudStorageConnector):
    """Google Cloud Storage connector."""
    
    def __init__(self):
        super().__init__(CloudProvider.GCP_STORAGE)
        self._storage_client = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google Cloud Storage."""
        try:
            if not config.validate_gcp_config():
                raise AuthenticationError("GCP credentials not configured properly")
            
            # Set environment variable for credentials if not already set
            if config.google_application_credentials:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.google_application_credentials
            
            # Create storage client
            self._storage_client = storage.Client(project=config.google_cloud_project_id)
            
            # Test authentication by listing buckets
            buckets = list(self._storage_client.list_buckets(max_results=1))
            
            logger.info("Google Cloud Storage authentication successful")
            return True
            
        except DefaultCredentialsError as e:
            raise AuthenticationError(f"GCP credentials error: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"GCP connection failed: {str(e)}")
    
    @with_retry()
    def list_files(self, bucket_name: str, prefix: str = "") -> List[FileInfo]:
        """List files in a GCP Storage bucket."""
        if not self._storage_client:
            self.authenticate()
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            
            files = []
            for blob in blobs:
                file_info = FileInfo(
                    name=blob.name,
                    size=blob.size or 0,
                    last_modified=blob.time_created.isoformat() if blob.time_created else "",
                    etag=blob.etag.strip('"') if blob.etag else None,
                    content_type=blob.content_type,
                    metadata=blob.metadata or {}
                )
                files.append(file_info)
            
            logger.info(f"Listed {len(files)} files from GCP bucket", bucket=bucket_name, prefix=prefix)
            return files
            
        except NotFound:
            raise FileNotFoundError(f"GCP bucket '{bucket_name}' not found")
        except Forbidden:
            raise PermissionError(f"Access denied to GCP bucket '{bucket_name}'")
        except Exception as e:
            raise CloudStorageError(f"GCP list error: {str(e)}")
    
    @with_retry()
    def upload_file(self, local_path: str, bucket_name: str, remote_path: str, **kwargs) -> TransferResult:
        """Upload a file to Google Cloud Storage."""
        if not self._storage_client:
            self.authenticate()
        
        start_time = time.time()
        local_file = Path(local_path)
        
        if not local_file.exists():
            raise FileNotFoundError(f"Local file '{local_path}' not found")
        
        file_size = local_file.stat().st_size
        
        log_operation_start(
            "gcp_upload",
            local_path=local_path,
            bucket=bucket_name,
            remote_path=remote_path,
            size_bytes=file_size
        )
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            
            # Set metadata if provided
            if 'metadata' in kwargs:
                blob.metadata = kwargs['metadata']
            if 'content_type' in kwargs:
                blob.content_type = kwargs['content_type']
            
            # Upload file
            blob.upload_from_filename(str(local_path))
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=local_path,
                destination_path=f"gcs://{bucket_name}/{remote_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "gcp_upload",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"GCP upload failed: {str(e)}"
            log_operation_error("gcp_upload", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=local_path,
                destination_path=f"gcs://{bucket_name}/{remote_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def download_file(self, bucket_name: str, remote_path: str, local_path: str, **kwargs) -> TransferResult:
        """Download a file from Google Cloud Storage."""
        if not self._storage_client:
            self.authenticate()
        
        start_time = time.time()
        
        # Create local directory if it doesn't exist
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_operation_start(
            "gcp_download",
            bucket=bucket_name,
            remote_path=remote_path,
            local_path=local_path
        )
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"File 'gcs://{bucket_name}/{remote_path}' not found")
            
            # Get file size
            blob.reload()
            file_size = blob.size or 0
            
            # Download file
            blob.download_to_filename(str(local_path))
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"gcs://{bucket_name}/{remote_path}",
                destination_path=local_path,
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "gcp_download",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except NotFound:
            error_msg = f"File 'gcs://{bucket_name}/{remote_path}' not found"
            log_operation_error("gcp_download", FileNotFoundError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"gcs://{bucket_name}/{remote_path}",
                destination_path=local_path,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"GCP download failed: {str(e)}"
            log_operation_error("gcp_download", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"gcs://{bucket_name}/{remote_path}",
                destination_path=local_path,
                error_message=error_msg
            )
    
    @with_retry()
    def copy_file(self, source_bucket: str, source_path: str, 
                 dest_bucket: str, dest_path: str, **kwargs) -> TransferResult:
        """Copy a file within GCP or between buckets."""
        if not self._storage_client:
            self.authenticate()
        
        start_time = time.time()
        
        log_operation_start(
            "gcp_copy",
            source_bucket=source_bucket,
            source_path=source_path,
            dest_bucket=dest_bucket,
            dest_path=dest_path
        )
        
        try:
            # Get source blob
            source_bucket_obj = self._storage_client.bucket(source_bucket)
            source_blob = source_bucket_obj.blob(source_path)
            
            if not source_blob.exists():
                raise FileNotFoundError(f"Source file 'gcs://{source_bucket}/{source_path}' not found")
            
            # Get source blob properties for size
            source_blob.reload()
            file_size = source_blob.size or 0
            
            # Get destination bucket and copy
            dest_bucket_obj = self._storage_client.bucket(dest_bucket)
            dest_blob = source_bucket_obj.copy_blob(source_blob, dest_bucket_obj, dest_path)
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"gcs://{source_bucket}/{source_path}",
                destination_path=f"gcs://{dest_bucket}/{dest_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success("gcp_copy", duration=duration, bytes_transferred=file_size)
            return result
            
        except Exception as e:
            error_msg = f"GCP copy failed: {str(e)}"
            log_operation_error("gcp_copy", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"gcs://{source_bucket}/{source_path}",
                destination_path=f"gcs://{dest_bucket}/{dest_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def delete_file(self, bucket_name: str, remote_path: str) -> bool:
        """Delete a file from Google Cloud Storage."""
        if not self._storage_client:
            self.authenticate()
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            blob.delete()
            logger.info("File deleted from GCP", bucket=bucket_name, blob=remote_path)
            return True
            
        except Exception as e:
            logger.error("GCP delete failed", error=str(e), bucket=bucket_name, blob=remote_path)
            return False
    
    def file_exists(self, bucket_name: str, remote_path: str) -> bool:
        """Check if a file exists in Google Cloud Storage."""
        if not self._storage_client:
            self.authenticate()
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False
    
    def get_file_info(self, bucket_name: str, remote_path: str) -> FileInfo:
        """Get information about a file in Google Cloud Storage."""
        if not self._storage_client:
            self.authenticate()
        
        try:
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(remote_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"File 'gcs://{bucket_name}/{remote_path}' not found")
            
            blob.reload()
            
            return FileInfo(
                name=remote_path,
                size=blob.size or 0,
                last_modified=blob.time_created.isoformat() if blob.time_created else "",
                etag=blob.etag.strip('"') if blob.etag else None,
                content_type=blob.content_type,
                metadata=blob.metadata or {}
            )
            
        except NotFound:
            raise FileNotFoundError(f"File 'gcs://{bucket_name}/{remote_path}' not found")
        except Exception as e:
            raise CloudStorageError(f"GCP error: {str(e)}")
