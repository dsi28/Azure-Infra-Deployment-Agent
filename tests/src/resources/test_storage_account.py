"""
Unit tests for resources.storage_account module.

Tests for StorageAccountConfiguration, StorageAccountResource, and related
functionality with expected use cases, edge cases, and failure scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

from src.resources.storage_account import (
    StorageAccountResource,
    create_storage_account_resource
)
from src.resources.storage_config import StorageAccountConfiguration
from src.resources.base import ResourceRequest, ResourceResponse, ResourceStatus
from src.resources.validation_result import ValidationResult


class TestStorageAccountConfiguration:
    """Test cases for StorageAccountConfiguration class."""
    
    def test_storage_account_configuration_initialization_default(self):
        """Test StorageAccountConfiguration with default values."""
        config = StorageAccountConfiguration()
        
        assert config.name is None
        assert config.resource_group is None
        assert config.location is None
        assert config.performance_tier == "Standard"
        assert config.replication_type == "LRS"
        assert config.access_tier == "Hot"
        assert config.kind == "StorageV2"
        assert config.tags == {}
        assert config.enable_https_only is True
        assert config.enable_hierarchical_namespace is False
    
    def test_storage_account_configuration_initialization_custom(self):
        """Test StorageAccountConfiguration with custom values."""
        config = StorageAccountConfiguration(
            name="teststorage123",
            resource_group="test-rg",
            location="East US",
            performance_tier="Premium",
            replication_type="ZRS",
            access_tier="Cool",
            kind="FileStorage",
            tags={"env": "test", "owner": "team"},
            enable_https_only=False,
            enable_hierarchical_namespace=True
        )
        
        assert config.name == "teststorage123"
        assert config.resource_group == "test-rg"
        assert config.location == "East US"
        assert config.performance_tier == "Premium"
        assert config.replication_type == "ZRS"
        assert config.access_tier == "Cool"
        assert config.kind == "FileStorage"
        assert config.tags == {"env": "test", "owner": "team"}
        assert config.enable_https_only is False
        assert config.enable_hierarchical_namespace is True
    
    def test_get_required_parameters_all_none(self):
        """Test getting required parameters when all are None."""
        config = StorageAccountConfiguration()
        
        required = config.get_required_parameters()
        
        assert "name" in required
        assert "resource_group" in required
        assert "location" in required
        assert len(required) == 3
    
    def test_get_required_parameters_some_set(self):
        """Test getting required parameters when some are set."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg"
        )
        
        required = config.get_required_parameters()
        
        assert "name" not in required
        assert "resource_group" not in required
        assert "location" in required
        assert len(required) == 1
    
    def test_get_required_parameters_all_set(self):
        """Test getting required parameters when all are set."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US"
        )
        
        required = config.get_required_parameters()
        
        assert len(required) == 0
    
    def test_get_missing_required_parameters_some_missing(self):
        """Test getting missing required parameters."""
        config = StorageAccountConfiguration(name="test")
        
        missing = config.get_missing_required_parameters()
        
        assert "resource_group" in missing
        assert "location" in missing
        assert "name" not in missing
        assert len(missing) == 2
    
    def test_to_dict_success(self):
        """Test converting configuration to dictionary."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US",
            tags={"env": "test"}
        )
        
        result = config.to_dict()
        
        assert result["name"] == "teststorage"
        assert result["resource_group"] == "test-rg"
        assert result["location"] == "East US"
        assert result["performance_tier"] == "Standard"
        assert result["tags"] == {"env": "test"}
        assert result["enable_https_only"] is True


