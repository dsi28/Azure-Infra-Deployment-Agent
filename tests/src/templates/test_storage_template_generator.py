"""
Unit tests for templates.storage_template_generator module.

Tests for StorageAccountTemplateGenerator functionality including template
generation, validation, parameter substitution, and preview functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from src.templates.storage_template_generator import (
    StorageAccountTemplateGenerator,
    create_storage_template_generator
)
from src.templates.generator import GeneratedTemplate, TemplateMetadata
from src.resources.storage_config import StorageAccountConfiguration


class TestStorageAccountTemplateGenerator:
    """Test cases for StorageAccountTemplateGenerator class."""
    
    def setup_method(self):
        """Set up test environment."""
        with patch('src.templates.storage_template_generator.TemplateGenerator'):
            self.generator = StorageAccountTemplateGenerator()
    
    def test_storage_template_generator_initialization(self):
        """Test StorageAccountTemplateGenerator initialization."""
        with patch('src.templates.storage_template_generator.TemplateGenerator') as mock_generator:
            generator = StorageAccountTemplateGenerator()
            
            mock_generator.assert_called_once_with(None)
            assert hasattr(generator, 'generator')
    
    def test_generate_template_success(self):
        """Test successful template generation."""
        # Create complete configuration
        config = StorageAccountConfiguration(
            name="teststorage123",
            resource_group="test-rg",
            location="East US",
            performance_tier="Standard",
            replication_type="LRS"
        )
        
        # Mock the underlying generator
        mock_template = GeneratedTemplate(
            metadata=TemplateMetadata(
                template_name="storage_account",
                resource_type="Microsoft.Storage/storageAccounts",
                generated_at=datetime.utcnow(),
                parameters={}
            ),
            content={"resources": [{"type": "Microsoft.Storage/storageAccounts"}]},
            raw_json='{"resources": []}'
        )
        
        self.generator.generator.generate_arm_template = Mock(return_value=mock_template)
        
        result = self.generator.generate_template(config)
        
        assert result == mock_template
        self.generator.generator.generate_arm_template.assert_called_once()
    
    def test_generate_template_incomplete_config_failure(self):
        """Test template generation with incomplete configuration."""
        # Create incomplete configuration
        config = StorageAccountConfiguration(name="test")  # Missing required fields
        
        with pytest.raises(ValueError) as exc_info:
            self.generator.generate_template(config)
        
        assert "missing required parameters" in str(exc_info.value)
        assert "resource_group" in str(exc_info.value)
        assert "location" in str(exc_info.value)
    
    def test_prepare_template_parameters_success(self):
        """Test template parameter preparation."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US",
            performance_tier="Premium",
            replication_type="ZRS",
            access_tier="Cool",
            kind="FileStorage",
            tags={"env": "test"}
        )
        
        params = self.generator._prepare_template_parameters(config)
        
        assert params["storageAccountName"] == "teststorage"
        assert params["location"] == "East US"
        assert params["performanceTier"] == "Premium"
        assert params["replicationType"] == "ZRS"
        assert params["accessTier"] == "Cool"
        assert params["storageAccountKind"] == "FileStorage"
        assert params["skuName"] == "Premium_ZRS"
        assert params["tags"] == {"env": "test"}
        assert params["config"] == config
    
    def test_generate_parameters_file_success(self):
        """Test ARM parameters file generation."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="West US",
            performance_tier="Standard",
            replication_type="GRS",
            tags={"project": "test", "env": "dev"}
        )
        
        params_file = self.generator.generate_parameters_file(config)
        
        assert params_file["$schema"].endswith("deploymentParameters.json#")
        assert params_file["contentVersion"] == "1.0.0.0"
        
        params = params_file["parameters"]
        assert params["storageAccountName"]["value"] == "teststorage"
        assert params["location"]["value"] == "West US"
        assert params["performanceTier"]["value"] == "Standard"
        assert params["replicationType"]["value"] == "GRS"
        assert params["tags"]["value"] == {"project": "test", "env": "dev"}
    
    def test_generate_parameters_file_no_tags(self):
        """Test ARM parameters file generation without tags."""
        config = StorageAccountConfiguration(
            name="teststorage",
            resource_group="test-rg",
            location="East US"
        )
        
        params_file = self.generator.generate_parameters_file(config)
        
        assert "tags" not in params_file["parameters"]
    
    def test_preview_template_success(self):
        """Test template preview generation."""
        config = StorageAccountConfiguration(
            name="previewstorage",
            resource_group="preview-rg",
            location="North Europe",
            tags={"env": "preview"}
        )
        
        # Mock generated template
        mock_template = GeneratedTemplate(
            metadata=TemplateMetadata(
                template_name="storage_account",
                resource_type="Microsoft.Storage/storageAccounts",
                generated_at=datetime(2024, 1, 1, 12, 0, 0),
                parameters={}
            ),
            content={"resources": [{}]},
            raw_json='{"test": "template"}'
        )
        
        self.generator.generate_template = Mock(return_value=mock_template)
        
        preview = self.generator.preview_template(config)
        
        assert "ARM TEMPLATE PREVIEW" in preview
        assert "previewstorage" in preview
        assert "preview-rg" in preview
        assert "North Europe" in preview
        assert "env: preview" in preview
        assert '{"test": "template"}' in preview
    
    
    @patch('builtins.open', new_callable=Mock)
    @patch('pathlib.Path.mkdir')
    def test_save_template_files_success(self, mock_mkdir, mock_open):
        """Test saving template and parameters files."""
        config = StorageAccountConfiguration(
            name="savestorage",
            resource_group="save-rg",
            location="West US"
        )
        
        # Mock generated template
        mock_template = GeneratedTemplate(
            metadata=TemplateMetadata(
                template_name="storage_account",
                resource_type="Microsoft.Storage/storageAccounts",
                generated_at=datetime.utcnow(),
                parameters={}
            ),
            content={"resources": []},
            raw_json='{"test": "template"}'
        )
        
        self.generator.generate_template = Mock(return_value=mock_template)
        self.generator.generate_parameters_file = Mock(return_value={"parameters": {}})
        
        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            
            result = self.generator.save_template_files(config)
        
        assert "template" in result
        assert "parameters" in result
        assert mock_open.call_count == 2  # Template and parameters files
        mock_mkdir.assert_called_once()
    
    def test_save_template_files_custom_output_dir(self):
        """Test saving template files to custom directory."""
        config = StorageAccountConfiguration(
            name="customstorage",
            resource_group="custom-rg",
            location="East US"
        )
        
        custom_dir = Path("/custom/output")
        
        # Mock template generation
        self.generator.generate_template = Mock()
        self.generator.generate_parameters_file = Mock(return_value={})
        
        with patch('builtins.open'), patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
                
                result = self.generator.save_template_files(config, custom_dir)
        
        # Verify custom directory was used
        assert str(custom_dir) in str(result["template"])
        assert str(custom_dir) in str(result["parameters"])


class TestCreateStorageTemplateGenerator:
    """Test cases for create_storage_template_generator factory function."""
    
    def test_create_storage_template_generator_success(self):
        """Test successful storage template generator creation."""
        with patch('src.templates.storage_template_generator.StorageAccountTemplateGenerator') as mock_generator:
            result = create_storage_template_generator()
            
            mock_generator.assert_called_once_with(None)
    
    def test_create_storage_template_generator_with_custom_dir(self):
        """Test generator creation with custom templates directory."""
        custom_dir = Path("/custom/templates")
        
        with patch('src.templates.storage_template_generator.StorageAccountTemplateGenerator') as mock_generator:
            result = create_storage_template_generator(custom_dir)
            
            mock_generator.assert_called_once_with(custom_dir)


class TestStorageTemplateGeneratorIntegration:
    """Integration tests for storage template generator functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Use real generator but mock file system operations
        self.generator = StorageAccountTemplateGenerator()
    
    @patch('src.templates.generator.FileSystemLoader')
    @patch('src.templates.generator.Environment')
    def test_end_to_end_template_generation_workflow(self, mock_env, mock_loader):
        """Test complete template generation workflow."""
        # Mock Jinja2 environment and template
        mock_template = Mock()
        mock_template.render.return_value = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [{
                "type": "Microsoft.Storage/storageAccounts",
                "apiVersion": "2023-01-01",
                "name": "[parameters('storageAccountName')]",
                "sku": {"name": "[variables('storageAccountType')]"},
                "kind": "[parameters('storageAccountKind')]"
            }]
        })
        
        mock_env_instance = Mock()
        mock_env_instance.get_template.return_value = mock_template
        mock_env.return_value = mock_env_instance
        
        # Create configuration
        config = StorageAccountConfiguration(
            name="integrationtest",
            resource_group="integration-rg", 
            location="Central US",
            performance_tier="Standard",
            replication_type="LRS",
            tags={"test": "integration"}
        )
        
        # Generate template
        result = self.generator.generate_template(config)
        
        assert result.metadata.template_name == "storage_account"
        assert result.metadata.resource_type == "Microsoft.Storage/storageAccounts"
        assert len(result.content["resources"]) == 1
        assert result.content["resources"][0]["type"] == "Microsoft.Storage/storageAccounts"
    
    def test_real_world_configuration_scenarios(self):
        """Test template generation with realistic configuration scenarios."""
        scenarios = [
            {
                "name": "Basic production storage",
                "config": StorageAccountConfiguration(
                    name="proddata2024",
                    resource_group="production-resources",
                    location="East US",
                    performance_tier="Standard",
                    replication_type="GRS",
                    access_tier="Hot"
                ),
                "should_succeed": True
            },
            {
                "name": "Premium file storage", 
                "config": StorageAccountConfiguration(
                    name="premiumfiles",
                    resource_group="premium-rg",
                    location="West US",
                    performance_tier="Premium",
                    replication_type="ZRS",
                    kind="FileStorage"
                ),
                "should_succeed": True
            },
            {
                "name": "Development storage with tags",
                "config": StorageAccountConfiguration(
                    name="devstorage2024",
                    resource_group="dev-resources",
                    location="North Europe",
                    tags={
                        "environment": "development",
                        "project": "webapp",
                        "owner": "dev-team"
                    }
                ),
                "should_succeed": True
            }
        ]
        
        for scenario in scenarios:
            config = scenario["config"]
            
            # Mock the underlying template generation
            with patch.object(self.generator.generator, 'generate_arm_template') as mock_gen:
                mock_template = GeneratedTemplate(
                    metadata=TemplateMetadata(
                        template_name="storage_account",
                        resource_type="Microsoft.Storage/storageAccounts", 
                        generated_at=datetime.utcnow(),
                        parameters={}
                    ),
                    content={"resources": [{"type": "Microsoft.Storage/storageAccounts"}]},
                    raw_json='{"resources": []}'
                )
                mock_gen.return_value = mock_template
                
                if scenario["should_succeed"]:
                    result = self.generator.generate_template(config)
                    assert result is not None
                    assert result.metadata.template_name == "storage_account"
                    
                    # Test parameters file generation
                    params = self.generator.generate_parameters_file(config)
                    assert params["parameters"]["storageAccountName"]["value"] == config.name
                    
                    # Test preview generation
                    preview = self.generator.preview_template(config)
                    assert config.name in preview
                    assert config.location in preview