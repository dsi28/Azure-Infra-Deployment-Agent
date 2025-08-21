"""
Unit tests for storage template validation functionality.

Tests for template validation, storage-specific property validation,
and error handling scenarios for the storage template generator.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.templates.storage_template_generator import StorageAccountTemplateGenerator
from src.templates.generator import GeneratedTemplate, TemplateMetadata
from src.resources.storage_config import StorageAccountConfiguration


class TestStorageTemplateValidation:
    """Test cases for storage template validation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        with patch('src.templates.storage_template_generator.TemplateGenerator'):
            self.generator = StorageAccountTemplateGenerator()
    
    def test_validate_generated_template_success(self):
        """Test template validation with valid template."""
        config = StorageAccountConfiguration(
            name="validstorage",
            resource_group="valid-rg",
            location="East US"
        )
        
        # Mock valid template
        mock_template = GeneratedTemplate(
            metadata=TemplateMetadata(
                template_name="storage_account",
                resource_type="Microsoft.Storage/storageAccounts",
                generated_at=datetime.utcnow(),
                parameters={}
            ),
            content={
                "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
                "contentVersion": "1.0.0.0",
                "resources": [{
                    "type": "Microsoft.Storage/storageAccounts",
                    "apiVersion": "2023-01-01",
                    "name": "test",
                    "sku": {"name": "Standard_LRS"},
                    "kind": "StorageV2",
                    "properties": {
                        "supportsHttpsTrafficOnly": True,
                        "minimumTlsVersion": "TLS1_2",
                        "allowBlobPublicAccess": False,
                        "encryption": {"keySource": "Microsoft.Storage"}
                    }
                }]
            },
            raw_json="{}"
        )
        
        self.generator.generate_template = Mock(return_value=mock_template)
        self.generator.generator.validate_template = Mock(return_value=[])
        
        result = self.generator.validate_generated_template(config)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert "ARM template structure is valid" in result["info"]
    
    def test_validate_generated_template_with_errors(self):
        """Test template validation with errors."""
        config = StorageAccountConfiguration(
            name="invalidstorage",
            resource_group="invalid-rg",
            location="East US"
        )
        
        # Mock template with errors
        self.generator.generator.validate_template = Mock(return_value=["Missing $schema"])
        mock_template = GeneratedTemplate(
            metadata=TemplateMetadata(
                template_name="storage_account",
                resource_type="Microsoft.Storage/storageAccounts",
                generated_at=datetime.utcnow(),
                parameters={}
            ),
            content={"resources": []},  # No storage account resources
            raw_json="{}"
        )
        
        self.generator.generate_template = Mock(return_value=mock_template)
        
        result = self.generator.validate_generated_template(config)
        
        assert result["is_valid"] is False
        assert "Missing $schema" in result["errors"]
        assert "No storage account resource found" in result["errors"]
    
    def test_validate_generated_template_generation_failure(self):
        """Test template validation when generation fails."""
        config = StorageAccountConfiguration(
            name="failurestorage",
            resource_group="failure-rg",
            location="East US"
        )
        
        self.generator.generate_template = Mock(side_effect=Exception("Template generation failed"))
        
        result = self.generator.validate_generated_template(config)
        
        assert result["is_valid"] is False
        assert "Template generation failed: Template generation failed" in result["errors"]
    
    def test_validate_storage_specific_properties_success(self):
        """Test storage-specific property validation."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
                "properties": {
                    "supportsHttpsTrafficOnly": True,
                    "minimumTlsVersion": "TLS1_2",
                    "allowBlobPublicAccess": False,
                    "encryption": {"keySource": "Microsoft.Storage"}
                }
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert len(validation_result["errors"]) == 0
        assert "Storage account resource structure validated" in validation_result["info"]
    
    def test_validate_storage_specific_properties_warnings(self):
        """Test storage-specific validation with warnings."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2", 
                "properties": {
                    "supportsHttpsTrafficOnly": False,  # Should warn
                    "allowBlobPublicAccess": True,      # Should warn
                    "minimumTlsVersion": "TLS1_1"       # Should warn
                }
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert len(validation_result["errors"]) == 0
        assert "HTTPS-only traffic is not enforced" in validation_result["warnings"]
        assert "Public blob access is enabled" in validation_result["warnings"] 
        assert "Consider using TLS 1.2" in validation_result["warnings"]
    
    def test_validate_storage_specific_properties_encryption_warning(self):
        """Test validation warning for missing encryption configuration."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
                "properties": {
                    "supportsHttpsTrafficOnly": True,
                    "minimumTlsVersion": "TLS1_2",
                    "allowBlobPublicAccess": False
                    # Missing encryption
                }
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "Encryption configuration not explicitly defined" in validation_result["warnings"]
    
    def test_validate_storage_specific_properties_errors(self):
        """Test storage-specific validation with errors."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                # Missing sku and kind
                "properties": {}
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "Storage account missing SKU configuration" in validation_result["errors"]
        assert "Storage account missing kind specification" in validation_result["errors"]
    
    def test_validate_storage_specific_properties_no_storage_resource(self):
        """Test validation when no storage account resource found."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Compute/virtualMachines",  # Wrong resource type
                "name": "test-vm"
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "No storage account resource found in template" in validation_result["errors"]
    
    def test_validate_storage_specific_properties_multiple_storage_resources(self):
        """Test validation with multiple storage account resources."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [
                {
                    "type": "Microsoft.Storage/storageAccounts",
                    "name": "storage1",
                    "sku": {"name": "Standard_LRS"},
                    "kind": "StorageV2",
                    "properties": {}
                },
                {
                    "type": "Microsoft.Storage/storageAccounts",
                    "name": "storage2",
                    "sku": {"name": "Standard_GRS"},
                    "kind": "StorageV2",
                    "properties": {}
                }
            ]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "Multiple storage account resources found" in validation_result["warnings"]
    
    def test_validate_storage_specific_properties_empty_resources(self):
        """Test validation with empty resources array."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {"resources": []}
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "No storage account resource found in template" in validation_result["errors"]
    
    def test_validate_storage_specific_properties_no_resources_key(self):
        """Test validation when resources key is missing."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {"parameters": {}, "variables": {}}  # No resources key
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert "No storage account resource found in template" in validation_result["errors"]


