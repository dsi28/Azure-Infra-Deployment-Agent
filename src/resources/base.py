"""
Base resource classes for Azure Infrastructure Agent.

This module provides base classes and interfaces for Azure resource management,
including configuration validation, parameter collection, and template generation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ResourceStatus(Enum):
    """Enumeration of possible resource statuses."""
    DRAFT = "draft"
    VALIDATED = "validated"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    DELETED = "deleted"


class ResourceParameter(BaseModel):
    """Model for resource parameter definitions."""
    
    name: str
    type: str
    description: str
    required: bool = True
    default_value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    validation_pattern: Optional[str] = None


class ResourceConfiguration(BaseModel):
    """Base model for resource configurations."""
    
    resource_type: str
    name: str
    location: str
    resource_group: str
    tags: Optional[Dict[str, str]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ResourceStatus = ResourceStatus.DRAFT


class ValidationResult(BaseModel):
    """Result of resource configuration validation."""
    
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ResourceRequest(BaseModel):
    """Request for resource processing."""
    
    resource_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ResourceResponse(BaseModel):
    """Response from resource processing."""
    
    success: bool
    resource_type: str
    message: str
    configuration: Optional[Any] = None
    validation_result: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BaseResource(ABC):
    """
    Abstract base class for all Azure resources.
    
    This class defines the interface for resource management including
    parameter collection, validation, and template generation.
    """
    
    def __init__(self, resource_type: str):
        """
        Initialize the base resource.
        
        Args:
            resource_type (str): The Azure resource type (e.g., 'Microsoft.Storage/storageAccounts').
        """
        self.resource_type = resource_type
        self.parameters: List[ResourceParameter] = []
        self.arm_api_version = "2021-01-01"  # Default, should be overridden
    
    def add_parameter(self, parameter: ResourceParameter) -> None:
        """
        Add a parameter definition to this resource.
        
        Args:
            parameter (ResourceParameter): The parameter to add.
        """
        self.parameters.append(parameter)
    
    def get_required_parameters(self) -> List[ResourceParameter]:
        """
        Get all required parameters for this resource.
        
        Returns:
            List[ResourceParameter]: List of required parameters.
        """
        return [param for param in self.parameters if param.required]
    
    def get_optional_parameters(self) -> List[ResourceParameter]:
        """
        Get all optional parameters for this resource.
        
        Returns:
            List[ResourceParameter]: List of optional parameters.
        """
        return [param for param in self.parameters if not param.required]
    
    @abstractmethod
    def validate_configuration(self, config: ResourceConfiguration) -> ValidationResult:
        """
        Validate a resource configuration.
        
        Args:
            config (ResourceConfiguration): The configuration to validate.
            
        Returns:
            ValidationResult: The validation result.
        """
        pass
    
    @abstractmethod
    def generate_arm_template(self, config: ResourceConfiguration) -> Dict[str, Any]:
        """
        Generate an ARM template for this resource.
        
        Args:
            config (ResourceConfiguration): The resource configuration.
            
        Returns:
            Dict[str, Any]: The generated ARM template.
        """
        pass
    
    def collect_parameters_interactively(self) -> Dict[str, Any]:
        """
        Collect parameters from user through interactive prompts.
        
        This method should be overridden by specific resource implementations
        to provide custom parameter collection logic.
        
        Returns:
            Dict[str, Any]: The collected parameters.
        """
        # Basic implementation - should be overridden
        parameters = {}
        
        for param in self.get_required_parameters():
            value = input(f"Enter {param.name} ({param.description}): ")
            parameters[param.name] = value
        
        for param in self.get_optional_parameters():
            value = input(f"Enter {param.name} (optional - {param.description}): ")
            if value.strip():
                parameters[param.name] = value
        
        return parameters
    
    def create_configuration(self, name: str, location: str, resource_group: str, 
                           parameters: Dict[str, Any], tags: Optional[Dict[str, str]] = None) -> ResourceConfiguration:
        """
        Create a resource configuration instance.
        
        Args:
            name (str): The resource name.
            location (str): The Azure region.
            resource_group (str): The resource group name.
            parameters (Dict[str, Any]): The resource parameters.
            tags (Optional[Dict[str, str]]): Optional resource tags.
            
        Returns:
            ResourceConfiguration: The created configuration.
        """
        return ResourceConfiguration(
            resource_type=self.resource_type,
            name=name,
            location=location,
            resource_group=resource_group,
            parameters=parameters,
            tags=tags or {}
        )


class StorageResource(BaseResource):
    """Base class for Azure Storage resources."""
    
    def __init__(self, resource_type: str):
        super().__init__(resource_type)
        self.arm_api_version = "2021-04-01"
    
    def validate_storage_account_name(self, name: str) -> List[str]:
        """
        Validate a storage account name according to Azure rules.
        
        Args:
            name (str): The storage account name to validate.
            
        Returns:
            List[str]: List of validation errors (empty if valid).
        """
        errors = []
        
        # Length check
        if not (3 <= len(name) <= 24):
            errors.append("Storage account name must be between 3 and 24 characters long")
        
        # Character check
        if not name.isalnum():
            errors.append("Storage account name can only contain letters and numbers")
        
        # Lowercase check
        if not name.islower():
            errors.append("Storage account name must be lowercase")
        
        return errors


class ComputeResource(BaseResource):
    """Base class for Azure Compute resources."""
    
    def __init__(self, resource_type: str):
        super().__init__(resource_type)
        self.arm_api_version = "2021-07-01"


class NetworkResource(BaseResource):
    """Base class for Azure Network resources."""
    
    def __init__(self, resource_type: str):
        super().__init__(resource_type)
        self.arm_api_version = "2021-05-01"