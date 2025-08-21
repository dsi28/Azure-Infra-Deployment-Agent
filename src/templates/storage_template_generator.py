"""
Storage Account template generator for Azure Infrastructure Agent.

This module provides specialized template generation functionality for 
Azure Storage Account resources with parameter substitution and validation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .generator import TemplateGenerator, GeneratedTemplate, TemplateMetadata
from ..resources.storage_config import StorageAccountConfiguration
from ..config.logging import get_logger

logger = get_logger(__name__)


class StorageAccountTemplateGenerator:
    """
    Specialized template generator for Azure Storage Accounts.
    
    This class extends the base template generator with storage-specific
    functionality including parameter mapping, validation, and preview.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the storage account template generator.
        
        Args:
            templates_dir (Optional[Path]): Path to templates directory.
        """
        self.generator = TemplateGenerator(templates_dir)
        logger.info("StorageAccountTemplateGenerator initialized")
    
    def generate_template(self, config: StorageAccountConfiguration) -> GeneratedTemplate:
        """
        Generate ARM template for storage account from configuration.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            
        Returns:
            GeneratedTemplate: Generated ARM template.
            
        Raises:
            ValueError: If configuration is invalid.
            Exception: If template generation fails.
        """
        if not config.is_complete():
            missing = config.get_missing_required_parameters()
            raise ValueError(f"Configuration missing required parameters: {', '.join(missing)}")
        
        logger.info(f"Generating storage account template for: {config.name}")
        
        # Prepare template parameters
        template_params = self._prepare_template_parameters(config)
        
        try:
            # Generate the template using Jinja2
            generated = self.generator.generate_arm_template(
                template_name="storage_account",
                parameters=template_params,
                resource_type="Microsoft.Storage/storageAccounts"
            )
            
            logger.info("Storage account template generated successfully")
            return generated
            
        except Exception as e:
            logger.error(f"Failed to generate storage account template: {e}")
            raise
    
    def _prepare_template_parameters(self, config: StorageAccountConfiguration) -> Dict[str, Any]:
        """
        Prepare template parameters from storage account configuration.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            
        Returns:
            Dict[str, Any]: Template parameters.
        """
        # Convert performance tier and replication to SKU format
        sku_name = f"{config.performance_tier}_{config.replication_type}"
        
        template_params = {
            "config": config,
            "storageAccountName": config.name,
            "location": config.location,
            "performanceTier": config.performance_tier,
            "replicationType": config.replication_type,
            "accessTier": config.access_tier,
            "storageAccountKind": config.kind,
            "enableHttpsOnly": config.enable_https_only,
            "enableHierarchicalNamespace": config.enable_hierarchical_namespace,
            "skuName": sku_name,
            "resourceGroup": config.resource_group,
            "tags": config.tags
        }
        
        logger.debug(f"Prepared template parameters: {list(template_params.keys())}")
        return template_params
    
    def generate_parameters_file(self, config: StorageAccountConfiguration) -> Dict[str, Any]:
        """
        Generate ARM template parameters file for the storage account.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            
        Returns:
            Dict[str, Any]: ARM parameters file content.
        """
        parameters = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "storageAccountName": {
                    "value": config.name
                },
                "location": {
                    "value": config.location
                },
                "performanceTier": {
                    "value": config.performance_tier
                },
                "replicationType": {
                    "value": config.replication_type
                },
                "accessTier": {
                    "value": config.access_tier
                },
                "storageAccountKind": {
                    "value": config.kind
                },
                "enableHttpsOnly": {
                    "value": config.enable_https_only
                },
                "enableHierarchicalNamespace": {
                    "value": config.enable_hierarchical_namespace
                }
            }
        }
        
        # Add tags if present
        if config.tags:
            parameters["parameters"]["tags"] = {
                "value": config.tags
            }
        
        logger.info("Generated ARM parameters file")
        return parameters
    
    def preview_template(self, config: StorageAccountConfiguration) -> str:
        """
        Generate a formatted preview of the ARM template.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            
        Returns:
            str: Formatted template preview.
        """
        generated = self.generate_template(config)
        
        # Create a user-friendly preview
        preview_lines = [
            "=" * 60,
            "ARM TEMPLATE PREVIEW",
            "=" * 60,
            "",
            f"Template: {generated.metadata.template_name}",
            f"Resource Type: {generated.metadata.resource_type}",
            f"Generated: {generated.metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Resources: {generated.metadata.resource_count}",
            "",
            "Configuration Summary:",
            f"  Storage Account Name: {config.name}",
            f"  Resource Group: {config.resource_group}",
            f"  Location: {config.location}",
            f"  Performance Tier: {config.performance_tier}",
            f"  Replication: {config.replication_type}",
            f"  Access Tier: {config.access_tier}",
            f"  Kind: {config.kind}",
            f"  HTTPS Only: {config.enable_https_only}",
            f"  Hierarchical Namespace: {config.enable_hierarchical_namespace}",
        ]
        
        if config.tags:
            preview_lines.append("  Tags:")
            for key, value in config.tags.items():
                preview_lines.append(f"    {key}: {value}")
        
        preview_lines.extend([
            "",
            "ARM Template (JSON):",
            "-" * 40,
            generated.raw_json,
            "",
            "=" * 60
        ])
        
        return "\n".join(preview_lines)
    
    def validate_generated_template(self, config: StorageAccountConfiguration) -> Dict[str, Any]:
        """
        Validate a generated storage account template.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            
        Returns:
            Dict[str, Any]: Validation results with errors and warnings.
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        try:
            generated = self.generate_template(config)
            
            # Use base template validator
            template_errors = self.generator.validate_template(generated.content)
            if template_errors:
                validation_result["is_valid"] = False
                validation_result["errors"].extend(template_errors)
            
            # Storage-specific validations
            self._validate_storage_specific_properties(generated.content, validation_result)
            
            if validation_result["is_valid"]:
                validation_result["info"].append("ARM template structure is valid")
                validation_result["info"].append(f"Template contains {len(generated.content.get('resources', []))} resource(s)")
            
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Template generation failed: {str(e)}")
        
        logger.info(f"Template validation completed. Valid: {validation_result['is_valid']}")
        return validation_result
    
    def _validate_storage_specific_properties(self, template_content: Dict[str, Any], 
                                            validation_result: Dict[str, Any]) -> None:
        """
        Validate storage account specific properties in the template.
        
        Args:
            template_content (Dict[str, Any]): Template content to validate.
            validation_result (Dict[str, Any]): Validation result to update.
        """
        resources = template_content.get("resources", [])
        
        # Find storage account resource
        storage_resources = [r for r in resources if r.get("type") == "Microsoft.Storage/storageAccounts"]
        
        if not storage_resources:
            validation_result["errors"].append("No storage account resource found in template")
            return
        
        if len(storage_resources) > 1:
            validation_result["warnings"].append("Multiple storage account resources found")
        
        storage_resource = storage_resources[0]
        
        # Validate required properties
        if "sku" not in storage_resource:
            validation_result["errors"].append("Storage account missing SKU configuration")
        
        if "kind" not in storage_resource:
            validation_result["errors"].append("Storage account missing kind specification")
        
        # Check properties section
        properties = storage_resource.get("properties", {})
        
        # Validate security settings
        if not properties.get("supportsHttpsTrafficOnly", False):
            validation_result["warnings"].append("HTTPS-only traffic is not enforced")
        
        if properties.get("allowBlobPublicAccess", True):
            validation_result["warnings"].append("Public blob access is enabled - consider security implications")
        
        # Check TLS version
        tls_version = properties.get("minimumTlsVersion")
        if tls_version != "TLS1_2":
            validation_result["warnings"].append("Consider using TLS 1.2 as minimum TLS version")
        
        # Check encryption
        if "encryption" not in properties:
            validation_result["warnings"].append("Encryption configuration not explicitly defined")
        
        validation_result["info"].append("Storage account resource structure validated")
    
    def save_template_files(self, config: StorageAccountConfiguration, 
                          output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Save both ARM template and parameters file.
        
        Args:
            config (StorageAccountConfiguration): Storage account configuration.
            output_dir (Optional[Path]): Output directory path.
            
        Returns:
            Dict[str, Path]: Dictionary with saved file paths.
        """
        if output_dir is None:
            output_dir = Path("./generated_templates")
        
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"storage_account_{config.name}_{timestamp}"
        
        # Generate and save template
        generated = self.generate_template(config)
        template_path = output_dir / f"{base_name}.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(generated.raw_json)
        
        # Generate and save parameters file
        parameters = self.generate_parameters_file(config)
        params_path = output_dir / f"{base_name}.parameters.json"
        with open(params_path, 'w', encoding='utf-8') as f:
            json.dump(parameters, f, indent=2)
        
        saved_files = {
            "template": template_path,
            "parameters": params_path
        }
        
        logger.info(f"Saved template files: {list(saved_files.values())}")
        return saved_files


def create_storage_template_generator(templates_dir: Optional[Path] = None) -> StorageAccountTemplateGenerator:
    """
    Factory function to create a storage account template generator.
    
    Args:
        templates_dir (Optional[Path]): Path to templates directory.
        
    Returns:
        StorageAccountTemplateGenerator: Configured template generator.
    """
    return StorageAccountTemplateGenerator(templates_dir)