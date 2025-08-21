"""
Unit tests for resources.validators module.

Tests for validation utilities including ValidationResult, StorageAccountValidator,
and various validation scenarios with expected use cases, edge cases, and failures.
"""

import pytest
from src.resources.validators import (
    StorageAccountValidator,
    create_storage_validator
)
from src.resources.validation_result import ValidationSeverity, ValidationResult


class TestValidationSeverity:
    """Test cases for ValidationSeverity enum."""
    
    def test_validation_severity_values(self):
        """Test ValidationSeverity enum values."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationResult:
    """Test cases for ValidationResult class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.result = ValidationResult()
    
    def test_validation_result_initialization(self):
        """Test ValidationResult initialization."""
        result = ValidationResult()
        
        assert result.errors == []
        assert result.warnings == []
        assert result.info == []
        assert result.is_valid is True
        assert result.has_warnings is False
        assert result.message_count == 0
    
    def test_add_error_success(self):
        """Test successful error addition."""
        self.result.add_error("Test error message")
        
        assert len(self.result.errors) == 1
        assert "Test error message" in self.result.errors
        assert self.result.is_valid is False
        assert self.result.message_count == 1
    
    def test_add_warning_success(self):
        """Test successful warning addition."""
        self.result.add_warning("Test warning message")
        
        assert len(self.result.warnings) == 1
        assert "Test warning message" in self.result.warnings
        assert self.result.has_warnings is True
        assert self.result.is_valid is True  # Warnings don't make invalid
        assert self.result.message_count == 1
    
    def test_add_info_success(self):
        """Test successful info addition."""
        self.result.add_info("Test info message")
        
        assert len(self.result.info) == 1
        assert "Test info message" in self.result.info
        assert self.result.is_valid is True
        assert self.result.message_count == 1
    
    def test_is_valid_with_errors(self):
        """Test is_valid property with errors."""
        self.result.add_error("Error")
        self.result.add_warning("Warning")
        
        assert self.result.is_valid is False
    
    def test_is_valid_without_errors(self):
        """Test is_valid property without errors."""
        self.result.add_warning("Warning")
        self.result.add_info("Info")
        
        assert self.result.is_valid is True
    
    def test_get_summary_valid_no_warnings(self):
        """Test summary for valid result without warnings."""
        summary = self.result.get_summary()
        
        assert summary == "Valid"
    
    def test_get_summary_valid_with_warnings(self):
        """Test summary for valid result with warnings."""
        self.result.add_warning("Warning 1")
        self.result.add_warning("Warning 2")
        
        summary = self.result.get_summary()
        
        assert summary == "Valid with 2 warning(s)"
    
    def test_get_summary_invalid(self):
        """Test summary for invalid result."""
        self.result.add_error("Error 1")
        self.result.add_error("Error 2")
        self.result.add_warning("Warning 1")
        
        summary = self.result.get_summary()
        
        assert summary == "2 error(s), 1 warning(s)"
    
    def test_get_all_messages_success(self):
        """Test getting all messages with severities."""
        self.result.add_error("Error message")
        self.result.add_warning("Warning message")
        self.result.add_info("Info message")
        
        messages = self.result.get_all_messages()
        
        assert len(messages) == 3
        
        # Check that all severity types are present
        severities = [msg[0] for msg in messages]
        assert ValidationSeverity.ERROR in severities
        assert ValidationSeverity.WARNING in severities
        assert ValidationSeverity.INFO in severities
        
        # Check messages content
        message_texts = [msg[1] for msg in messages]
        assert "Error message" in message_texts
        assert "Warning message" in message_texts
        assert "Info message" in message_texts


