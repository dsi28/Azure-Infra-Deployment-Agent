"""
Unit tests for resources.base module.

Tests for base resource classes including BaseResource, StorageResource,
ComputeResource, and NetworkResource with various scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any
from datetime import datetime

from src.resources.base import (
    BaseResource,
    StorageResource,
    ComputeResource,
    NetworkResource,
    ResourceParameter,
    ResourceConfiguration,
    ValidationResult,
    ResourceStatus
)


class TestResourceStatus:
    """Test cases for ResourceStatus enum."""
    
    def test_resource_status_values(self):
        """Test ResourceStatus enum values."""
        assert ResourceStatus.DRAFT.value == "draft"
        assert ResourceStatus.VALIDATED.value == "validated"
        assert ResourceStatus.DEPLOYING.value == "deploying"
        assert ResourceStatus.DEPLOYED.value == "deployed"
        assert ResourceStatus.FAILED.value == "failed"
        assert ResourceStatus.DELETED.value == "deleted"


class TestResourceParameter:
    """Test cases for ResourceParameter model."""
    
    def test_resource_parameter_creation_success(self):
        """Test successful ResourceParameter creation."""
        param = ResourceParameter(
            name="storageAccountName",
            type="string",
            description="Name of the storage account",
            required=True,
            default_value="defaultstorage",
            allowed_values=["test1", "test2"],
            validation_pattern="^[a-z0-9]{3,24}$"
        )
        
        assert param.name == "storageAccountName"
        assert param.type == "string"
        assert param.description == "Name of the storage account"
        assert param.required is True
        assert param.default_value == "defaultstorage"
        assert param.allowed_values == ["test1", "test2"]
        assert param.validation_pattern == "^[a-z0-9]{3,24}$"
    
    def test_resource_parameter_minimal_creation(self):
        """Test ResourceParameter creation with minimal fields."""
        param = ResourceParameter(
            name="location",
            type="string",
            description="Azure region"
        )
        
        assert param.name == "location"
        assert param.type == "string"
        assert param.description == "Azure region"
        assert param.required is True  # Default
        assert param.default_value is None
        assert param.allowed_values is None
        assert param.validation_pattern is None
    
    def test_resource_parameter_optional_creation(self):
        """Test ResourceParameter creation for optional parameter."""
        param = ResourceParameter(
            name="tags",
            type="object",
            description="Resource tags",
            required=False
        )
        
        assert param.required is False


class TestResourceConfiguration:
    """Test cases for ResourceConfiguration model."""
    
    def test_resource_configuration_creation_success(self):
        """Test successful ResourceConfiguration creation."""
        config = ResourceConfiguration(
            resource_type="Microsoft.Storage/storageAccounts",
            name="teststorage",
            location="East US",
            resource_group="test-rg",
            tags={"environment": "test"},
            parameters={"sku": "Standard_LRS"}
        )
        
        assert config.resource_type == "Microsoft.Storage/storageAccounts"
        assert config.name == "teststorage"
        assert config.location == "East US"
        assert config.resource_group == "test-rg"
        assert config.tags == {"environment": "test"}
        assert config.parameters == {"sku": "Standard_LRS"}
        assert config.status == ResourceStatus.DRAFT
    
    def test_resource_configuration_minimal_creation(self):
        """Test ResourceConfiguration creation with minimal fields."""
        config = ResourceConfiguration(
            resource_type="Microsoft.Web/sites",
            name="testapp",
            location="West US",
            resource_group="app-rg"
        )
        
        assert config.resource_type == "Microsoft.Web/sites"
        assert config.name == "testapp"
        assert config.location == "West US"
        assert config.resource_group == "app-rg"
        assert config.tags is None
        assert config.parameters == {}
        assert config.status == ResourceStatus.DRAFT


class TestValidationResult:
    """Test cases for ValidationResult model."""
    
    def test_validation_result_success(self):
        """Test successful ValidationResult creation."""
        result = ValidationResult(
            is_valid=True,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        
        assert result.is_valid is True
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]
    
    def test_validation_result_defaults(self):
        """Test ValidationResult creation with defaults."""
        result = ValidationResult(is_valid=False)
        
        assert result.is_valid is False
        assert result.errors == []
        assert result.warnings == []


class ConcreteBaseResource(BaseResource):
    """Concrete implementation of BaseResource for testing."""
    
    def validate_configuration(self, config: ResourceConfiguration) -> ValidationResult:
        """Test implementation of validate_configuration."""
        errors = []
        warnings = []
        
        if not config.name:
            errors.append("Resource name is required")
        
        if not config.location:
            errors.append("Location is required")
        
        if config.name and len(config.name) < 3:
            warnings.append("Resource name is very short")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def generate_arm_template(self, config: ResourceConfiguration) -> Dict[str, Any]:
        """Test implementation of generate_arm_template."""
        return {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {
                    "type": config.resource_type,
                    "apiVersion": self.arm_api_version,
                    "name": config.name,
                    "location": config.location
                }
            ]
        }


class TestBaseResource:
    """Test cases for BaseResource class."""
    
    def test_base_resource_initialization_success(self):
        """Test successful BaseResource initialization."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        assert resource.resource_type == "Microsoft.Storage/storageAccounts"
        assert resource.parameters == []
        assert resource.arm_api_version == "2021-01-01"
    
    def test_add_parameter_success(self):
        """Test successful parameter addition."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        param = ResourceParameter(
            name="name",
            type="string",
            description="Storage account name"
        )
        
        resource.add_parameter(param)
        
        assert len(resource.parameters) == 1
        assert resource.parameters[0] == param
    
    def test_get_required_parameters_success(self):
        """Test getting required parameters."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        required_param = ResourceParameter(
            name="name",
            type="string",
            description="Storage account name",
            required=True
        )
        optional_param = ResourceParameter(
            name="tags",
            type="object",
            description="Resource tags",
            required=False
        )
        
        resource.add_parameter(required_param)
        resource.add_parameter(optional_param)
        
        required = resource.get_required_parameters()
        
        assert len(required) == 1
        assert required[0] == required_param
    
    def test_get_optional_parameters_success(self):
        """Test getting optional parameters."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        required_param = ResourceParameter(
            name="name",
            type="string",
            description="Storage account name",
            required=True
        )
        optional_param = ResourceParameter(
            name="tags",
            type="object",
            description="Resource tags",
            required=False
        )
        
        resource.add_parameter(required_param)
        resource.add_parameter(optional_param)
        
        optional = resource.get_optional_parameters()
        
        assert len(optional) == 1
        assert optional[0] == optional_param
    
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        config = ResourceConfiguration(
            resource_type="Microsoft.Storage/storageAccounts",
            name="teststorage",
            location="East US",
            resource_group="test-rg"
        )
        
        result = resource.validate_configuration(config)
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        config = ResourceConfiguration(
            resource_type="Microsoft.Storage/storageAccounts",
            name="",  # Empty name
            location="",  # Empty location
            resource_group="test-rg"
        )
        
        result = resource.validate_configuration(config)
        
        assert result.is_valid is False
        assert "Resource name is required" in result.errors
        assert "Location is required" in result.errors
    
    def test_validate_configuration_warnings(self):
        """Test configuration validation with warnings."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        config = ResourceConfiguration(
            resource_type="Microsoft.Storage/storageAccounts",
            name="ab",  # Short name
            location="East US",
            resource_group="test-rg"
        )
        
        result = resource.validate_configuration(config)
        
        assert result.is_valid is True
        assert "Resource name is very short" in result.warnings
    
    def test_generate_arm_template_success(self):
        """Test successful ARM template generation."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        config = ResourceConfiguration(
            resource_type="Microsoft.Storage/storageAccounts",
            name="teststorage",
            location="East US",
            resource_group="test-rg"
        )
        
        template = resource.generate_arm_template(config)
        
        assert template["$schema"] == "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
        assert template["contentVersion"] == "1.0.0.0"
        assert len(template["resources"]) == 1
        
        resource_def = template["resources"][0]
        assert resource_def["type"] == "Microsoft.Storage/storageAccounts"
        assert resource_def["name"] == "teststorage"
        assert resource_def["location"] == "East US"
    
    def test_create_configuration_success(self):
        """Test successful configuration creation."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        config = resource.create_configuration(
            name="teststorage",
            location="East US",
            resource_group="test-rg",
            parameters={"sku": "Standard_LRS"},
            tags={"env": "test"}
        )
        
        assert isinstance(config, ResourceConfiguration)
        assert config.resource_type == "Microsoft.Storage/storageAccounts"
        assert config.name == "teststorage"
        assert config.location == "East US"
        assert config.resource_group == "test-rg"
        assert config.parameters == {"sku": "Standard_LRS"}
        assert config.tags == {"env": "test"}
    
    def test_create_configuration_no_tags(self):
        """Test configuration creation without tags."""
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        config = resource.create_configuration(
            name="teststorage",
            location="East US",
            resource_group="test-rg",
            parameters={"sku": "Standard_LRS"}
        )
        
        assert config.tags == {}
    
    @patch('builtins.input')
    def test_collect_parameters_interactively_success(self, mock_input):
        """Test interactive parameter collection."""
        mock_input.side_effect = ["teststorage", "East US", "Standard_LRS", ""]
        
        resource = ConcreteBaseResource("Microsoft.Storage/storageAccounts")
        
        # Add some parameters
        resource.add_parameter(ResourceParameter(
            name="name",
            type="string",
            description="Storage account name",
            required=True
        ))
        resource.add_parameter(ResourceParameter(
            name="location",
            type="string",
            description="Azure region",
            required=True
        ))
        resource.add_parameter(ResourceParameter(
            name="sku",
            type="string",
            description="Storage SKU",
            required=False
        ))
        resource.add_parameter(ResourceParameter(
            name="kind",
            type="string",
            description="Storage kind",
            required=False
        ))
        
        params = resource.collect_parameters_interactively()
        
        assert params["name"] == "teststorage"
        assert params["location"] == "East US"
        assert params["sku"] == "Standard_LRS"
        assert "kind" not in params  # Empty optional parameter


