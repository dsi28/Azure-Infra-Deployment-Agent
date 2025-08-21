"""
Storage Account resource handler for Azure Infrastructure Agent.

This module implements the storage account resource class with parameter collection,
validation, and interactive questionnaire flow for gathering user requirements.
"""

from typing import Dict, Any, Optional, List

from .base import StorageResource, ResourceRequest, ResourceResponse
from .storage_config import (
    StorageAccountConfiguration, 
    StorageAccountTier, 
    ReplicationType, 
    AccessTier, 
    StorageAccountKind
)
from .validators import create_storage_validator
from .validation_result import ValidationResult
from ..agents.entities import ExtractedEntities, EntityType
from ..config.logging import get_logger

logger = get_logger(__name__)


class StorageAccountResource(StorageResource):
    """
    Azure Storage Account resource handler.
    
    This class manages the creation and configuration of Azure storage accounts,
    including parameter validation, interactive collection, and ARM template preparation.
    """
    
    def __init__(self):
        """Initialize storage account resource handler."""
        super().__init__()
        self.validator = create_storage_validator()
        logger.info("StorageAccountResource initialized")
    
    def process(self, request: ResourceRequest) -> ResourceResponse:
        """
        Process a storage account resource request.
        
        Args:
            request (ResourceRequest): The resource request to process.
            
        Returns:
            ResourceResponse: The processing result.
        """
        logger.info(f"Processing storage account request with {len(request.parameters)} parameters")
        
        try:
            # Create configuration from request parameters
            config = StorageAccountConfiguration.from_dict(request.parameters)
            
            # Check if configuration is complete
            if not config.is_complete():
                logger.info("Configuration incomplete, collecting parameters interactively")
                config = self.collect_parameters_interactively(config)
            
            # Validate configuration
            validation_result = self.validate_configuration(config)
            
            if validation_result.is_valid:
                logger.info("Storage account configuration validated successfully")
                message = f"Storage account configuration validated successfully. {validation_result.get_summary()}"
                if validation_result.info:
                    message += f"\n\nValidation notes:\n" + "\n".join(f"- {info}" for info in validation_result.info)
                
                return ResourceResponse(
                    success=True,
                    resource_type=self.resource_type,
                    message=message,
                    configuration=config,
                    validation_result=validation_result
                )
            else:
                logger.error("Storage account configuration validation failed")
                error_message = f"Validation failed: {validation_result.get_summary()}"
                if validation_result.errors:
                    error_message += f"\n\nErrors:\n" + "\n".join(f"- {error}" for error in validation_result.errors)
                if validation_result.warnings:
                    error_message += f"\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in validation_result.warnings)
                
                return ResourceResponse(
                    success=False,
                    resource_type=self.resource_type,
                    message=error_message,
                    configuration=None,
                    validation_result=validation_result
                )
        
        except Exception as e:
            logger.error(f"Error processing storage account request: {str(e)}")
            return ResourceResponse(
                success=False,
                resource_type=self.resource_type,
                message=f"Error processing storage account request: {str(e)}",
                configuration=None
            )
    
    def collect_parameters_interactively(self, config: Optional[StorageAccountConfiguration] = None) -> StorageAccountConfiguration:
        """
        Collect storage account parameters through interactive prompts.
        
        Args:
            config (Optional[StorageAccountConfiguration]): Existing partial configuration.
            
        Returns:
            StorageAccountConfiguration: Complete configuration with all required parameters.
        """
        logger.info("Starting interactive parameter collection")
        
        if config is None:
            config = StorageAccountConfiguration()
        
        print("\n=== Storage Account Configuration ===")
        print("Please provide the following information for your storage account:")
        print("(Press Enter to accept defaults where shown)")
        
        # Collect required parameters
        if not config.name:
            config.name = self._ask_for_parameter(
                "Storage Account Name",
                hint="Must be 3-24 characters, lowercase letters and numbers only"
            )
        
        if not config.resource_group:
            config.resource_group = self._ask_for_parameter(
                "Resource Group Name",
                hint="The resource group where the storage account will be created"
            )
        
        if not config.location:
            config.location = self._ask_for_parameter(
                "Location/Region",
                hint="Azure region (e.g., 'East US', 'West Europe')"
            )
        
        # Collect optional parameters with defaults
        new_performance_tier = self._ask_for_parameter(
            "Performance Tier", 
            default=config.performance_tier,
            hint="Standard (cost-effective) or Premium (high-performance)"
        )
        if new_performance_tier:
            config.performance_tier = new_performance_tier
        
        new_replication_type = self._ask_for_parameter(
            "Replication Type", 
            default=config.replication_type,
            hint="LRS, GRS, RAGRS, ZRS, GZRS, or RAGZRS"
        )
        if new_replication_type:
            config.replication_type = new_replication_type
        
        new_access_tier = self._ask_for_parameter(
            "Access Tier", 
            default=config.access_tier,
            hint="Hot (frequently accessed), Cool (infrequently), or Archive (rarely)"
        )
        if new_access_tier:
            config.access_tier = new_access_tier
        
        new_kind = self._ask_for_parameter(
            "Storage Account Kind", 
            default=config.kind,
            hint="StorageV2 (recommended), Storage, FileStorage, or BlockBlobStorage"
        )
        if new_kind:
            config.kind = new_kind
        
        logger.info("Interactive parameter collection completed")
        return config
    
    def _ask_for_parameter(self, param_name: str, default: str = None, hint: str = None) -> str:
        """
        Ask user for a parameter value with optional default and hint.
        
        Args:
            param_name (str): Name of the parameter to collect.
            default (str, optional): Default value if user provides empty input.
            hint (str, optional): Additional guidance for the user.
            
        Returns:
            str: The parameter value provided by the user or default.
        """
        prompt = f"\n{param_name}"
        if hint:
            prompt += f"\n  ({hint})"
        if default:
            prompt += f"\n  [Default: {default}]"
        prompt += ": "
        
        user_input = input(prompt).strip()
        
        if not user_input and default:
            return default
        
        return user_input
    
    def validate_configuration(self, config: StorageAccountConfiguration) -> ValidationResult:
        """
        Validate a storage account configuration.
        
        Args:
            config (StorageAccountConfiguration): Configuration to validate.
            
        Returns:
            ValidationResult: Validation results with errors, warnings, and info.
        """
        logger.debug("Validating storage account configuration")
        return self.validator.validate_all_parameters(config.to_dict())
    
    def generate_questionnaire_from_entities(self, entities: ExtractedEntities) -> List[Dict[str, str]]:
        """
        Generate questionnaire based on extracted entities.
        
        Args:
            entities (ExtractedEntities): Entities extracted from user input.
            
        Returns:
            List[Dict[str, str]]: List of questions to ask the user.
        """
        questions = []
        
        # Check what we're missing and generate appropriate questions
        if not entities.resource_name:
            questions.append({
                "parameter": "name",
                "question": "What would you like to name your storage account?",
                "hint": "Must be 3-24 characters, lowercase letters and numbers only",
                "required": True
            })
        
        if not entities.resource_group:
            questions.append({
                "parameter": "resource_group", 
                "question": "Which resource group should contain this storage account?",
                "hint": "Existing resource group name, or new one will be created",
                "required": True
            })
        
        if not entities.region:
            questions.append({
                "parameter": "location",
                "question": "Which Azure region should host your storage account?",
                "hint": "e.g., 'East US', 'West Europe', 'Southeast Asia'",
                "required": True
            })
        
        if not entities.performance_tier:
            questions.append({
                "parameter": "performance_tier",
                "question": "What performance tier do you need?",
                "hint": "Standard for cost-effectiveness, Premium for high performance",
                "required": False,
                "default": StorageAccountTier.STANDARD.value
            })
        
        if not entities.replication_type:
            questions.append({
                "parameter": "replication_type",
                "question": "What replication type would you like?",
                "hint": "LRS (local), GRS (geo), RAGRS (read-access geo), ZRS (zone), GZRS (geo-zone)",
                "required": False,
                "default": ReplicationType.LRS.value
            })
        
        logger.debug(f"Generated {len(questions)} questions from entities")
        return questions
    
    def create_configuration_from_questionnaire(self, answers: Dict[str, str]) -> StorageAccountConfiguration:
        """
        Create storage account configuration from questionnaire answers.
        
        Args:
            answers (Dict[str, str]): User's answers to configuration questions.
            
        Returns:
            StorageAccountConfiguration: Configuration built from answers.
        """
        logger.debug("Creating configuration from questionnaire answers")
        return StorageAccountConfiguration.from_dict(answers)


def create_storage_account_resource() -> StorageAccountResource:
    """
    Factory function to create a storage account resource handler.
    
    Returns:
        StorageAccountResource: Configured storage account resource handler.
    """
    return StorageAccountResource()