class TestStorageAccountValidator:
    """Test cases for StorageAccountValidator class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = StorageAccountValidator()
    
    def test_storage_account_validator_initialization(self):
        """Test StorageAccountValidator initialization."""
        validator = StorageAccountValidator()
        
        assert validator.valid_performance_tiers == {"Standard", "Premium"}
        assert "LRS" in validator.valid_replication_types
        assert "GRS" in validator.valid_replication_types
        assert "Hot" in validator.valid_access_tiers
        assert "StorageV2" in validator.valid_kinds
        assert "East US" in validator.valid_regions
    
    def test_validate_storage_account_name_success(self):
        """Test successful storage account name validation."""
        valid_names = [
            "teststorage123",
            "mycompanystorage",
            "storage4testing",
            "abc123def456"
        ]
        
        for name in valid_names:
            result = self.validator.validate_storage_account_name(name)
            assert result.is_valid, f"Name '{name}' should be valid: {result.errors}"
    
    def test_validate_storage_account_name_empty_failure(self):
        """Test storage account name validation with empty name."""
        result = self.validator.validate_storage_account_name("")
        
        assert not result.is_valid
        assert "cannot be empty" in result.errors[0]
    
    def test_validate_storage_account_name_too_short_failure(self):
        """Test storage account name validation - too short."""
        result = self.validator.validate_storage_account_name("ab")
        
        assert not result.is_valid
        assert "at least 3 characters" in result.errors[0]
    
    def test_validate_storage_account_name_too_long_failure(self):
        """Test storage account name validation - too long."""
        long_name = "a" * 25  # 25 characters
        result = self.validator.validate_storage_account_name(long_name)
        
        assert not result.is_valid
        assert "no more than 24 characters" in result.errors[0]
    
    def test_validate_storage_account_name_invalid_chars_failure(self):
        """Test storage account name validation - invalid characters."""
        invalid_names = [
            "test-storage",  # Hyphen not allowed
            "Test_Storage",  # Uppercase not allowed
            "test.storage",  # Period not allowed
            "test@storage"   # Special chars not allowed
        ]
        
        for name in invalid_names:
            result = self.validator.validate_storage_account_name(name)
            assert not result.is_valid, f"Name '{name}' should be invalid"
            assert "lowercase letters and numbers" in result.errors[0]
    
    def test_validate_storage_account_name_reserved_failure(self):
        """Test storage account name validation - reserved names."""
        reserved_names = ["con", "aux", "nul", "prn"]
        
        for name in reserved_names:
            result = self.validator.validate_storage_account_name(name)
            assert not result.is_valid
            assert "reserved name" in result.errors[0]
    
    def test_validate_storage_account_name_warnings(self):
        """Test storage account name validation warnings."""
        # All numbers warning
        result = self.validator.validate_storage_account_name("12345")
        assert result.is_valid
        assert result.has_warnings
        assert "should include letters" in result.warnings[0]
        
        # Short name warning
        result = self.validator.validate_storage_account_name("abc")
        assert result.is_valid
        assert result.has_warnings
        assert "longer name" in result.warnings[0]
    
    def test_validate_resource_group_name_success(self):
        """Test successful resource group name validation."""
        valid_names = [
            "test-resource-group",
            "MyResourceGroup",
            "rg_test.001",
            "resource(group)name"
        ]
        
        for name in valid_names:
            result = self.validator.validate_resource_group_name(name)
            assert result.is_valid, f"Resource group '{name}' should be valid: {result.errors}"
    
    def test_validate_resource_group_name_failure(self):
        """Test resource group name validation failures."""
        # Empty name
        result = self.validator.validate_resource_group_name("")
        assert not result.is_valid
        
        # Too long name
        long_name = "a" * 91
        result = self.validator.validate_resource_group_name(long_name)
        assert not result.is_valid
        assert "no more than 90 characters" in result.errors[0]
        
        # Invalid characters
        result = self.validator.validate_resource_group_name("test@resource#group")
        assert not result.is_valid
        
        # Ends with period
        result = self.validator.validate_resource_group_name("test-rg.")
        assert not result.is_valid
        assert "cannot end with a period" in result.errors[0]
    
    def test_validate_performance_tier_success(self):
        """Test successful performance tier validation."""
        for tier in ["Standard", "Premium"]:
            result = self.validator.validate_performance_tier(tier)
            assert result.is_valid
            assert len(result.info) > 0  # Should have guidance
    
    def test_validate_performance_tier_failure(self):
        """Test performance tier validation failure."""
        result = self.validator.validate_performance_tier("InvalidTier")
        
        assert not result.is_valid
        assert "Invalid performance tier" in result.errors[0]
        assert "Standard" in result.errors[0]
        assert "Premium" in result.errors[0]
    
    def test_validate_replication_type_success(self):
        """Test successful replication type validation."""
        valid_types = ["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"]
        
        for replication in valid_types:
            result = self.validator.validate_replication_type(replication)
            assert result.is_valid, f"Replication '{replication}' should be valid"
            assert len(result.info) > 0  # Should have guidance
    
    def test_validate_replication_type_with_premium_tier(self):
        """Test replication type validation with Premium performance tier."""
        # Valid for Premium
        result = self.validator.validate_replication_type("LRS", "Premium")
        assert result.is_valid
        
        result = self.validator.validate_replication_type("ZRS", "Premium")
        assert result.is_valid
        
        # Invalid for Premium
        result = self.validator.validate_replication_type("GRS", "Premium")
        assert not result.is_valid
        assert "Premium performance tier only supports" in result.errors[0]
    
    def test_validate_access_tier_success(self):
        """Test successful access tier validation."""
        valid_tiers = ["Hot", "Cool", "Archive"]
        
        for tier in valid_tiers:
            result = self.validator.validate_access_tier(tier)
            assert result.is_valid
            assert len(result.info) > 0  # Should have guidance
    
    def test_validate_access_tier_with_account_kind(self):
        """Test access tier validation with specific account kinds."""
        # Should warn for FileStorage
        result = self.validator.validate_access_tier("Hot", "FileStorage")
        assert result.is_valid
        assert result.has_warnings
        assert "not applicable for FileStorage" in result.warnings[0]
    
    def test_validate_region_success(self):
        """Test successful region validation."""
        common_regions = ["East US", "West US", "North Europe", "Southeast Asia"]
        
        for region in common_regions:
            result = self.validator.validate_region(region)
            assert result.is_valid
            assert f"Region '{region}' is valid" in result.info[0]
    
    def test_validate_region_uncommon_warning(self):
        """Test region validation with uncommon region."""
        result = self.validator.validate_region("Unknown Region")
        
        assert result.is_valid  # Still valid, just warns
        assert result.has_warnings
        assert "not in the common regions list" in result.warnings[0]
    
    def test_validate_storage_account_kind_success(self):
        """Test successful storage account kind validation."""
        valid_kinds = ["StorageV2", "Storage", "BlobStorage", "FileStorage", "BlockBlobStorage"]
        
        for kind in valid_kinds:
            result = self.validator.validate_storage_account_kind(kind)
            assert result.is_valid
            assert len(result.info) > 0  # Should have guidance
    
    def test_validate_storage_account_kind_legacy_warning(self):
        """Test storage account kind validation with legacy kind."""
        result = self.validator.validate_storage_account_kind("Storage")
        
        assert result.is_valid
        assert result.has_warnings
        assert "legacy" in result.warnings[0]
    
    def test_validate_all_parameters_success(self):
        """Test validation of all parameters together."""
        params = {
            "name": "teststorage123",
            "resource_group": "test-rg",
            "location": "East US",
            "performance_tier": "Standard",
            "replication_type": "LRS",
            "access_tier": "Hot",
            "kind": "StorageV2"
        }
        
        result = self.validator.validate_all_parameters(params)
        assert result.is_valid
    
    def test_validate_all_parameters_with_errors(self):
        """Test validation of all parameters with errors."""
        params = {
            "name": "ab",  # Too short
            "resource_group": "",  # Empty
            "location": "Invalid Region",
            "performance_tier": "InvalidTier",
            "replication_type": "InvalidReplication"
        }
        
        result = self.validator.validate_all_parameters(params)
        assert not result.is_valid
        assert len(result.errors) >= 4  # At least one error per invalid param
    
    def test_validate_parameter_combinations(self):
        """Test cross-parameter validation."""
        # Test Premium + incompatible replication
        params = {
            "name": "teststorage",
            "performance_tier": "Premium",
            "replication_type": "GRS",  # Not compatible with Premium
            "kind": "StorageV2"
        }
        
        result = self.validator.validate_all_parameters(params)
        assert not result.is_valid
        assert any("Premium performance tier only supports" in error for error in result.errors)


class TestCreateStorageValidator:
    """Test cases for create_storage_validator factory function."""
    
    def test_create_storage_validator_success(self):
        """Test successful storage validator creation."""
        validator = create_storage_validator()
        
        assert isinstance(validator, StorageAccountValidator)
        assert validator.valid_performance_tiers == {"Standard", "Premium"}


class TestValidationIntegration:
    """Integration tests for validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = StorageAccountValidator()
    
    def test_complete_storage_account_validation_success(self):
        """Test complete storage account validation workflow."""
        # Valid configuration
        params = {
            "name": "companydata2023",
            "resource_group": "production-resources",
            "location": "East US",
            "performance_tier": "Standard",
            "replication_type": "GRS",
            "access_tier": "Hot",
            "kind": "StorageV2"
        }
        
        result = self.validator.validate_all_parameters(params)
        
        assert result.is_valid
        assert result.message_count > 0  # Should have info messages
    
    def test_complete_storage_account_validation_with_issues(self):
        """Test complete storage account validation with various issues."""
        params = {
            "name": "Test-Storage!",  # Invalid characters
            "resource_group": "rg.",  # Ends with period
            "location": "Mars",  # Invalid region
            "performance_tier": "Super",  # Invalid tier
            "replication_type": "INVALID",  # Invalid replication
            "access_tier": "Frozen"  # Invalid access tier
        }
        
        result = self.validator.validate_all_parameters(params)
        
        assert not result.is_valid
        assert len(result.errors) >= 5  # Should have multiple errors
        assert result.message_count > len(result.errors)  # Should have warnings/info too
    
    def test_real_world_scenario_validation(self):
        """Test validation with realistic scenarios."""
        scenarios = [
            {
                "name": "Production storage account",
                "params": {
                    "name": "proddata2023",
                    "resource_group": "prod-resources",
                    "location": "East US",
                    "performance_tier": "Premium",
                    "replication_type": "ZRS",
                    "kind": "FileStorage"
                },
                "should_be_valid": True
            },
            {
                "name": "Development storage with issues",
                "params": {
                    "name": "dev",  # Too short
                    "resource_group": "dev-rg",
                    "location": "West US",
                    "performance_tier": "Standard",
                    "replication_type": "LRS"
                },
                "should_be_valid": True,  # Valid but with warnings
                "should_have_warnings": True
            },
            {
                "name": "Invalid configuration",
                "params": {
                    "name": "",  # Empty
                    "resource_group": "a" * 100,  # Too long
                    "performance_tier": "Premium",
                    "replication_type": "GRS"  # Incompatible with Premium
                },
                "should_be_valid": False
            }
        ]
        
        for scenario in scenarios:
            result = self.validator.validate_all_parameters(scenario["params"])
            
            if scenario["should_be_valid"]:
                assert result.is_valid, f"Scenario '{scenario['name']}' should be valid: {result.errors}"
            else:
                assert not result.is_valid, f"Scenario '{scenario['name']}' should be invalid"
            
            if scenario.get("should_have_warnings"):
                assert result.has_warnings, f"Scenario '{scenario['name']}' should have warnings"