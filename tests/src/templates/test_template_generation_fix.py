"""
Test for Template Generation Fix (Task 3.4).

This test verifies that the storage_account.json.j2 template file
can be located and processed correctly without "TemplateNotFound" errors.
"""

import json
import pytest
from unittest.mock import Mock
from pathlib import Path

from src.templates.storage_template_generator import StorageAccountTemplateGenerator
from src.resources.storage_config import StorageAccountConfiguration


class TestTemplateGenerationFix:
    """Test that Task 3.4 template generation issues are resolved."""
    
    def test_storage_template_file_exists_in_templates_directory(self):
        """Test that storage_account.json.j2 exists in the templates directory."""
        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent
        template_file = project_root / "templates" / "storage_account.json.j2"
        
        assert template_file.exists(), f"Template file should exist at {template_file}"
        
        # Verify it's a valid Jinja2 template with expected content
        content = template_file.read_text()
        assert "$schema" in content
        assert "Microsoft.Storage/storageAccounts" in content
        assert "{{ generation_timestamp }}" in content
    
    def test_template_generator_can_locate_template_file(self):
        """Test that TemplateGenerator can locate storage_account.json.j2."""
        # Create generator with default settings (should use root templates/ directory)
        generator = StorageAccountTemplateGenerator()
        
        # Verify it can list available templates
        available_templates = generator.generator.list_available_templates()
        assert "storage_account" in available_templates, "storage_account template should be available"
    
    def test_template_generation_without_template_not_found_error(self):
        """Test that template generation completes without TemplateNotFound errors."""
        # Create a complete storage account configuration
        config = StorageAccountConfiguration()
        config.name = "testsa001"
        config.resource_group = "test-rg"
        config.location = "East US"
        config.performance_tier = "Standard"
        config.replication_type = "LRS"
        config.access_tier = "Hot"
        config.kind = "StorageV2"
        config.enable_https_only = True
        config.enable_hierarchical_namespace = False
        config.tags = {"Environment": "Test"}
        
        # Generate template - should not raise TemplateNotFound
        generator = StorageAccountTemplateGenerator()
        
        try:
            generated = generator.generate_template(config)
            assert generated is not None, "Template generation should succeed"
            assert generated.metadata.template_name == "storage_account"
            assert generated.metadata.resource_count >= 1
        except Exception as e:
            pytest.fail(f"Template generation should not raise TemplateNotFound: {e}")
    
    def test_generated_template_is_valid_arm_json(self):
        """Test that generated templates produce valid ARM JSON."""
        # Create test configuration
        config = StorageAccountConfiguration()
        config.name = "testsa002"
        config.resource_group = "test-rg"
        config.location = "East US"
        config.performance_tier = "Standard"
        config.replication_type = "LRS"
        config.access_tier = "Hot"
        config.kind = "StorageV2"
        config.enable_https_only = True
        config.enable_hierarchical_namespace = False
        
        generator = StorageAccountTemplateGenerator()
        generated = generator.generate_template(config)
        
        # Parse the JSON to ensure it's valid
        template_json = json.loads(generated.raw_json)
        
        # Verify ARM template structure
        assert "$schema" in template_json
        assert "contentVersion" in template_json
        assert "resources" in template_json
        
        # Verify schema is correct
        schema = template_json["$schema"]
        assert schema.startswith("https://schema.management.azure.com/")
        
        # Verify resources
        resources = template_json["resources"]
        assert len(resources) >= 1
        
        storage_resources = [r for r in resources if r.get("type") == "Microsoft.Storage/storageAccounts"]
        assert len(storage_resources) == 1, "Should have exactly one storage account resource"
        
        storage_resource = storage_resources[0]
        assert "sku" in storage_resource, "Storage account should have SKU"
        assert "kind" in storage_resource, "Storage account should have kind"
    
    def test_template_validation_passes(self):
        """Test that generated templates pass validation."""
        config = StorageAccountConfiguration()
        config.name = "testsa003"
        config.resource_group = "test-rg"
        config.location = "East US"
        config.performance_tier = "Premium"
        config.replication_type = "LRS"
        config.access_tier = "Hot"
        config.kind = "StorageV2"
        config.enable_https_only = True
        config.enable_hierarchical_namespace = False
        config.tags = {"Purpose": "Testing"}
        
        generator = StorageAccountTemplateGenerator()
        
        # Validate the generated template
        validation_result = generator.validate_generated_template(config)
        
        assert validation_result["is_valid"], f"Template validation should pass. Errors: {validation_result['errors']}"
        assert isinstance(validation_result["errors"], list)
        assert isinstance(validation_result["warnings"], list)
        assert isinstance(validation_result["info"], list)
        
        # Should have some info messages
        assert len(validation_result["info"]) > 0, "Should have validation info messages"
    
    def test_task_3_4_acceptance_criteria_met(self):
        """Test that all Task 3.4 acceptance criteria are met."""
        # Acceptance Criteria from TASK.md:
        # - Template generation completes without "TemplateNotFound" errors
        # - Generated ARM templates pass validation  
        # - Templates contain proper parameter substitution from storage account configuration
        
        config = StorageAccountConfiguration()
        config.name = "acceptancetest001"
        config.resource_group = "acceptance-test-rg"
        config.location = "West US"
        config.performance_tier = "Standard"
        config.replication_type = "GRS"
        config.access_tier = "Cool"
        config.kind = "StorageV2"
        config.enable_https_only = True
        config.enable_hierarchical_namespace = True
        config.tags = {"TestType": "Acceptance", "Task": "3.4"}
        
        generator = StorageAccountTemplateGenerator()
        
        # Criterion 1: Template generation completes without "TemplateNotFound" errors
        try:
            generated = generator.generate_template(config)
        except Exception as e:
            if "TemplateNotFound" in str(e) or "Template not found" in str(e):
                pytest.fail(f"Template generation should not fail with TemplateNotFound: {e}")
            else:
                raise  # Re-raise if it's a different error
        
        # Criterion 2: Generated ARM templates pass validation
        validation_result = generator.validate_generated_template(config)
        assert validation_result["is_valid"], f"Template validation should pass: {validation_result['errors']}"
        
        # Criterion 3: Templates contain proper parameter substitution
        template_json = json.loads(generated.raw_json)
        
        # Check that parameters are correctly defined
        parameters = template_json.get("parameters", {})
        required_params = ["storageAccountName", "location", "performanceTier", "replicationType"]
        for param in required_params:
            assert param in parameters, f"Parameter {param} should be in template"
        
        # Check that variables use parameter substitution
        variables = template_json.get("variables", {})
        assert "storageAccountType" in variables
        
        # Check that resources use parameter references
        resources = template_json["resources"]
        storage_resource = next(r for r in resources if r["type"] == "Microsoft.Storage/storageAccounts")
        
        # Should use parameter references like [parameters('storageAccountName')]
        assert "[parameters('storageAccountName')]" in json.dumps(storage_resource)
        assert "[parameters('location')]" in json.dumps(storage_resource)
        
        # Check that tags are included when provided
        if config.tags:
            # Template should have tags parameter when config has tags
            assert "tags" in parameters
            # Resource should reference tags parameter
            assert "[parameters('tags')]" in json.dumps(storage_resource)
        
        print("All Task 3.4 acceptance criteria have been met!")