class TestStorageAccountResource:
    """Test cases for StorageAccountResource class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.resource = StorageAccountResource()
    
    def test_storage_account_resource_initialization(self):
        """Test StorageAccountResource initialization."""
        resource = StorageAccountResource()
        
        assert resource.resource_type == "Microsoft.Storage/storageAccounts"
        assert hasattr(resource, 'validator')
    
    @patch('src.resources.storage_account.create_storage_validator')
    def test_storage_account_resource_initialization_with_mock_validator(self, mock_validator):
        """Test initialization with mocked validator."""
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        
        resource = StorageAccountResource()
        
        assert resource.validator == mock_validator_instance
        mock_validator.assert_called_once()
    
    def test_process_success_complete_config(self):
        """Test successful processing with complete configuration."""
        # Mock validator
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_info("Valid configuration")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Create complete request
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US"
        )
        request = ResourceRequest(
            resource_type="Microsoft.Storage/storageAccounts",
            parameters=config.to_dict()
        )
        
        response = self.resource.process(request)
        
        assert response.success is True
        assert response.resource_type == "Microsoft.Storage/storageAccounts"
        assert "Valid configuration" in response.message
        assert response.configuration is not None
        mock_validator.validate_all_parameters.assert_called_once()
    
    def test_process_failure_validation_errors(self):
        """Test processing failure due to validation errors."""
        # Mock validator with errors
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_error("Invalid storage account name")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Create request with invalid config
        request = ResourceRequest(
            resource_type="Microsoft.Storage/storageAccounts",
            parameters={"name": "invalid-name!"}
        )
        
        response = self.resource.process(request)
        
        assert response.success is False
        assert "Validation failed" in response.message
        assert "Invalid storage account name" in response.message
        assert response.configuration is None
    
    def test_process_incomplete_config_triggers_interactive(self):
        """Test that incomplete config triggers interactive collection."""
        # Mock validator
        mock_validator = Mock()
        validation_result = ValidationResult()
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Mock interactive collection
        complete_config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US"
        )
        
        with patch.object(self.resource, 'collect_parameters_interactively', return_value=complete_config):
            # Create incomplete request
            request = ResourceRequest(
                resource_type="Microsoft.Storage/storageAccounts",
                parameters={"name": "teststorage"}  # Missing required fields
            )
            
            response = self.resource.process(request)
            
            assert response.success is True
            assert response.configuration == complete_config
    
    @patch('builtins.input')
    def test_collect_parameters_interactively_new_config(self, mock_input):
        """Test interactive parameter collection with new config."""
        # Set up input responses
        mock_input.side_effect = [
            "teststorage123",  # name
            "test-resource-group",  # resource_group
            "East US",  # location
            "Premium",  # performance_tier
            "ZRS",  # replication_type
            "Cool",  # access_tier
            "FileStorage"  # kind
        ]
        
        config = self.resource.collect_parameters_interactively()
        
        assert config.name == "teststorage123"
        assert config.resource_group == "test-resource-group"
        assert config.location == "East US"
        assert config.performance_tier == "Premium"
        assert config.replication_type == "ZRS"
        assert config.access_tier == "Cool"
        assert config.kind == "FileStorage"
    
    @patch('builtins.input')
    def test_collect_parameters_interactively_partial_config(self, mock_input):
        """Test interactive parameter collection with existing partial config."""
        # Set up input responses for missing parameters only
        mock_input.side_effect = [
            "test-resource-group",  # resource_group
            "West US"  # location
        ]
        
        # Start with partial config
        existing_config = StorageAccountConfiguration(name="existing-storage")
        
        config = self.resource.collect_parameters_interactively(existing_config)
        
        assert config.name == "existing-storage"  # Unchanged
        assert config.resource_group == "test-resource-group"  # New
        assert config.location == "West US"  # New
    
    @patch('builtins.input')
    def test_collect_parameters_interactively_default_values(self, mock_input):
        """Test interactive collection with default value acceptance."""
        # Use empty strings to accept defaults
        mock_input.side_effect = [
            "teststorage",  # name
            "test-rg",  # resource_group  
            "East US",  # location
            "",  # performance_tier (accept default)
            "",  # replication_type (accept default)
            "",  # access_tier (accept default)
            ""   # kind (accept default)
        ]
        
        config = self.resource.collect_parameters_interactively()
        
        assert config.name == "teststorage"
        assert config.resource_group == "test-rg"
        assert config.location == "East US"
        assert config.performance_tier == "Standard"  # Default
        assert config.replication_type == "LRS"  # Default
        assert config.access_tier == "Hot"  # Default
        assert config.kind == "StorageV2"  # Default
    
    def test_ask_for_parameter_with_default(self):
        """Test parameter asking with default value."""
        with patch('builtins.input', return_value=""):
            result = self.resource._ask_for_parameter("Test Parameter", "default_value")
            assert result == "default_value"
    
    def test_ask_for_parameter_with_input(self):
        """Test parameter asking with user input."""
        with patch('builtins.input', return_value="user_input"):
            result = self.resource._ask_for_parameter("Test Parameter", "default_value")
            assert result == "user_input"
    
    def test_ask_for_parameter_no_default(self):
        """Test parameter asking without default value."""
        with patch('builtins.input', return_value="user_input"):
            result = self.resource._ask_for_parameter("Test Parameter")
            assert result == "user_input"
    
    def test_validate_configuration_success(self):
        """Test configuration validation success."""
        # Mock validator
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_info("Valid")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US"
        )
        
        result = self.resource.validate_configuration(config)
        
        assert result.is_valid is True
        mock_validator.validate_all_parameters.assert_called_once_with(config.to_dict())
    
    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        # Mock validator with errors
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_error("Invalid name")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        config = StorageAccountConfiguration(name="bad-name!")
        
        result = self.resource.validate_configuration(config)
        
        assert result.is_valid is False
        assert "Invalid name" in result.errors


class TestCreateStorageAccountResource:
    """Test cases for create_storage_account_resource factory function."""
    
    def test_create_storage_account_resource_success(self):
        """Test successful storage account resource creation."""
        resource = create_storage_account_resource()
        
        assert isinstance(resource, StorageAccountResource)
        assert resource.resource_type == "Microsoft.Storage/storageAccounts"
    
    @patch('src.resources.storage_account.create_storage_validator')
    def test_create_storage_account_resource_with_validator(self, mock_validator):
        """Test resource creation with validator initialization."""
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        
        resource = create_storage_account_resource()
        
        assert resource.validator == mock_validator_instance
        mock_validator.assert_called_once()


class TestStorageAccountIntegration:
    """Integration tests for storage account functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.resource = StorageAccountResource()
    
    def test_complete_storage_account_workflow_success(self):
        """Test complete workflow from request to response."""
        # Mock validator to return valid result
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_info("Configuration is valid")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Create complete request
        request = ResourceRequest(
            resource_type="Microsoft.Storage/storageAccounts",
            parameters={
                "name": "teststorage123",
                "resource_group": "test-resources",
                "location": "East US",
                "performance_tier": "Standard",
                "replication_type": "GRS"
            }
        )
        
        response = self.resource.process(request)
        
        assert response.success is True
        assert response.resource_type == "Microsoft.Storage/storageAccounts"
        assert response.configuration is not None
        assert response.configuration.name == "teststorage123"
        assert response.configuration.resource_group == "test-resources"
        assert response.configuration.location == "East US"
    
    def test_complete_storage_account_workflow_with_validation_errors(self):
        """Test complete workflow with validation failures."""
        # Mock validator to return errors
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_error("Storage account name too short")
        validation_result.add_error("Invalid replication type")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Create request with invalid parameters
        request = ResourceRequest(
            resource_type="Microsoft.Storage/storageAccounts",
            parameters={
                "name": "ab",  # Too short
                "resource_group": "test-rg",
                "location": "East US",
                "replication_type": "INVALID"  # Invalid replication
            }
        )
        
        response = self.resource.process(request)
        
        assert response.success is False
        assert "Validation failed" in response.message
        assert "Storage account name too short" in response.message
        assert "Invalid replication type" in response.message
        assert response.configuration is None
    
    @patch('builtins.input')
    def test_interactive_workflow_integration(self, mock_input):
        """Test integration with interactive parameter collection."""
        # Set up interactive responses
        mock_input.side_effect = [
            "interactivestorage",
            "interactive-rg", 
            "West US",
            "",  # Accept default performance tier
            "",  # Accept default replication
            "",  # Accept default access tier
            ""   # Accept default kind
        ]
        
        # Mock validator
        mock_validator = Mock()
        validation_result = ValidationResult()
        validation_result.add_info("Valid configuration")
        mock_validator.validate_all_parameters.return_value = validation_result
        self.resource.validator = mock_validator
        
        # Create incomplete request (missing required parameters)
        request = ResourceRequest(
            resource_type="Microsoft.Storage/storageAccounts",
            parameters={}  # Empty parameters to trigger interactive
        )
        
        response = self.resource.process(request)
        
        assert response.success is True
        assert response.configuration.name == "interactivestorage"
        assert response.configuration.resource_group == "interactive-rg"
        assert response.configuration.location == "West US"
        assert response.configuration.performance_tier == "Standard"  # Default
    
    def test_real_world_configuration_scenarios(self):
        """Test realistic configuration scenarios."""
        scenarios = [
            {
                "name": "Basic storage account",
                "params": {
                    "name": "companydata2023",
                    "resource_group": "production-resources",
                    "location": "East US"
                },
                "should_succeed": True
            },
            {
                "name": "Premium storage account",
                "params": {
                    "name": "premiumstorage",
                    "resource_group": "high-perf-rg",
                    "location": "West US",
                    "performance_tier": "Premium",
                    "replication_type": "ZRS",
                    "kind": "FileStorage"
                },
                "should_succeed": True
            },
            {
                "name": "Invalid configuration",
                "params": {
                    "name": "ab",  # Too short
                    "resource_group": "",  # Empty
                    "location": "Invalid Region"
                },
                "should_succeed": False
            }
        ]
        
        # Mock validator to behave appropriately
        mock_validator = Mock()
        self.resource.validator = mock_validator
        
        for scenario in scenarios:
            # Set up validator response
            validation_result = ValidationResult()
            if scenario["should_succeed"]:
                validation_result.add_info("Valid configuration")
            else:
                validation_result.add_error("Configuration has errors")
            
            mock_validator.validate_all_parameters.return_value = validation_result
            
            # Create request
            request = ResourceRequest(
                resource_type="Microsoft.Storage/storageAccounts",
                parameters=scenario["params"]
            )
            
            response = self.resource.process(request)
            
            if scenario["should_succeed"]:
                assert response.success is True, f"Scenario '{scenario['name']}' should succeed"
            else:
                assert response.success is False, f"Scenario '{scenario['name']}' should fail"