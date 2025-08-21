"""
Unit tests for templates.generator module.

Tests for template generation including TemplateGenerator, DefaultTemplateGenerator,
and various template generation scenarios.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.templates.generator import (
    TemplateGenerator,
    DefaultTemplateGenerator,
    TemplateMetadata,
    GeneratedTemplate
)


class TestTemplateMetadata:
    """Test cases for TemplateMetadata model."""
    
    def test_template_metadata_creation_success(self):
        """Test successful TemplateMetadata creation."""
        now = datetime.utcnow()
        metadata = TemplateMetadata(
            template_name="storage_account",
            resource_type="Microsoft.Storage/storageAccounts",
            generated_at=now,
            generator_version="1.0.0",
            parameters={"name": "test", "location": "East US"},
            resource_count=1
        )
        
        assert metadata.template_name == "storage_account"
        assert metadata.resource_type == "Microsoft.Storage/storageAccounts"
        assert metadata.generated_at == now
        assert metadata.generator_version == "1.0.0"
        assert metadata.parameters == {"name": "test", "location": "East US"}
        assert metadata.resource_count == 1
    
    def test_template_metadata_defaults(self):
        """Test TemplateMetadata with default values."""
        now = datetime.utcnow()
        metadata = TemplateMetadata(
            template_name="web_app",
            resource_type="Microsoft.Web/sites",
            generated_at=now,
            parameters={}
        )
        
        assert metadata.generator_version == "1.0.0"
        assert metadata.resource_count == 1


class TestGeneratedTemplate:
    """Test cases for GeneratedTemplate model."""
    
    def test_generated_template_creation_success(self):
        """Test successful GeneratedTemplate creation."""
        now = datetime.utcnow()
        metadata = TemplateMetadata(
            template_name="test_template",
            resource_type="Microsoft.Storage/storageAccounts",
            generated_at=now,
            parameters={}
        )
        
        content = {"$schema": "test-schema", "resources": []}
        raw_json = json.dumps(content, indent=2)
        
        template = GeneratedTemplate(
            metadata=metadata,
            content=content,
            raw_json=raw_json
        )
        
        assert template.metadata == metadata
        assert template.content == content
        assert template.raw_json == raw_json


class TestTemplateGenerator:
    """Test cases for TemplateGenerator class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates"
        self.templates_dir.mkdir()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.templates.generator.get_settings')
    def test_template_generator_initialization_success(self, mock_get_settings):
        """Test successful TemplateGenerator initialization."""
        mock_settings = Mock()
        mock_settings.get_templates_dir.return_value = self.templates_dir
        mock_get_settings.return_value = mock_settings
        
        generator = TemplateGenerator()
        
        assert generator.templates_dir == self.templates_dir
        assert generator.env is not None
    
    def test_template_generator_initialization_custom_dir(self):
        """Test TemplateGenerator initialization with custom directory."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        assert generator.templates_dir == self.templates_dir
    
    def test_list_available_templates_success(self):
        """Test listing available template files."""
        # Create test template files
        (self.templates_dir / "storage_account.json.j2").write_text("test template")
        (self.templates_dir / "web_app.json.j2").write_text("test template")
        (self.templates_dir / "not_template.txt").write_text("not a template")
        
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        templates = generator.list_available_templates()
        
        assert "storage_account" in templates
        assert "web_app" in templates
        assert "not_template" not in templates
        assert len(templates) == 2
    
    def test_list_available_templates_empty_directory(self):
        """Test listing templates in empty directory."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        templates = generator.list_available_templates()
        
        assert templates == []
    
    def test_generate_arm_template_success(self):
        """Test successful ARM template generation."""
        # Create a test template file
        template_content = '''
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "resources": [
        {
            "type": "Microsoft.Storage/storageAccounts",
            "name": "{{ name }}",
            "location": "{{ location }}"
        }
    ]
}
'''
        template_file = self.templates_dir / "storage_account.json.j2"
        template_file.write_text(template_content.strip())
        
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        parameters = {
            "name": "teststorage",
            "location": "East US"
        }
        
        result = generator.generate_arm_template(
            template_name="storage_account",
            parameters=parameters,
            resource_type="Microsoft.Storage/storageAccounts"
        )
        
        assert isinstance(result, GeneratedTemplate)
        assert result.metadata.template_name == "storage_account"
        assert result.metadata.resource_type == "Microsoft.Storage/storageAccounts"
        assert result.metadata.resource_count == 1
        
        # Check generated content
        assert result.content["$schema"] == "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
        assert result.content["resources"][0]["name"] == "teststorage"
        assert result.content["resources"][0]["location"] == "East US"
    
    def test_generate_arm_template_template_not_found(self):
        """Test ARM template generation with non-existent template."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        with pytest.raises(Exception) as exc_info:
            generator.generate_arm_template(
                template_name="nonexistent",
                parameters={}
            )
        
        assert "Template not found" in str(exc_info.value) or "TemplateNotFound" in str(exc_info.value)
    
    def test_generate_arm_template_invalid_json(self):
        """Test ARM template generation with invalid JSON template."""
        # Create template with invalid JSON
        template_content = '''
{
    "$schema": "test-schema",
    "resources": [
        {
            "name": "{{ name }}"
            // Missing comma - invalid JSON
            "location": "{{ location }}"
        }
    ]
}
'''
        template_file = self.templates_dir / "invalid.json.j2"
        template_file.write_text(template_content.strip())
        
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        with pytest.raises(Exception) as exc_info:
            generator.generate_arm_template(
                template_name="invalid",
                parameters={"name": "test", "location": "East US"}
            )
        
        assert "invalid JSON" in str(exc_info.value)
    
    def test_save_template_success(self):
        """Test successful template saving."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        # Create a test template
        metadata = TemplateMetadata(
            template_name="test_template",
            resource_type="Microsoft.Storage/storageAccounts",
            generated_at=datetime.utcnow(),
            parameters={}
        )
        
        content = {"$schema": "test-schema", "resources": []}
        raw_json = json.dumps(content, indent=2)
        
        generated_template = GeneratedTemplate(
            metadata=metadata,
            content=content,
            raw_json=raw_json
        )
        
        # Save to custom location
        output_file = Path(self.temp_dir) / "output.json"
        saved_path = generator.save_template(generated_template, output_file)
        
        assert saved_path == output_file
        assert output_file.exists()
        
        # Verify content
        saved_content = json.loads(output_file.read_text())
        assert saved_content == content
    
    @patch('src.templates.generator.get_settings')
    def test_save_template_auto_generate_filename(self, mock_get_settings):
        """Test template saving with auto-generated filename."""
        output_dir = Path(self.temp_dir) / "output"
        output_dir.mkdir()
        
        mock_settings = Mock()
        mock_settings.get_output_dir.return_value = output_dir
        mock_get_settings.return_value = mock_settings
        
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        # Create a test template
        metadata = TemplateMetadata(
            template_name="storage_account",
            resource_type="Microsoft.Storage/storageAccounts",
            generated_at=datetime.utcnow(),
            parameters={}
        )
        
        content = {"$schema": "test-schema", "resources": []}
        generated_template = GeneratedTemplate(
            metadata=metadata,
            content=content,
            raw_json=json.dumps(content, indent=2)
        )
        
        saved_path = generator.save_template(generated_template)
        
        assert saved_path.parent == output_dir
        assert saved_path.name.startswith("storage_account_")
        assert saved_path.suffix == ".json"
        assert saved_path.exists()
    
    def test_validate_template_success(self):
        """Test successful template validation."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template_content = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {
                    "type": "Microsoft.Storage/storageAccounts",
                    "apiVersion": "2021-04-01",
                    "name": "teststorage"
                }
            ]
        }
        
        errors = generator.validate_template(template_content)
        
        assert errors == []
    
    def test_validate_template_missing_required_properties(self):
        """Test template validation with missing required properties."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template_content = {
            "contentVersion": "1.0.0.0"
            # Missing $schema and resources
        }
        
        errors = generator.validate_template(template_content)
        
        assert len(errors) >= 2
        assert any("Missing required property: $schema" in error for error in errors)
        assert any("Missing required property: resources" in error for error in errors)
    
    def test_validate_template_invalid_schema(self):
        """Test template validation with invalid schema."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template_content = {
            "$schema": "invalid-schema",
            "contentVersion": "1.0.0.0",
            "resources": []
        }
        
        errors = generator.validate_template(template_content)
        
        assert any("Invalid ARM template schema URL" in error for error in errors)
    
    def test_validate_template_invalid_resources(self):
        """Test template validation with invalid resources."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template_content = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {
                    "name": "test-resource"
                    # Missing type and apiVersion
                }
            ]
        }
        
        errors = generator.validate_template(template_content)
        
        assert any("missing required property: type" in error for error in errors)
        assert any("missing required property: apiVersion" in error for error in errors)
    
    def test_create_basic_arm_template_success(self):
        """Test creation of basic ARM template structure."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template = generator.create_basic_arm_template()
        
        assert template["$schema"] == "https://schema.management.azure.com/schemas/2021-04-01/deploymentTemplate.json#"
        assert template["contentVersion"] == "1.0.0.0"
        assert template["parameters"] == {}
        assert template["variables"] == {}
        assert template["resources"] == []
        assert template["outputs"] == {}
    
    def test_create_basic_arm_template_custom_versions(self):
        """Test creation of basic ARM template with custom versions."""
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        template = generator.create_basic_arm_template(
            schema_version="2019-04-01",
            content_version="2.0.0.0"
        )
        
        assert "2019-04-01" in template["$schema"]
        assert template["contentVersion"] == "2.0.0.0"
    
    def test_custom_filters_success(self):
        """Test custom Jinja2 filters work correctly."""
        # Create template using filters
        template_content = '''
{
    "test_json": {{ data | to_json }},
    "camel_case": "{{ snake_case_var | camel_case }}",
    "pascal_case": "{{ snake_case_var | pascal_case }}",
    "resource_name": "{{ resource_type | resource_name(name) }}"
}
'''
        template_file = self.templates_dir / "filter_test.json.j2"
        template_file.write_text(template_content.strip())
        
        generator = TemplateGenerator(templates_dir=self.templates_dir)
        
        parameters = {
            "data": {"key": "value"},
            "snake_case_var": "test_variable",
            "resource_type": "Microsoft.Storage/storageAccounts",
            "name": "mystorage"
        }
        
        result = generator.generate_arm_template("filter_test", parameters)
        
        # Check filter results
        content = result.content
        assert content["test_json"] == {"key": "value"}
        assert content["camel_case"] == "testVariable"
        assert content["pascal_case"] == "TestVariable"
        assert content["resource_name"] == "storageAccounts-mystorage"


class TestDefaultTemplateGenerator:
    """Test cases for DefaultTemplateGenerator class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_default_template_generator_initialization(self):
        """Test DefaultTemplateGenerator initialization."""
        generator = DefaultTemplateGenerator()
        
        assert generator.generator is not None
        assert isinstance(generator.generator, TemplateGenerator)
    
    def test_generate_storage_account_template_success(self):
        """Test successful storage account template generation."""
        generator = DefaultTemplateGenerator()
        
        result = generator.generate_storage_account_template(
            name="teststorage",
            location="East US",
            resource_group="test-rg",
            sku_name="Standard_GRS",
            kind="BlobStorage",
            access_tier="Cool"
        )
        
        assert isinstance(result, GeneratedTemplate)
        assert result.metadata.template_name == "storage_account"
        assert result.metadata.resource_type == "Microsoft.Storage/storageAccounts"
        
        # Check template content
        content = result.content
        assert content["$schema"] == "https://schema.management.azure.com/schemas/2021-04-01/deploymentTemplate.json#"
        assert content["contentVersion"] == "1.0.0.0"
        
        # Check parameters
        assert "storageAccountName" in content["parameters"]
        assert "location" in content["parameters"]
        assert content["parameters"]["storageAccountName"]["defaultValue"] == "teststorage"
        assert content["parameters"]["location"]["defaultValue"] == "East US"
        
        # Check resources
        assert len(content["resources"]) == 1
        resource = content["resources"][0]
        assert resource["type"] == "Microsoft.Storage/storageAccounts"
        assert resource["apiVersion"] == "2021-04-01"
        assert resource["sku"]["name"] == "Standard_GRS"
        assert resource["kind"] == "BlobStorage"
        assert resource["properties"]["accessTier"] == "Cool"
        assert resource["properties"]["supportsHttpsTrafficOnly"] is True
        assert resource["properties"]["minimumTlsVersion"] == "TLS1_2"
        
        # Check outputs
        assert "storageAccountName" in content["outputs"]
        assert "storageAccountId" in content["outputs"]
    
    def test_generate_storage_account_template_defaults(self):
        """Test storage account template generation with default values."""
        generator = DefaultTemplateGenerator()
        
        result = generator.generate_storage_account_template(
            name="teststorage",
            location="East US",
            resource_group="test-rg"
        )
        
        # Check default values were used
        resource = result.content["resources"][0]
        assert resource["sku"]["name"] == "Standard_LRS"
        assert resource["kind"] == "StorageV2"
        assert resource["properties"]["accessTier"] == "Hot"
    
    def test_generate_storage_account_template_metadata(self):
        """Test storage account template metadata."""
        generator = DefaultTemplateGenerator()
        
        result = generator.generate_storage_account_template(
            name="teststorage",
            location="East US",
            resource_group="test-rg",
            sku_name="Premium_LRS"
        )
        
        metadata = result.metadata
        assert metadata.template_name == "storage_account"
        assert metadata.resource_type == "Microsoft.Storage/storageAccounts"
        assert metadata.parameters["name"] == "teststorage"
        assert metadata.parameters["location"] == "East US"
        assert metadata.parameters["resource_group"] == "test-rg"
        assert metadata.parameters["sku_name"] == "Premium_LRS"