class TestStorageTemplateValidationEdgeCases:
    """Test edge cases and error scenarios in storage template validation."""
    
    def setup_method(self):
        """Set up test environment."""
        with patch('src.templates.storage_template_generator.TemplateGenerator'):
            self.generator = StorageAccountTemplateGenerator()
    
    def test_validation_with_complex_storage_properties(self):
        """Test validation with complex storage account properties."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "sku": {"name": "Premium_ZRS"},
                "kind": "FileStorage",
                "properties": {
                    "supportsHttpsTrafficOnly": True,
                    "minimumTlsVersion": "TLS1_2",
                    "allowBlobPublicAccess": False,
                    "isHnsEnabled": True,
                    "networkAcls": {
                        "defaultAction": "Deny",
                        "ipRules": [],
                        "virtualNetworkRules": []
                    },
                    "encryption": {
                        "services": {
                            "file": {"enabled": True},
                            "blob": {"enabled": True}
                        },
                        "keySource": "Microsoft.Storage"
                    }
                }
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        assert len(validation_result["errors"]) == 0
        assert "Storage account resource structure validated" in validation_result["info"]
    
    def test_validation_with_minimal_storage_properties(self):
        """Test validation with minimal storage account properties."""
        validation_result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        template_content = {
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
                "properties": {}  # Empty properties
            }]
        }
        
        self.generator._validate_storage_specific_properties(template_content, validation_result)
        
        # Should generate warnings for missing security configurations
        assert "HTTPS-only traffic is not enforced" in validation_result["warnings"]
        assert "Consider using TLS 1.2" in validation_result["warnings"]
        assert "Encryption configuration not explicitly defined" in validation_result["warnings"]
    
    def test_validation_result_structure_integrity(self):
        """Test that validation result structure is maintained properly."""
        config = StorageAccountConfiguration(
            name="structuretest",
            resource_group="test-rg",
            location="East US"
        )
        
        # Mock template generation to raise an exception
        self.generator.generate_template = Mock(side_effect=ValueError("Test error"))
        
        result = self.generator.validate_generated_template(config)
        
        # Verify all expected keys are present
        assert "is_valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "info" in result
        
        # Verify types
        assert isinstance(result["is_valid"], bool)
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["info"], list)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0