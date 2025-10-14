"""
AWS S3 connector implementation.
"""
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

import boto3
from botocore.exceptions import (
    ClientError, 
    NoCredentialsError, 
    PartialCredentialsError,
    BotoCoreError
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

class S3Connector(CloudStorageConnector):
    """AWS S3 storage connector."""
    
    def __init__(self):
        super().__init__(CloudProvider.AWS_S3)
        self._s3_client = None
        self._s3_resource = None
    
    def authenticate(self) -> bool:
        """Authenticate with AWS S3."""
        try:
            if not config.validate_aws_config():
                raise AuthenticationError("AWS credentials not configured properly")
            
            # Create S3 client
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                region_name=config.aws_default_region
            )
            
            # Create S3 resource
            self._s3_resource = boto3.resource(
                's3',
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                region_name=config.aws_default_region
            )
            
            # Test authentication by listing buckets
            self._s3_client.list_buckets()
            
            logger.info("AWS S3 authentication successful")
            return True
            
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise AuthenticationError(f"AWS credentials error: {str(e)}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['InvalidAccessKeyId', 'SignatureDoesNotMatch']:
                raise AuthenticationError(f"AWS authentication failed: {str(e)}")
            else:
                raise ConnectionError(f"AWS connection error: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"AWS connection failed: {str(e)}")
    
    @with_retry()
    def list_files(self, bucket: str, prefix: str = "") -> List[FileInfo]:
        """List files in an S3 bucket."""
        if not self._s3_client:
            self.authenticate()
        
        try:
            files = []
            paginator = self._s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        file_info = FileInfo(
                            name=obj['Key'],
                            size=obj['Size'],
                            last_modified=obj['LastModified'].isoformat(),
                            etag=obj['ETag'].strip('"'),
                            metadata={}
                        )
                        files.append(file_info)
            
            logger.info(f"Listed {len(files)} files from S3 bucket", bucket=bucket, prefix=prefix)
            return files
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise FileNotFoundError(f"S3 bucket '{bucket}' not found")
            elif error_code == 'AccessDenied':
                raise PermissionError(f"Access denied to S3 bucket '{bucket}'")
            else:
                raise CloudStorageError(f"S3 list error: {str(e)}")
    
    @with_retry()
    def upload_file(self, local_path: str, bucket: str, remote_path: str, **kwargs) -> TransferResult:
        """Upload a file to S3."""
        if not self._s3_client:
            self.authenticate()
        
        start_time = time.time()
        local_file = Path(local_path)
        
        if not local_file.exists():
            raise FileNotFoundError(f"Local file '{local_path}' not found")
        
        file_size = local_file.stat().st_size
        
        log_operation_start(
            "s3_upload",
            local_path=local_path,
            bucket=bucket,
            remote_path=remote_path,
            size_bytes=file_size
        )
        
        try:
            # Upload with progress callback if file is large
            extra_args = kwargs.get('extra_args', {})
            
            self._s3_client.upload_file(
                str(local_path),
                bucket,
                remote_path,
                ExtraArgs=extra_args
            )
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=local_path,
                destination_path=f"s3://{bucket}/{remote_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "s3_upload",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except ClientError as e:
            error_msg = f"S3 upload failed: {str(e)}"
            log_operation_error("s3_upload", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=local_path,
                destination_path=f"s3://{bucket}/{remote_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def download_file(self, bucket: str, remote_path: str, local_path: str, **kwargs) -> TransferResult:
        """Download a file from S3."""
        if not self._s3_client:
            self.authenticate()
        
        start_time = time.time()
        
        # Create local directory if it doesn't exist
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_operation_start(
            "s3_download",
            bucket=bucket,
            remote_path=remote_path,
            local_path=local_path
        )
        
        try:
            # Get file size first
            response = self._s3_client.head_object(Bucket=bucket, Key=remote_path)
            file_size = response['ContentLength']
            
            # Download file
            self._s3_client.download_file(bucket, remote_path, str(local_path))
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"s3://{bucket}/{remote_path}",
                destination_path=local_path,
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success(
                "s3_download",
                duration=duration,
                bytes_transferred=file_size,
                speed=format_bytes(int(file_size / duration)) + "/s" if duration > 0 else "N/A"
            )
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                error_msg = f"File 's3://{bucket}/{remote_path}' not found"
            else:
                error_msg = f"S3 download failed: {str(e)}"
            
            log_operation_error("s3_download", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"s3://{bucket}/{remote_path}",
                destination_path=local_path,
                error_message=error_msg
            )
    
    @with_retry()
    def copy_file(self, source_bucket: str, source_path: str, 
                 dest_bucket: str, dest_path: str, **kwargs) -> TransferResult:
        """Copy a file within S3 or between S3 buckets."""
        if not self._s3_client:
            self.authenticate()
        
        start_time = time.time()
        copy_source = {'Bucket': source_bucket, 'Key': source_path}
        
        log_operation_start(
            "s3_copy",
            source_bucket=source_bucket,
            source_path=source_path,
            dest_bucket=dest_bucket,
            dest_path=dest_path
        )
        
        try:
            # Get source file size
            response = self._s3_client.head_object(Bucket=source_bucket, Key=source_path)
            file_size = response['ContentLength']
            
            # Copy file
            self._s3_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_path,
                **kwargs
            )
            
            duration = time.time() - start_time
            
            result = TransferResult(
                success=True,
                source_path=f"s3://{source_bucket}/{source_path}",
                destination_path=f"s3://{dest_bucket}/{dest_path}",
                bytes_transferred=file_size,
                duration_seconds=duration
            )
            
            log_operation_success("s3_copy", duration=duration, bytes_transferred=file_size)
            return result
            
        except ClientError as e:
            error_msg = f"S3 copy failed: {str(e)}"
            log_operation_error("s3_copy", CloudStorageError(error_msg))
            return TransferResult(
                success=False,
                source_path=f"s3://{source_bucket}/{source_path}",
                destination_path=f"s3://{dest_bucket}/{dest_path}",
                error_message=error_msg
            )
    
    @with_retry()
    def delete_file(self, bucket: str, remote_path: str) -> bool:
        """Delete a file from S3."""
        if not self._s3_client:
            self.authenticate()
        
        try:
            self._s3_client.delete_object(Bucket=bucket, Key=remote_path)
            logger.info("File deleted from S3", bucket=bucket, key=remote_path)
            return True
            
        except ClientError as e:
            logger.error("S3 delete failed", error=str(e), bucket=bucket, key=remote_path)
            return False
    
    def file_exists(self, bucket: str, remote_path: str) -> bool:
        """Check if a file exists in S3."""
        if not self._s3_client:
            self.authenticate()
        
        try:
            self._s3_client.head_object(Bucket=bucket, Key=remote_path)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_info(self, bucket: str, remote_path: str) -> FileInfo:
        """Get information about a file in S3."""
        if not self._s3_client:
            self.authenticate()
        
        try:
            response = self._s3_client.head_object(Bucket=bucket, Key=remote_path)
            
            return FileInfo(
                name=remote_path,
                size=response['ContentLength'],
                last_modified=response['LastModified'].isoformat(),
                etag=response['ETag'].strip('"'),
                content_type=response.get('ContentType'),
                metadata=response.get('Metadata', {})
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File 's3://{bucket}/{remote_path}' not found")
            raise CloudStorageError(f"S3 error: {str(e)}")
