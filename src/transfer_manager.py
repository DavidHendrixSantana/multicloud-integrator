"""
Multi-cloud transfer manager for copying files between different cloud providers.
"""
import os
import time
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
from pathlib import Path
import structlog

from connectors import (
    CloudProvider,
    CloudStorageConnector,
    get_connector_by_name,
    TransferResult,
    FileInfo
)
from config import config
from utils import format_bytes, calculate_transfer_speed
from logger import log_operation_start, log_operation_success, log_operation_error

logger = structlog.get_logger()

class MultiCloudTransferManager:
    """
    Manager for transferring files between different cloud storage providers.
    """
    
    def __init__(self):
        self._connectors: Dict[str, CloudStorageConnector] = {}
        self._temp_dir = Path("temp_transfers")
        self._temp_dir.mkdir(exist_ok=True)
    
    def _parse_cloud_url(self, url: str) -> Tuple[str, str, str]:
        """
        Parse a cloud storage URL into provider, container/bucket, and path.
        
        Supported formats:
        - s3://bucket/path/to/file
        - azure://container/path/to/file  
        - gcs://bucket/path/to/file
        - gs://bucket/path/to/file (GCS alternative)
        
        Returns:
            Tuple of (provider, container/bucket, path)
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        if scheme in ['s3']:
            provider = 'aws'
        elif scheme in ['azure']:
            provider = 'azure'
        elif scheme in ['gcs', 'gs']:
            provider = 'gcp'
        else:
            raise ValueError(f"Unsupported URL scheme: {scheme}")
        
        container = parsed.netloc
        path = parsed.path.lstrip('/')
        
        return provider, container, path
    
    def _get_connector(self, provider: str) -> CloudStorageConnector:
        """Get or create a connector for the specified provider."""
        if provider not in self._connectors:
            self._connectors[provider] = get_connector_by_name(provider)
            # Authenticate the connector
            if not self._connectors[provider].authenticate():
                raise Exception(f"Failed to authenticate with {provider}")
        
        return self._connectors[provider]
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to all configured cloud providers.
        
        Returns:
            Dictionary mapping provider names to connection status
        """
        results = {}
        
        # Test AWS S3
        if config.validate_aws_config():
            try:
                connector = get_connector_by_name('aws')
                results['aws_s3'] = connector.test_connection()
            except Exception as e:
                logger.error("AWS S3 connection test failed", error=str(e))
                results['aws_s3'] = False
        else:
            results['aws_s3'] = None  # Not configured
        
        # Test Azure Blob
        if config.validate_azure_config():
            try:
                connector = get_connector_by_name('azure')
                results['azure_blob'] = connector.test_connection()
            except Exception as e:
                logger.error("Azure Blob connection test failed", error=str(e))
                results['azure_blob'] = False
        else:
            results['azure_blob'] = None  # Not configured
        
        # Test GCP Storage
        if config.validate_gcp_config():
            try:
                connector = get_connector_by_name('gcp')
                results['gcp_storage'] = connector.test_connection()
            except Exception as e:
                logger.error("GCP Storage connection test failed", error=str(e))
                results['gcp_storage'] = False
        else:
            results['gcp_storage'] = None  # Not configured
        
        return results
    
    def list_files(self, cloud_url: str, prefix: str = "") -> List[FileInfo]:
        """
        List files in a cloud storage location.
        
        Args:
            cloud_url: Cloud storage URL (e.g., 's3://bucket', 'azure://container')
            prefix: Optional prefix to filter files
            
        Returns:
            List of FileInfo objects
        """
        provider, container, path = self._parse_cloud_url(cloud_url)
        
        # Combine path from URL with additional prefix
        full_prefix = os.path.join(path, prefix).replace('\\', '/') if path else prefix
        
        connector = self._get_connector(provider)
        return connector.list_files(container, full_prefix)
    
    def copy_file_direct(self, source_url: str, dest_url: str, **kwargs) -> TransferResult:
        """
        Copy a file directly between cloud providers (if same provider) or via local temp.
        
        Args:
            source_url: Source cloud URL
            dest_url: Destination cloud URL
            **kwargs: Additional options for transfer
            
        Returns:
            TransferResult with operation details
        """
        start_time = time.time()
        
        source_provider, source_container, source_path = self._parse_cloud_url(source_url)
        dest_provider, dest_container, dest_path = self._parse_cloud_url(dest_url)
        
        log_operation_start(
            "multi_cloud_copy",
            source_url=source_url,
            dest_url=dest_url,
            source_provider=source_provider,
            dest_provider=dest_provider
        )
        
        try:
            # If same provider, use direct copy
            if source_provider == dest_provider:
                connector = self._get_connector(source_provider)
                result = connector.copy_file(
                    source_container, source_path,
                    dest_container, dest_path,
                    **kwargs
                )
            else:
                # Different providers - download then upload via temp file
                result = self._copy_via_temp(
                    source_provider, source_container, source_path,
                    dest_provider, dest_container, dest_path,
                    **kwargs
                )
            
            if result.success:
                log_operation_success(
                    "multi_cloud_copy",
                    duration=result.duration_seconds,
                    bytes_transferred=result.bytes_transferred,
                    speed=calculate_transfer_speed(
                        result.bytes_transferred, 
                        result.duration_seconds
                    )
                )
            else:
                log_operation_error(
                    "multi_cloud_copy", 
                    Exception(result.error_message or "Copy failed")
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Multi-cloud copy failed: {str(e)}"
            log_operation_error("multi_cloud_copy", e)
            
            return TransferResult(
                success=False,
                source_path=source_url,
                destination_path=dest_url,
                duration_seconds=time.time() - start_time,
                error_message=error_msg
            )
    
    def _copy_via_temp(self, 
                      source_provider: str, source_container: str, source_path: str,
                      dest_provider: str, dest_container: str, dest_path: str,
                      **kwargs) -> TransferResult:
        """
        Copy file between different providers via temporary local file.
        """
        start_time = time.time()
        temp_filename = f"temp_{int(time.time())}_{os.path.basename(source_path)}"
        temp_file_path = self._temp_dir / temp_filename
        
        total_bytes_transferred = 0
        
        try:
            # Step 1: Download from source
            source_connector = self._get_connector(source_provider)
            download_result = source_connector.download_file(
                source_container, source_path, str(temp_file_path)
            )
            
            if not download_result.success:
                return TransferResult(
                    success=False,
                    source_path=f"{source_provider}://{source_container}/{source_path}",
                    destination_path=f"{dest_provider}://{dest_container}/{dest_path}",
                    error_message=f"Download failed: {download_result.error_message}"
                )
            
            total_bytes_transferred = download_result.bytes_transferred
            
            # Step 2: Upload to destination
            dest_connector = self._get_connector(dest_provider)
            upload_result = dest_connector.upload_file(
                str(temp_file_path), dest_container, dest_path, **kwargs
            )
            
            if not upload_result.success:
                return TransferResult(
                    success=False,
                    source_path=f"{source_provider}://{source_container}/{source_path}",
                    destination_path=f"{dest_provider}://{dest_container}/{dest_path}",
                    error_message=f"Upload failed: {upload_result.error_message}"
                )
            
            # Success
            total_duration = time.time() - start_time
            
            return TransferResult(
                success=True,
                source_path=f"{source_provider}://{source_container}/{source_path}",
                destination_path=f"{dest_provider}://{dest_container}/{dest_path}",
                bytes_transferred=total_bytes_transferred,
                duration_seconds=total_duration
            )
            
        finally:
            # Clean up temp file
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception as e:
                    logger.warning("Failed to delete temp file", temp_file=str(temp_file_path), error=str(e))
    
    def upload_file(self, local_path: str, dest_url: str, **kwargs) -> TransferResult:
        """
        Upload a local file to cloud storage.
        
        Args:
            local_path: Path to local file
            dest_url: Destination cloud URL
            **kwargs: Additional options for upload
            
        Returns:
            TransferResult with operation details
        """
        provider, container, remote_path = self._parse_cloud_url(dest_url)
        connector = self._get_connector(provider)
        
        return connector.upload_file(local_path, container, remote_path, **kwargs)
    
    def download_file(self, source_url: str, local_path: str, **kwargs) -> TransferResult:
        """
        Download a file from cloud storage to local filesystem.
        
        Args:
            source_url: Source cloud URL
            local_path: Local destination path
            **kwargs: Additional options for download
            
        Returns:
            TransferResult with operation details
        """
        provider, container, remote_path = self._parse_cloud_url(source_url)
        connector = self._get_connector(provider)
        
        return connector.download_file(container, remote_path, local_path, **kwargs)
    
    def delete_file(self, cloud_url: str) -> bool:
        """
        Delete a file from cloud storage.
        
        Args:
            cloud_url: Cloud storage URL of file to delete
            
        Returns:
            True if successful, False otherwise
        """
        provider, container, remote_path = self._parse_cloud_url(cloud_url)
        connector = self._get_connector(provider)
        
        return connector.delete_file(container, remote_path)
    
    def file_exists(self, cloud_url: str) -> bool:
        """
        Check if a file exists in cloud storage.
        
        Args:
            cloud_url: Cloud storage URL to check
            
        Returns:
            True if file exists, False otherwise
        """
        provider, container, remote_path = self._parse_cloud_url(cloud_url)
        connector = self._get_connector(provider)
        
        return connector.file_exists(container, remote_path)
    
    def get_file_info(self, cloud_url: str) -> FileInfo:
        """
        Get information about a file in cloud storage.
        
        Args:
            cloud_url: Cloud storage URL
            
        Returns:
            FileInfo object with file details
        """
        provider, container, remote_path = self._parse_cloud_url(cloud_url)
        connector = self._get_connector(provider)
        
        return connector.get_file_info(container, remote_path)
    
    def batch_copy(self, transfers: List[Tuple[str, str]], **kwargs) -> List[TransferResult]:
        """
        Perform multiple file transfers in batch.
        
        Args:
            transfers: List of (source_url, dest_url) tuples
            **kwargs: Additional options for transfers
            
        Returns:
            List of TransferResult objects
        """
        results = []
        
        for i, (source_url, dest_url) in enumerate(transfers, 1):
            logger.info(f"Processing transfer {i}/{len(transfers)}", 
                       source=source_url, destination=dest_url)
            
            result = self.copy_file_direct(source_url, dest_url, **kwargs)
            results.append(result)
            
            if not result.success:
                logger.error(f"Transfer {i} failed", error=result.error_message)
        
        # Summary statistics
        successful = sum(1 for r in results if r.success)
        total_bytes = sum(r.bytes_transferred for r in results if r.success)
        
        logger.info(
            "Batch transfer completed",
            successful=successful,
            total=len(transfers),
            total_bytes_transferred=total_bytes,
            total_size=format_bytes(total_bytes)
        )
        
        return results
    
    def cleanup(self):
        """Clean up temporary files and resources."""
        try:
            if self._temp_dir.exists():
                for temp_file in self._temp_dir.iterdir():
                    if temp_file.is_file():
                        temp_file.unlink()
                        logger.debug("Cleaned up temp file", file=str(temp_file))
        except Exception as e:
            logger.warning("Error during cleanup", error=str(e))
