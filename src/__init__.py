"""
Multi-Cloud File Transfer CLI Tool

A powerful command-line tool for transferring files between AWS S3, Azure Blob Storage, 
and Google Cloud Storage with built-in resilience and comprehensive logging.
"""

__version__ = "1.0.0"
__author__ = "Multi-Cloud CLI Team"
__email__ = "contact@example.com"

from .config import config
from .transfer_manager import MultiCloudTransferManager
from .connectors import (
    CloudProvider,
    get_connector_by_name,
    list_supported_providers
)

__all__ = [
    "config",
    "MultiCloudTransferManager", 
    "CloudProvider",
    "get_connector_by_name",
    "list_supported_providers"
]
