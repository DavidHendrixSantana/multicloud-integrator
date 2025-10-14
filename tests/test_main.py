"""
Unit tests for the multi-cloud CLI tool.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from connectors.base import CloudProvider, FileInfo, TransferResult
from connectors import get_connector_by_name, get_connector
from transfer_manager import MultiCloudTransferManager

class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def test_config_creation(self):
        """Test basic configuration creation."""
        config = Config()
        self.assertEqual(config.aws_default_region, "us-east-1")
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.log_level, "INFO")
    
    def test_aws_config_validation(self):
        """Test AWS configuration validation."""
        config = Config()
        
        # Test invalid config
        config.aws_access_key_id = None
        config.aws_secret_access_key = None
        self.assertFalse(config.validate_aws_config())
        
        # Test valid config
        config.aws_access_key_id = "test_key"
        config.aws_secret_access_key = "test_secret"
        self.assertTrue(config.validate_aws_config())

class TestConnectorFactory(unittest.TestCase):
    """Test connector factory functions."""
    
    def test_get_connector_by_name(self):
        """Test getting connectors by name."""
        # Test AWS
        connector = get_connector_by_name('aws')
        self.assertEqual(connector.provider, CloudProvider.AWS_S3)
        
        connector = get_connector_by_name('s3')
        self.assertEqual(connector.provider, CloudProvider.AWS_S3)
        
        # Test Azure
        connector = get_connector_by_name('azure')
        self.assertEqual(connector.provider, CloudProvider.AZURE_BLOB)
        
        # Test GCP
        connector = get_connector_by_name('gcp')
        self.assertEqual(connector.provider, CloudProvider.GCP_STORAGE)
        
        # Test invalid name
        with self.assertRaises(ValueError):
            get_connector_by_name('invalid')
    
    def test_get_connector_by_enum(self):
        """Test getting connectors by enum."""
        connector = get_connector(CloudProvider.AWS_S3)
        self.assertEqual(connector.provider, CloudProvider.AWS_S3)
        
        connector = get_connector(CloudProvider.AZURE_BLOB)
        self.assertEqual(connector.provider, CloudProvider.AZURE_BLOB)
        
        connector = get_connector(CloudProvider.GCP_STORAGE)
        self.assertEqual(connector.provider, CloudProvider.GCP_STORAGE)

class TestFileInfo(unittest.TestCase):
    """Test FileInfo data class."""
    
    def test_file_info_creation(self):
        """Test FileInfo object creation."""
        file_info = FileInfo(
            name="test.txt",
            size=1024,
            last_modified="2025-01-15T10:30:45",
            etag="abc123",
            content_type="text/plain",
            metadata={"author": "test"}
        )
        
        self.assertEqual(file_info.name, "test.txt")
        self.assertEqual(file_info.size, 1024)
        self.assertEqual(file_info.content_type, "text/plain")
        self.assertEqual(file_info.metadata["author"], "test")

class TestTransferResult(unittest.TestCase):
    """Test TransferResult data class."""
    
    def test_successful_result(self):
        """Test successful transfer result."""
        result = TransferResult(
            success=True,
            source_path="local/file.txt",
            destination_path="s3://bucket/file.txt",
            bytes_transferred=1024,
            duration_seconds=2.5
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.bytes_transferred, 1024)
        self.assertEqual(result.duration_seconds, 2.5)
        self.assertIsNone(result.error_message)
    
    def test_failed_result(self):
        """Test failed transfer result."""
        result = TransferResult(
            success=False,
            source_path="local/file.txt",
            destination_path="s3://bucket/file.txt",
            error_message="Connection failed"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Connection failed")
        self.assertEqual(result.bytes_transferred, 0)

class TestMultiCloudTransferManager(unittest.TestCase):
    """Test MultiCloudTransferManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = MultiCloudTransferManager()
    
    def test_parse_cloud_url(self):
        """Test cloud URL parsing."""
        # Test S3 URL
        provider, container, path = self.manager._parse_cloud_url("s3://bucket/folder/file.txt")
        self.assertEqual(provider, "aws")
        self.assertEqual(container, "bucket")
        self.assertEqual(path, "folder/file.txt")
        
        # Test Azure URL
        provider, container, path = self.manager._parse_cloud_url("azure://container/path/file.txt")
        self.assertEqual(provider, "azure")
        self.assertEqual(container, "container")
        self.assertEqual(path, "path/file.txt")
        
        # Test GCS URL
        provider, container, path = self.manager._parse_cloud_url("gcs://bucket/file.txt")
        self.assertEqual(provider, "gcp")
        self.assertEqual(container, "bucket")
        self.assertEqual(path, "file.txt")
        
        # Test invalid URL
        with self.assertRaises(ValueError):
            self.manager._parse_cloud_url("invalid://bucket/file.txt")
    
    def test_cleanup(self):
        """Test cleanup functionality."""
        # Create a temporary file in temp directory
        self.manager._temp_dir.mkdir(exist_ok=True)
        temp_file = self.manager._temp_dir / "test_file.tmp"
        temp_file.write_text("test content")
        
        self.assertTrue(temp_file.exists())
        
        # Run cleanup
        self.manager.cleanup()
        
        # File should be cleaned up
        self.assertFalse(temp_file.exists())

class TestUtils(unittest.TestCase):
    """Test utility functions."""
    
    def test_format_bytes(self):
        """Test byte formatting utility."""
        from utils import format_bytes
        
        self.assertEqual(format_bytes(0), "0.0 B")
        self.assertEqual(format_bytes(512), "512.0 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_bytes(1073741824), "1.0 GB")
    
    def test_calculate_transfer_speed(self):
        """Test transfer speed calculation."""
        from utils import calculate_transfer_speed
        
        speed = calculate_transfer_speed(1024, 2.0)
        self.assertEqual(speed, "512.0 B/s")
        
        speed = calculate_transfer_speed(1048576, 1.0)
        self.assertEqual(speed, "1.0 MB/s")
        
        # Test zero duration
        speed = calculate_transfer_speed(1024, 0)
        self.assertEqual(speed, "N/A")

if __name__ == '__main__':
    unittest.main()
