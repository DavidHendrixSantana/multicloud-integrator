"""
Cloud storage connectors package.
"""
from .base import CloudProvider, CloudStorageConnector, FileInfo, TransferResult
from .s3_connector import S3Connector
from .azure_connector import AzureBlobConnector
from .gcp_connector import GCPStorageConnector

__all__ = [
    'CloudProvider',
    'CloudStorageConnector',
    'FileInfo',
    'TransferResult',
    'S3Connector',
    'AzureBlobConnector',
    'GCPStorageConnector'
]

def get_connector(provider: CloudProvider) -> CloudStorageConnector:
    """
    Factory function to get the appropriate connector for a cloud provider.
    
    Args:
        provider: The cloud provider enum
        
    Returns:
        CloudStorageConnector: The appropriate connector instance
        
    Raises:
        ValueError: If the provider is not supported
    """
    if provider == CloudProvider.AWS_S3:
        return S3Connector()
    elif provider == CloudProvider.AZURE_BLOB:
        return AzureBlobConnector()
    elif provider == CloudProvider.GCP_STORAGE:
        return GCPStorageConnector()
    else:
        raise ValueError(f"Unsupported cloud provider: {provider}")

def get_connector_by_name(provider_name: str) -> CloudStorageConnector:
    """
    Get a connector by provider name string.
    
    Args:
        provider_name: Name of the provider ('aws', 's3', 'azure', 'blob', 'gcp', 'gcs')
        
    Returns:
        CloudStorageConnector: The appropriate connector instance
        
    Raises:
        ValueError: If the provider name is not recognized
    """
    provider_name = provider_name.lower().strip()
    
    if provider_name in ['aws', 's3', 'aws_s3']:
        return S3Connector()
    elif provider_name in ['azure', 'blob', 'azure_blob']:
        return AzureBlobConnector()
    elif provider_name in ['gcp', 'gcs', 'google', 'gcp_storage']:
        return GCPStorageConnector()
    else:
        supported = ['aws/s3', 'azure/blob', 'gcp/gcs']
        raise ValueError(f"Unsupported provider '{provider_name}'. Supported: {supported}")

def list_supported_providers():
    """
    List all supported cloud providers.
    
    Returns:
        List of tuples containing (provider_enum, provider_name, description)
    """
    return [
        (CloudProvider.AWS_S3, 'aws_s3', 'Amazon Web Services S3'),
        (CloudProvider.AZURE_BLOB, 'azure_blob', 'Microsoft Azure Blob Storage'),
        (CloudProvider.GCP_STORAGE, 'gcp_storage', 'Google Cloud Platform Storage')
    ]
