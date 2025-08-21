"""
Resource validation utilities for Azure Infrastructure Agent.

This module provides validation functions for Azure resource parameters
including naming conventions, value constraints, and business rules.
"""

import re
from typing import List, Dict, Any, Optional, Union

from .validation_result import ValidationResult, ValidationSeverity
from ..config.logging import get_logger

logger = get_logger(__name__)


class StorageAccountValidator:
    """
    Validator for Azure Storage Account parameters.
    
    Implements Azure-specific validation rules for storage account
    names, tiers, replication types, and other parameters.
    """
    
    def __init__(self):
        """Initialize storage account validator with Azure rules."""
        self.valid_performance_tiers = {"Standard", "Premium"}
        self.valid_replication_types = {
            "LRS",     # Locally redundant storage
            "GRS",     # Geo-redundant storage
            "RAGRS",   # Read-access geo-redundant storage
            "ZRS",     # Zone-redundant storage
            "GZRS",    # Geo-zone-redundant storage
            "RAGZRS"   # Read-access geo-zone-redundant storage
        }
        self.valid_access_tiers = {"Hot", "Cool", "Archive"}
        self.valid_kinds = {"Storage", "StorageV2", "BlobStorage", "FileStorage", "BlockBlobStorage"}
        
        # Azure regions (subset - commonly used ones)
        self.valid_regions = {
            "East US", "East US 2", "West US", "West US 2", "West US 3",
            "Central US", "North Central US", "South Central US", "West Central US",
            "Canada Central", "Canada East",
            "Brazil South",
            "North Europe", "West Europe", 
            "UK South", "UK West",
            "France Central", "France South",
            "Germany West Central", "Germany North",
            "Switzerland North", "Switzerland West",
            "Norway East", "Norway West",
            "Southeast Asia", "East Asia",
            "Japan East", "Japan West",
            "Korea Central", "Korea South",
            "India Central", "India South", "India West",
            "Australia East", "Australia Southeast", "Australia Central", "Australia Central 2",
            "UAE North", "UAE Central",
            "South Africa North", "South Africa West"
        }
    
    def validate_storage_account_name(self, name: str) -> ValidationResult:
        """
        Validate a storage account name according to Azure rules.
        
        Azure storage account naming rules:
        - Length: 3-24 characters
        - Characters: lowercase letters and numbers only
        - Must be unique across all Azure
        - Cannot end with a dash
        - Cannot contain consecutive dashes
        
        Args:
            name (str): The storage account name to validate.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not name:
            result.add_error("Storage account name cannot be empty")
            return result
        
        # Length validation
        if len(name) < 3:
            result.add_error("Storage account name must be at least 3 characters long")
        elif len(name) > 24:
            result.add_error("Storage account name must be no more than 24 characters long")
        
        # Character validation
        if not re.match(r'^[a-z0-9]+$', name):
            result.add_error("Storage account name can only contain lowercase letters and numbers")
        
        # Additional Azure-specific rules
        if name.startswith('-') or name.endswith('-'):
            result.add_error("Storage account name cannot start or end with a dash")
        
        if '--' in name:
            result.add_error("Storage account name cannot contain consecutive dashes")
        
        # Check for reserved names
        reserved_names = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 
                         'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 
                         'lpt6', 'lpt7', 'lpt8', 'lpt9'}
        if name.lower() in reserved_names:
            result.add_error(f"'{name}' is a reserved name and cannot be used")
        
        # Best practice warnings
        if name.isdigit():
            result.add_warning("Storage account name should include letters, not just numbers")
        
        if len(name) < 6:
            result.add_warning("Consider using a longer name for better uniqueness")
        
        # Info about uniqueness
        result.add_info("Remember that storage account names must be globally unique across all of Azure")
        
        return result
    
    def validate_resource_group_name(self, name: str) -> ValidationResult:
        """
        Validate a resource group name according to Azure rules.
        
        Args:
            name (str): The resource group name to validate.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not name:
            result.add_error("Resource group name cannot be empty")
            return result
        
        # Length validation (1-90 characters)
        if len(name) < 1:
            result.add_error("Resource group name must be at least 1 character long")
        elif len(name) > 90:
            result.add_error("Resource group name must be no more than 90 characters long")
        
        # Character validation
        # Reason: Azure allows alphanumeric, periods, underscores, hyphens, and parentheses
        if not re.match(r'^[a-zA-Z0-9._\-()]+$', name):
            result.add_error("Resource group name can only contain letters, numbers, periods, underscores, hyphens, and parentheses")
        
        # Cannot end with a period
        if name.endswith('.'):
            result.add_error("Resource group name cannot end with a period")
        
        return result
    
    def validate_performance_tier(self, tier: str) -> ValidationResult:
        """
        Validate storage account performance tier.
        
        Args:
            tier (str): The performance tier to validate.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not tier:
            result.add_error("Performance tier cannot be empty")
            return result
        
        if tier not in self.valid_performance_tiers:
            result.add_error(f"Invalid performance tier '{tier}'. Valid options: {', '.join(sorted(self.valid_performance_tiers))}")
        
        # Performance tier guidance
        if tier == "Premium":
            result.add_info("Premium tier provides higher performance but costs more")
        elif tier == "Standard":
            result.add_info("Standard tier is cost-effective for most workloads")
        
        return result
    
    def validate_replication_type(self, replication: str, performance_tier: str = None) -> ValidationResult:
        """
        Validate storage account replication type.
        
        Args:
            replication (str): The replication type to validate.
            performance_tier (str, optional): Performance tier for compatibility check.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not replication:
            result.add_error("Replication type cannot be empty")
            return result
        
        if replication not in self.valid_replication_types:
            result.add_error(f"Invalid replication type '{replication}'. Valid options: {', '.join(sorted(self.valid_replication_types))}")
            return result
        
        # Premium tier restrictions
        if performance_tier == "Premium":
            premium_compatible = {"LRS", "ZRS"}
            if replication not in premium_compatible:
                result.add_error(f"Premium performance tier only supports LRS and ZRS replication, not {replication}")
        
        # Add guidance based on replication type
        replication_info = {
            "LRS": "Locally redundant - lowest cost, basic protection",
            "GRS": "Geo-redundant - protects against regional disasters",
            "RAGRS": "Read-access geo-redundant - GRS with read access to secondary region",
            "ZRS": "Zone-redundant - protects against zone failures",
            "GZRS": "Geo-zone-redundant - combines ZRS and GRS protection",
            "RAGZRS": "Read-access geo-zone-redundant - GZRS with read access to secondary"
        }
        
        if replication in replication_info:
            result.add_info(replication_info[replication])
        
        return result
    
    def validate_access_tier(self, tier: str, account_kind: str = None) -> ValidationResult:
        """
        Validate storage account access tier.
        
        Args:
            tier (str): The access tier to validate.
            account_kind (str, optional): Storage account kind for compatibility check.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not tier:
            result.add_error("Access tier cannot be empty")
            return result
        
        if tier not in self.valid_access_tiers:
            result.add_error(f"Invalid access tier '{tier}'. Valid options: {', '.join(sorted(self.valid_access_tiers))}")
            return result
        
        # Access tier only applies to certain account kinds
        if account_kind in ["FileStorage", "BlockBlobStorage"]:
            result.add_warning(f"Access tier setting is not applicable for {account_kind} accounts")
        
        # Add guidance
        tier_info = {
            "Hot": "Optimized for frequently accessed data - higher storage cost, lower access cost",
            "Cool": "Optimized for infrequently accessed data - lower storage cost, higher access cost",
            "Archive": "Lowest cost tier for rarely accessed data - requires rehydration before access"
        }
        
        if tier in tier_info:
            result.add_info(tier_info[tier])
        
        return result
    
    def validate_region(self, region: str) -> ValidationResult:
        """
        Validate Azure region.
        
        Args:
            region (str): The region to validate.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not region:
            result.add_error("Region cannot be empty")
            return result
        
        # Check if region is in our known list
        if region not in self.valid_regions:
            result.add_warning(f"Region '{region}' is not in the common regions list. Please verify it exists.")
            result.add_info("Common regions include: East US, West US, North Europe, West Europe, Southeast Asia")
        else:
            result.add_info(f"Region '{region}' is valid")
        
        return result
    
    def validate_storage_account_kind(self, kind: str) -> ValidationResult:
        """
        Validate storage account kind.
        
        Args:
            kind (str): The storage account kind to validate.
            
        Returns:
            ValidationResult: Validation result with errors/warnings.
        """
        result = ValidationResult()
        
        if not kind:
            result.add_error("Storage account kind cannot be empty")
            return result
        
        if kind not in self.valid_kinds:
            result.add_error(f"Invalid storage account kind '{kind}'. Valid options: {', '.join(sorted(self.valid_kinds))}")
            return result
        
        # Add guidance based on kind
        kind_info = {
            "StorageV2": "General-purpose v2 - recommended for most scenarios",
            "Storage": "General-purpose v1 - legacy, use StorageV2 instead",
            "BlobStorage": "Blob-only storage - deprecated, use StorageV2",
            "FileStorage": "Premium file shares only",
            "BlockBlobStorage": "Premium block blobs only"
        }
        
        if kind in kind_info:
            result.add_info(kind_info[kind])
        
        if kind == "Storage":
            result.add_warning("General-purpose v1 accounts are legacy. Consider using StorageV2 for new deployments")
        
        return result
    
    def validate_all_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """
        Validate all storage account parameters together.
        
        Args:
            parameters (Dict[str, Any]): Dictionary of parameters to validate.
            
        Returns:
            ValidationResult: Combined validation result.
        """
        combined_result = ValidationResult()
        
        # Validate individual parameters
        validations = []
        
        if 'name' in parameters:
            validations.append(self.validate_storage_account_name(parameters['name']))
        
        if 'resource_group' in parameters:
            validations.append(self.validate_resource_group_name(parameters['resource_group']))
        
        if 'location' in parameters:
            validations.append(self.validate_region(parameters['location']))
        
        if 'performance_tier' in parameters:
            validations.append(self.validate_performance_tier(parameters['performance_tier']))
        
        if 'replication_type' in parameters:
            tier = parameters.get('performance_tier')
            validations.append(self.validate_replication_type(parameters['replication_type'], tier))
        
        if 'access_tier' in parameters:
            kind = parameters.get('kind', 'StorageV2')
            validations.append(self.validate_access_tier(parameters['access_tier'], kind))
        
        if 'kind' in parameters:
            validations.append(self.validate_storage_account_kind(parameters['kind']))
        
        # Combine all validation results
        for validation in validations:
            combined_result.errors.extend(validation.errors)
            combined_result.warnings.extend(validation.warnings)
            combined_result.info.extend(validation.info)
        
        # Cross-parameter validations
        self._validate_parameter_combinations(parameters, combined_result)
        
        logger.info(f"Validated {len(parameters)} parameters: {combined_result.get_summary()}")
        
        return combined_result
    
    def _validate_parameter_combinations(self, parameters: Dict[str, Any], result: ValidationResult) -> None:
        """
        Validate parameter combinations and compatibility.
        
        Args:
            parameters (Dict[str, Any]): Parameters to validate.
            result (ValidationResult): Result object to add messages to.
        """
        # Premium + FileStorage/BlockBlobStorage compatibility
        performance_tier = parameters.get('performance_tier')
        kind = parameters.get('kind')
        
        if performance_tier == "Premium":
            if kind not in ["FileStorage", "BlockBlobStorage"]:
                result.add_warning("Premium performance tier works best with FileStorage or BlockBlobStorage kinds")
        
        # BlobStorage account limitations
        if kind == "BlobStorage":
            if parameters.get('access_tier') == "Archive":
                result.add_info("Archive tier is available for BlobStorage accounts")
        
        # Regional considerations
        location = parameters.get('location')
        replication = parameters.get('replication_type')
        
        if location and replication:
            # Some replication types may not be available in all regions
            if replication in ["GZRS", "RAGZRS"]:
                result.add_info("GZRS and RA-GZRS are not available in all regions. Verify availability in your target region.")


def create_storage_validator() -> StorageAccountValidator:
    """
    Factory function to create a storage account validator.
    
    Returns:
        StorageAccountValidator: Configured validator instance.
    """
    return StorageAccountValidator()