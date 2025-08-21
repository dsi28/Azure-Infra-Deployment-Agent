"""
Template generation module for Azure Infrastructure Agent.

This module handles the generation of ARM templates and Bicep files
from resource configurations using Jinja2 templating engine.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from pydantic import BaseModel

from ..config.settings import get_settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class TemplateMetadata(BaseModel):
    """Metadata for generated templates."""
    
    template_name: str
    resource_type: str
    generated_at: datetime
    generator_version: str = "1.0.0"
    parameters: Dict[str, Any]
    resource_count: int = 1


class GeneratedTemplate(BaseModel):
    """Container for generated template content and metadata."""
    
    metadata: TemplateMetadata
    content: Dict[str, Any]
    raw_json: str


class TemplateGenerator:
    """
    Main template generator class.
    
    This class handles loading template files, processing them with Jinja2,
    and generating ARM templates from resource configurations.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template generator.
        
        Args:
            templates_dir (Optional[Path]): Path to templates directory.
        """
        self.settings = get_settings()
        self.templates_dir = templates_dir or self.settings.get_templates_dir()
        
        # Ensure templates directory exists
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._add_custom_filters()
        
        logger.info(f"TemplateGenerator initialized with templates_dir: {self.templates_dir}")
    
    def _add_custom_filters(self) -> None:
        """Add custom Jinja2 filters for template processing."""
        
        def to_json(value, indent=2):
            """Convert value to JSON string."""
            return json.dumps(value, indent=indent)
        
        def camel_case(value):
            """Convert snake_case to camelCase."""
            components = value.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])
        
        def pascal_case(value):
            """Convert snake_case to PascalCase."""
            components = value.split('_')
            return ''.join(word.capitalize() for word in components)
        
        def resource_name(resource_type, name):
            """Generate a proper resource name for ARM template."""
            return f"{resource_type.split('/')[-1]}-{name}"
        
        self.env.filters['to_json'] = to_json
        self.env.filters['camel_case'] = camel_case
        self.env.filters['pascal_case'] = pascal_case
        self.env.filters['resource_name'] = resource_name
    
    def list_available_templates(self) -> List[str]:
        """
        List all available template files.
        
        Returns:
            List[str]: List of available template names.
        """
        template_files = []
        for file_path in self.templates_dir.glob("*.json.j2"):
            template_files.append(file_path.stem.replace('.json', ''))
        
        return sorted(template_files)
    
    def generate_arm_template(self, 
                            template_name: str, 
                            parameters: Dict[str, Any],
                            resource_type: str = None) -> GeneratedTemplate:
        """
        Generate an ARM template from a Jinja2 template file.
        
        Args:
            template_name (str): Name of the template file (without .json.j2 extension).
            parameters (Dict[str, Any]): Parameters to pass to the template.
            resource_type (str): The Azure resource type being generated.
            
        Returns:
            GeneratedTemplate: The generated template with metadata.
            
        Raises:
            TemplateNotFound: If the template file doesn't exist.
            Exception: If template generation fails.
        """
        template_file = f"{template_name}.json.j2"
        
        try:
            template = self.env.get_template(template_file)
            logger.info(f"Loaded template: {template_file}")
        except TemplateNotFound:
            logger.error(f"Template not found: {template_file}")
            raise
        
        try:
            # Add common template variables
            template_vars = {
                **parameters,
                'generated_at': datetime.utcnow().isoformat(),
                'generator_version': '1.0.0',
            }
            
            # Render the template
            rendered_content = template.render(**template_vars)
            
            # Parse JSON to validate and format
            template_dict = json.loads(rendered_content)
            formatted_json = json.dumps(template_dict, indent=2, sort_keys=True)
            
            # Create metadata
            metadata = TemplateMetadata(
                template_name=template_name,
                resource_type=resource_type or "unknown",
                generated_at=datetime.utcnow(),
                parameters=parameters,
                resource_count=len(template_dict.get("resources", []))
            )
            
            # Create generated template object
            generated_template = GeneratedTemplate(
                metadata=metadata,
                content=template_dict,
                raw_json=formatted_json
            )
            
            logger.info(f"Successfully generated ARM template: {template_name}")
            return generated_template
            
        except json.JSONDecodeError as e:
            logger.error(f"Generated template is not valid JSON: {e}")
            raise Exception(f"Template generation produced invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to generate template {template_name}: {e}")
            raise
    
    def save_template(self, generated_template: GeneratedTemplate, 
                     output_file: Optional[Path] = None) -> Path:
        """
        Save a generated template to file.
        
        Args:
            generated_template (GeneratedTemplate): The generated template to save.
            output_file (Optional[Path]): Output file path. If None, auto-generate.
            
        Returns:
            Path: Path to the saved file.
        """
        if output_file is None:
            output_dir = self.settings.get_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{generated_template.metadata.template_name}_{timestamp}.json"
            output_file = output_dir / filename
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the template
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(generated_template.raw_json)
        
        logger.info(f"Template saved to: {output_file}")
        return output_file
    
    def validate_template(self, template_content: Dict[str, Any]) -> List[str]:
        """
        Validate an ARM template structure.
        
        Args:
            template_content (Dict[str, Any]): The template content to validate.
            
        Returns:
            List[str]: List of validation errors (empty if valid).
        """
        errors = []
        
        # Check required top-level properties
        required_properties = ["$schema", "contentVersion", "resources"]
        for prop in required_properties:
            if prop not in template_content:
                errors.append(f"Missing required property: {prop}")
        
        # Validate schema URL
        if "$schema" in template_content:
            schema = template_content["$schema"]
            if not schema.startswith("https://schema.management.azure.com/"):
                errors.append("Invalid ARM template schema URL")
        
        # Validate content version
        if "contentVersion" in template_content:
            version = template_content["contentVersion"]
            if not isinstance(version, str) or not version:
                errors.append("contentVersion must be a non-empty string")
        
        # Validate resources array
        if "resources" in template_content:
            resources = template_content["resources"]
            if not isinstance(resources, list):
                errors.append("resources must be an array")
            else:
                for i, resource in enumerate(resources):
                    if not isinstance(resource, dict):
                        errors.append(f"Resource {i} must be an object")
                        continue
                    
                    # Check required resource properties
                    required_resource_props = ["type", "apiVersion", "name"]
                    for prop in required_resource_props:
                        if prop not in resource:
                            errors.append(f"Resource {i} missing required property: {prop}")
        
        return errors
    
    def create_basic_arm_template(self, 
                                schema_version: str = "2021-04-01",
                                content_version: str = "1.0.0.0") -> Dict[str, Any]:
        """
        Create a basic ARM template structure.
        
        Args:
            schema_version (str): ARM template schema version.
            content_version (str): Template content version.
            
        Returns:
            Dict[str, Any]: Basic ARM template structure.
        """
        return {
            "$schema": f"https://schema.management.azure.com/schemas/{schema_version}/deploymentTemplate.json#",
            "contentVersion": content_version,
            "parameters": {},
            "variables": {},
            "resources": [],
            "outputs": {}
        }


class DefaultTemplateGenerator:
    """
    Generator for default ARM templates when no custom template is available.
    
    This class creates basic ARM templates programmatically for common
    Azure resources without requiring Jinja2 template files.
    """
    
    def __init__(self):
        """Initialize the default template generator."""
        self.generator = TemplateGenerator()
    
    def generate_storage_account_template(self, 
                                        name: str,
                                        location: str,
                                        resource_group: str,
                                        sku_name: str = "Standard_LRS",
                                        kind: str = "StorageV2",
                                        access_tier: str = "Hot") -> GeneratedTemplate:
        """
        Generate a storage account ARM template.
        
        Args:
            name (str): Storage account name.
            location (str): Azure region.
            resource_group (str): Resource group name.
            sku_name (str): Storage account SKU.
            kind (str): Storage account kind.
            access_tier (str): Access tier (Hot/Cool).
            
        Returns:
            GeneratedTemplate: Generated storage account template.
        """
        template = self.generator.create_basic_arm_template()
        
        # Add parameters
        template["parameters"] = {
            "storageAccountName": {
                "type": "string",
                "defaultValue": name,
                "metadata": {
                    "description": "Name of the storage account"
                }
            },
            "location": {
                "type": "string",
                "defaultValue": location,
                "metadata": {
                    "description": "Location for the storage account"
                }
            }
        }
        
        # Add storage account resource
        storage_resource = {
            "type": "Microsoft.Storage/storageAccounts",
            "apiVersion": "2021-04-01",
            "name": "[parameters('storageAccountName')]",
            "location": "[parameters('location')]",
            "sku": {
                "name": sku_name
            },
            "kind": kind,
            "properties": {
                "accessTier": access_tier,
                "supportsHttpsTrafficOnly": True,
                "minimumTlsVersion": "TLS1_2"
            }
        }
        
        template["resources"].append(storage_resource)
        
        # Add outputs
        template["outputs"] = {
            "storageAccountName": {
                "type": "string",
                "value": "[parameters('storageAccountName')]"
            },
            "storageAccountId": {
                "type": "string",
                "value": "[resourceId('Microsoft.Storage/storageAccounts', parameters('storageAccountName'))]"
            }
        }
        
        # Create metadata
        metadata = TemplateMetadata(
            template_name="storage_account",
            resource_type="Microsoft.Storage/storageAccounts",
            generated_at=datetime.utcnow(),
            parameters={
                "name": name,
                "location": location,
                "resource_group": resource_group,
                "sku_name": sku_name,
                "kind": kind,
                "access_tier": access_tier
            }
        )
        
        return GeneratedTemplate(
            metadata=metadata,
            content=template,
            raw_json=json.dumps(template, indent=2)
        )