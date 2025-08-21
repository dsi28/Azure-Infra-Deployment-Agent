"""
Storage Account configuration classes for Azure Infrastructure Agent.

This module contains configuration dataclasses and enums for storage account
resource specifications.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..config.logging import get_logger

logger = get_logger(__name__)


class StorageAccountTier(Enum):
    """Storage account performance tiers."""
    STANDARD = "Standard"
    PREMIUM = "Premium"


class ReplicationType(Enum):
    """Storage replication types."""
    LRS = "LRS"      # Locally redundant storage
    GRS = "GRS"      # Geo-redundant storage
    RAGRS = "RAGRS"  # Read-access geo-redundant storage
    ZRS = "ZRS"      # Zone-redundant storage
    GZRS = "GZRS"    # Geo-zone-redundant storage
    RAGZRS = "RAGZRS" # Read-access geo-zone-redundant storage


class AccessTier(Enum):
    """Storage access tiers."""
    HOT = "Hot"
    COOL = "Cool"
    ARCHIVE = "Archive"


class StorageAccountKind(Enum):
    """Storage account kinds."""
    STORAGE = "Storage"                    # General-purpose v1 (legacy)
    STORAGE_V2 = "StorageV2"              # General-purpose v2 (recommended)
    BLOB_STORAGE = "BlobStorage"          # Blob-only storage (deprecated)
    FILE_STORAGE = "FileStorage"          # Premium file shares only
    BLOCK_BLOB_STORAGE = "BlockBlobStorage" # Premium block blobs only


@dataclass
class StorageAccountConfiguration:
    """
    Configuration for Azure Storage Account creation.
    
    This class encapsulates all parameters needed to create a storage account,
    with sensible defaults and validation support.
    """
    
    # Required parameters
    name: Optional[str] = None
    resource_group: Optional[str] = None
    location: Optional[str] = None
    
    # Optional parameters with defaults
    performance_tier: str = StorageAccountTier.STANDARD.value
    replication_type: str = ReplicationType.LRS.value
    access_tier: str = AccessTier.HOT.value
    kind: str = StorageAccountKind.STORAGE_V2.value
    
    # Advanced options
    tags: Dict[str, str] = field(default_factory=dict)
    enable_https_only: bool = True
    enable_hierarchical_namespace: bool = False
    
    def get_required_parameters(self) -> List[str]:
        """
        Get list of required parameters that must be specified.
        
        Returns:
            List[str]: List of required parameter names.
        """
        required_params = []
        
        if not self.name:
            required_params.append("name")
        if not self.resource_group:
            required_params.append("resource_group")
        if not self.location:
            required_params.append("location")
            
        return required_params
    
    def get_missing_required_parameters(self) -> List[str]:
        """
        Get list of missing required parameters.
        
        Returns:
            List[str]: List of missing required parameter names.
        """
        return self.get_required_parameters()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary.
        """
        return {
            "name": self.name,
            "resource_group": self.resource_group,
            "location": self.location,
            "performance_tier": self.performance_tier,
            "replication_type": self.replication_type,
            "access_tier": self.access_tier,
            "kind": self.kind,
            "tags": self.tags,
            "enable_https_only": self.enable_https_only,
            "enable_hierarchical_namespace": self.enable_hierarchical_namespace
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorageAccountConfiguration":
        """
        Create configuration from dictionary.
        
        Args:
            data (Dict[str, Any]): Configuration data as dictionary.
            
        Returns:
            StorageAccountConfiguration: Configuration instance.
        """
        # Filter out None values and unknown keys
        valid_keys = {
            "name", "resource_group", "location", "performance_tier",
            "replication_type", "access_tier", "kind", "tags",
            "enable_https_only", "enable_hierarchical_namespace"
        }
        
        filtered_data = {
            key: value for key, value in data.items()
            if key in valid_keys and value is not None
        }
        
        return cls(**filtered_data)
    
    def is_complete(self) -> bool:
        """
        Check if all required parameters are specified.
        
        Returns:
            bool: True if all required parameters are set, False otherwise.
        """
        return len(self.get_required_parameters()) == 0
    
    def merge_with(self, other: "StorageAccountConfiguration") -> "StorageAccountConfiguration":
        """
        Merge this configuration with another, taking non-None values from other.
        
        Args:
            other (StorageAccountConfiguration): Configuration to merge with.
            
        Returns:
            StorageAccountConfiguration: New merged configuration.
        """
        result_dict = self.to_dict()
        other_dict = other.to_dict()
        
        # Update with non-None values from other
        for key, value in other_dict.items():
            if value is not None:
                result_dict[key] = value
        
        return StorageAccountConfiguration.from_dict(result_dict)
    
    def get_display_summary(self) -> str:
        """
        Get a human-readable summary of the configuration.
        
        Returns:
            str: Display-friendly configuration summary.
        """
        summary_parts = []
        
        if self.name:
            summary_parts.append(f"Name: {self.name}")
        if self.resource_group:
            summary_parts.append(f"Resource Group: {self.resource_group}")
        if self.location:
            summary_parts.append(f"Location: {self.location}")
        
        summary_parts.extend([
            f"Performance: {self.performance_tier}",
            f"Replication: {self.replication_type}",
            f"Access Tier: {self.access_tier}",
            f"Kind: {self.kind}"
        ])
        
        if self.tags:
            tags_str = ", ".join([f"{k}={v}" for k, v in self.tags.items()])
            summary_parts.append(f"Tags: {tags_str}")
        
        return "\n".join(summary_parts)


def create_storage_account_config(**kwargs) -> StorageAccountConfiguration:
    """
    Factory function to create a storage account configuration.
    
    Args:
        **kwargs: Configuration parameters.
        
    Returns:
        StorageAccountConfiguration: New configuration instance.
    """
    return StorageAccountConfiguration(**kwargs)