class TestStorageResource:
    """Test cases for StorageResource class."""
    
    def test_storage_resource_initialization_success(self):
        """Test successful StorageResource initialization."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        assert resource.resource_type == "Microsoft.Storage/storageAccounts"
        assert resource.arm_api_version == "2021-04-01"
    
    def test_validate_storage_account_name_success(self):
        """Test successful storage account name validation."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("teststorage123")
        
        assert errors == []
    
    def test_validate_storage_account_name_too_short_failure(self):
        """Test storage account name validation - too short."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("ab")
        
        assert "Storage account name must be between 3 and 24 characters long" in errors
    
    def test_validate_storage_account_name_too_long_failure(self):
        """Test storage account name validation - too long."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("a" * 25)
        
        assert "Storage account name must be between 3 and 24 characters long" in errors
    
    def test_validate_storage_account_name_invalid_chars_failure(self):
        """Test storage account name validation - invalid characters."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("test-storage")
        
        assert "Storage account name can only contain letters and numbers" in errors
    
    def test_validate_storage_account_name_uppercase_failure(self):
        """Test storage account name validation - uppercase letters."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("TestStorage")
        
        assert "Storage account name must be lowercase" in errors
    
    def test_validate_storage_account_name_multiple_errors_failure(self):
        """Test storage account name validation - multiple errors."""
        resource = StorageResource("Microsoft.Storage/storageAccounts")
        
        errors = resource.validate_storage_account_name("AB")  # Too short, uppercase
        
        assert len(errors) == 2
        assert "Storage account name must be between 3 and 24 characters long" in errors
        assert "Storage account name must be lowercase" in errors


class TestComputeResource:
    """Test cases for ComputeResource class."""
    
    def test_compute_resource_initialization_success(self):
        """Test successful ComputeResource initialization."""
        resource = ComputeResource("Microsoft.Web/sites")
        
        assert resource.resource_type == "Microsoft.Web/sites"
        assert resource.arm_api_version == "2021-07-01"


class TestNetworkResource:
    """Test cases for NetworkResource class."""
    
    def test_network_resource_initialization_success(self):
        """Test successful NetworkResource initialization."""
        resource = NetworkResource("Microsoft.Network/virtualNetworks")
        
        assert resource.resource_type == "Microsoft.Network/virtualNetworks"
        assert resource.arm_api_version == "2021-05-01"