class TestTemplateGeneratorIntegration:
    """Integration tests for template generation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates"
        self.templates_dir.mkdir()
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.templates.generator.get_settings')
    def test_complete_template_workflow(self, mock_get_settings):
        """Test complete template generation workflow."""
        mock_settings = Mock()
        mock_settings.get_templates_dir.return_value = self.templates_dir
        mock_settings.get_output_dir.return_value = self.output_dir
        mock_get_settings.return_value = mock_settings
        
        # Create a template file
        template_content = '''
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "resourceName": {
            "type": "string",
            "defaultValue": "{{ name }}"
        }
    },
    "resources": [
        {
            "type": "{{ resource_type }}",
            "apiVersion": "2021-04-01",
            "name": "[parameters('resourceName')]",
            "location": "{{ location }}",
            "properties": {{ properties | to_json }}
        }
    ]
}
'''
        template_file = self.templates_dir / "test_resource.json.j2"
        template_file.write_text(template_content.strip())
        
        # Generate template
        generator = TemplateGenerator()
        
        parameters = {
            "name": "myresource",
            "resource_type": "Microsoft.Storage/storageAccounts",
            "location": "West US",
            "properties": {
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2"
            }
        }
        
        result = generator.generate_arm_template("test_resource", parameters)
        
        # Validate generated template
        errors = generator.validate_template(result.content)
        assert errors == []
        
        # Save template
        saved_path = generator.save_template(result)
        assert saved_path.exists()
        
        # Verify saved content
        saved_content = json.loads(saved_path.read_text())
        assert saved_content == result.content