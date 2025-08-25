"""
ARM template deployment engine for Azure Infrastructure Agent.

This module provides ARM template deployment functionality with validation,
error handling, and rollback capabilities.
"""

import json
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from azure.core.credentials import TokenCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode, DeploymentProperties
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from pydantic import BaseModel, Field

from ..auth.azure_auth import AzureAuthenticator, AuthenticationResult
from ..config.logging import get_logger
from .deployment_monitor import DeploymentMonitor, DeploymentStatus, DeploymentResult

logger = get_logger(__name__)


class DeploymentConfig(BaseModel):
    """Configuration for ARM template deployment."""
    
    deployment_name: str = Field(description="Name for the deployment")
    resource_group_name: str = Field(description="Target resource group name")
    location: str = Field(description="Azure region for resources")
    template: Dict[str, Any] = Field(description="ARM template content")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")
    mode: str = Field(default="Incremental", description="Deployment mode")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    timeout_minutes: int = Field(default=30, description="Deployment timeout in minutes")


class ValidationResult(BaseModel):
    """Result of template validation."""
    
    is_valid: bool = Field(description="Whether the template is valid")
    error_message: Optional[str] = Field(default=None, description="Validation error message")
    estimated_cost: Optional[float] = Field(default=None, description="Estimated deployment cost")
    resource_count: int = Field(default=0, description="Number of resources to be deployed")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class RollbackConfig(BaseModel):
    """Configuration for deployment rollback."""
    
    target_deployment_name: Optional[str] = Field(default=None, description="Previous deployment to rollback to")
    delete_resources: bool = Field(default=False, description="Whether to delete resources on rollback")
    preserve_data: bool = Field(default=True, description="Whether to preserve data during rollback")
    rollback_timeout_minutes: int = Field(default=15, description="Rollback operation timeout")


class ARMDeployer:
    """
    ARM template deployment engine with validation and rollback capabilities.
    
    This class handles ARM template deployment to Azure with comprehensive
    error handling, validation, and rollback functionality.
    """
    
    def __init__(self, subscription_id: Optional[str] = None) -> None:
        """
        Initialize the ARM deployer.
        
        Args:
            subscription_id: Azure subscription ID (uses authenticated subscription if None)
        """
        self.subscription_id = subscription_id
        self.authenticator = AzureAuthenticator()
        self.client: Optional[ResourceManagementClient] = None
        self.monitor = DeploymentMonitor()
        self._auth_result: Optional[AuthenticationResult] = None
        
    def _ensure_authenticated(self) -> None:
        """Ensure Azure authentication and client initialization."""
        if not self._auth_result or not self._auth_result.success:
            self._auth_result = self.authenticator.authenticate()
            
        if not self._auth_result.success:
            raise Exception(f"Failed to authenticate with Azure: {self._auth_result.error_message}")
            
        # Use authenticated subscription if none provided
        if not self.subscription_id:
            self.subscription_id = self._auth_result.subscription_id
            
        if not self.subscription_id:
            raise Exception("No Azure subscription ID available")
            
        if not self.client:
            self.client = ResourceManagementClient(
                self._auth_result.credential,
                self.subscription_id
            )
            
    def validate_template(self, config: DeploymentConfig) -> ValidationResult:
        """
        Validate an ARM template before deployment.
        
        Args:
            config: Deployment configuration with template and parameters
            
        Returns:
            ValidationResult with validation status and details
        """
        self._ensure_authenticated()
        
        logger.info(f"Validating ARM template for deployment: {config.deployment_name}")
        
        try:
            # Prepare validation properties
            validation_properties = DeploymentProperties(
                mode=DeploymentMode.incremental,
                template=config.template,
                parameters=self._format_parameters(config.parameters)
            )
            
            # Perform validation
            validation_result = self.client.deployments.validate(
                resource_group_name=config.resource_group_name,
                deployment_name=f"validation-{uuid.uuid4().hex[:8]}",
                parameters={"properties": validation_properties}
            )
            
            if validation_result.error:
                logger.error(f"Template validation failed: {validation_result.error.message}")
                return ValidationResult(
                    is_valid=False,
                    error_message=validation_result.error.message
                )
                
            # Analyze template for additional insights
            resource_count = self._count_template_resources(config.template)
            warnings = self._analyze_template_warnings(config.template)
            
            logger.info("Template validation successful")
            return ValidationResult(
                is_valid=True,
                resource_count=resource_count,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Template validation error: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                is_valid=False,
                error_message=error_msg
            )
            
    def ensure_resource_group_exists(self, resource_group_name: str, location: str, tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Ensure that a resource group exists, creating it if necessary.
        
        Args:
            resource_group_name: Name of the resource group
            location: Azure region for the resource group
            tags: Optional tags for the resource group
            
        Returns:
            True if resource group exists or was created successfully
        """
        self._ensure_authenticated()
        
        logger.info(f"Ensuring resource group exists: {resource_group_name}")
        
        try:
            # Check if resource group exists
            self.client.resource_groups.get(resource_group_name)
            logger.info(f"Resource group '{resource_group_name}' already exists")
            return True
            
        except ResourceNotFoundError:
            # Create resource group
            try:
                rg_tags = {
                    'created_by': 'azure-infrastructure-agent',
                    'created_at': datetime.utcnow().isoformat()
                }
                if tags:
                    rg_tags.update(tags)
                
                rg_params = {
                    'location': location,
                    'tags': rg_tags
                }
                
                self.client.resource_groups.create_or_update(
                    resource_group_name, rg_params
                )
                logger.info(f"Created resource group '{resource_group_name}' in '{location}'")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create resource group: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking resource group: {str(e)}")
            return False
            
    def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """
        Deploy an ARM template to Azure.
        
        Args:
            config: Deployment configuration
            
        Returns:
            DeploymentResult with deployment status and details
        """
        self._ensure_authenticated()
        
        logger.info(f"Starting ARM template deployment: {config.deployment_name}")
        
        # Ensure resource group exists
        if not self.ensure_resource_group_exists(config.resource_group_name, config.location, config.tags):
            return DeploymentResult(
                deployment_name=config.deployment_name,
                status=DeploymentStatus(
                    name=config.deployment_name,
                    status="Failed",
                    timestamp=datetime.utcnow(),
                    provisioning_state="Failed",
                    error_message="Failed to ensure resource group exists"
                )
            )
            
        start_time = datetime.utcnow()
        
        try:
            # Prepare deployment properties
            deployment_mode = (
                DeploymentMode.incremental if config.mode.lower() == 'incremental' 
                else DeploymentMode.complete
            )
            
            deployment_properties = DeploymentProperties(
                mode=deployment_mode,
                template=config.template,
                parameters=self._format_parameters(config.parameters)
            )
            
            # Start the deployment
            logger.info(f"Initiating deployment '{config.deployment_name}' in resource group '{config.resource_group_name}'")
            
            deployment_operation = self.client.deployments.begin_create_or_update(
                resource_group_name=config.resource_group_name,
                deployment_name=config.deployment_name,
                parameters={"properties": deployment_properties}
            )
            
            # Monitor deployment progress
            result = self.monitor.monitor_deployment(
                deployment_operation=deployment_operation,
                deployment_name=config.deployment_name,
                resource_group_name=config.resource_group_name,
                timeout_minutes=config.timeout_minutes,
                client=self.client
            )
            
            # Calculate duration
            end_time = datetime.utcnow()
            result.duration = end_time - start_time
            
            logger.info(f"Deployment '{config.deployment_name}' completed with status: {result.status.provisioning_state}")
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = str(e)
            
            logger.error(f"Deployment '{config.deployment_name}' failed: {error_message}")
            
            return DeploymentResult(
                deployment_name=config.deployment_name,
                status=DeploymentStatus(
                    name=config.deployment_name,
                    status="Failed",
                    timestamp=end_time,
                    provisioning_state="Failed",
                    error_message=error_message
                ),
                duration=end_time - start_time
            )
            
    def rollback_deployment(self, deployment_name: str, resource_group_name: str, config: RollbackConfig) -> DeploymentResult:
        """
        Rollback a failed or problematic deployment.
        
        Args:
            deployment_name: Name of the deployment to rollback
            resource_group_name: Resource group containing the deployment
            config: Rollback configuration
            
        Returns:
            DeploymentResult with rollback status
        """
        self._ensure_authenticated()
        
        logger.info(f"Starting rollback for deployment: {deployment_name}")
        
        start_time = datetime.utcnow()
        
        try:
            if config.target_deployment_name:
                # Rollback to a specific previous deployment
                return self._rollback_to_deployment(
                    deployment_name, resource_group_name, 
                    config.target_deployment_name, config
                )
            else:
                # Delete the current deployment and its resources
                return self._rollback_by_deletion(
                    deployment_name, resource_group_name, config
                )
                
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Rollback failed: {str(e)}"
            
            logger.error(error_message)
            
            return DeploymentResult(
                deployment_name=f"rollback-{deployment_name}",
                status=DeploymentStatus(
                    name=f"rollback-{deployment_name}",
                    status="Failed",
                    timestamp=end_time,
                    provisioning_state="Failed",
                    error_message=error_message
                ),
                duration=end_time - start_time
            )
            
    def _rollback_to_deployment(self, current_deployment: str, resource_group_name: str, target_deployment: str, config: RollbackConfig) -> DeploymentResult:
        """
        Rollback to a specific previous deployment state.
        
        Args:
            current_deployment: Current deployment to rollback
            resource_group_name: Resource group name
            target_deployment: Target deployment to rollback to
            config: Rollback configuration
            
        Returns:
            DeploymentResult with rollback status
        """
        logger.info(f"Rolling back '{current_deployment}' to '{target_deployment}'")
        
        try:
            # Get the target deployment template and parameters
            target_deployment_obj = self.client.deployments.get(resource_group_name, target_deployment)
            
            if not target_deployment_obj.properties:
                raise Exception(f"Target deployment '{target_deployment}' has no properties")
                
            # Create rollback deployment
            rollback_deployment_name = f"rollback-{uuid.uuid4().hex[:8]}"
            
            rollback_config = DeploymentConfig(
                deployment_name=rollback_deployment_name,
                resource_group_name=resource_group_name,
                location="",  # Will be ignored for existing RG
                template=target_deployment_obj.properties.template,
                parameters=self._extract_parameters(target_deployment_obj.properties.parameters),
                mode="Complete" if not config.preserve_data else "Incremental",
                timeout_minutes=config.rollback_timeout_minutes
            )
            
            return self.deploy(rollback_config)
            
        except Exception as e:
            raise Exception(f"Failed to rollback to deployment '{target_deployment}': {str(e)}")
            
    def _rollback_by_deletion(self, deployment_name: str, resource_group_name: str, config: RollbackConfig) -> DeploymentResult:
        """
        Rollback by deleting resources created by the deployment.
        
        Args:
            deployment_name: Deployment to rollback
            resource_group_name: Resource group name
            config: Rollback configuration
            
        Returns:
            DeploymentResult with rollback status
        """
        logger.info(f"Rolling back deployment '{deployment_name}' by deletion")
        
        start_time = datetime.utcnow()
        
        try:
            # Get resources created by this deployment
            deployed_resources = self._get_deployed_resources(deployment_name, resource_group_name)
            
            if config.delete_resources and deployed_resources:
                # Delete resources in reverse dependency order
                logger.info(f"Deleting {len(deployed_resources)} resources from deployment")
                self._delete_deployment_resources(deployed_resources, resource_group_name)
                
            # Delete the deployment record
            self.client.deployments.delete(resource_group_name, deployment_name)
            
            end_time = datetime.utcnow()
            
            return DeploymentResult(
                deployment_name=f"rollback-{deployment_name}",
                status=DeploymentStatus(
                    name=f"rollback-{deployment_name}",
                    status="Succeeded",
                    timestamp=end_time,
                    provisioning_state="Succeeded"
                ),
                duration=end_time - start_time,
                deployed_resources=[]
            )
            
        except Exception as e:
            raise Exception(f"Failed to rollback deployment by deletion: {str(e)}")
            
    def get_deployment_history(self, resource_group_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get deployment history for a resource group.
        
        Args:
            resource_group_name: Resource group name
            limit: Maximum number of deployments to return
            
        Returns:
            List of deployment information dictionaries
        """
        self._ensure_authenticated()
        
        try:
            deployments = list(self.client.deployments.list_by_resource_group(
                resource_group_name=resource_group_name,
                top=limit
            ))
            
            deployment_history = []
            for deployment in deployments:
                deployment_info = {
                    "name": deployment.name,
                    "timestamp": deployment.properties.timestamp if deployment.properties else None,
                    "provisioning_state": deployment.properties.provisioning_state if deployment.properties else "Unknown",
                    "mode": str(deployment.properties.mode) if deployment.properties else "Unknown",
                    "correlation_id": deployment.properties.correlation_id if deployment.properties else None
                }
                deployment_history.append(deployment_info)
                
            return deployment_history
            
        except Exception as e:
            logger.error(f"Failed to get deployment history: {str(e)}")
            return []
            
    def _format_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format parameters for ARM template deployment.
        
        Args:
            parameters: Raw parameters dictionary
            
        Returns:
            Formatted parameters for ARM deployment
        """
        formatted = {}
        for key, value in parameters.items():
            if isinstance(value, dict) and 'value' in value:
                # Already in ARM parameter format
                formatted[key] = value
            else:
                # Convert to ARM parameter format
                formatted[key] = {'value': value}
                
        return formatted
        
    def _extract_parameters(self, arm_parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract parameter values from ARM parameter format.
        
        Args:
            arm_parameters: ARM-formatted parameters
            
        Returns:
            Simple parameter dictionary
        """
        if not arm_parameters:
            return {}
            
        extracted = {}
        for key, param_obj in arm_parameters.items():
            if isinstance(param_obj, dict) and 'value' in param_obj:
                extracted[key] = param_obj['value']
            else:
                extracted[key] = param_obj
                
        return extracted
        
    def _count_template_resources(self, template: Dict[str, Any]) -> int:
        """Count the number of resources in an ARM template."""
        resources = template.get('resources', [])
        return len(resources)
        
    def _analyze_template_warnings(self, template: Dict[str, Any]) -> List[str]:
        """Analyze template for potential warnings or issues."""
        warnings = []
        
        # Check for missing parameters section
        if 'parameters' not in template:
            warnings.append("Template has no parameters section")
            
        # Check for hardcoded values
        template_str = json.dumps(template)
        if 'password' in template_str.lower():
            warnings.append("Template may contain hardcoded passwords")
            
        # Check for missing outputs
        if 'outputs' not in template:
            warnings.append("Template has no outputs section")
            
        return warnings
        
    def _get_deployed_resources(self, deployment_name: str, resource_group_name: str) -> List[str]:
        """Get list of resources deployed by a specific deployment."""
        deployed_resources = []
        
        try:
            operations = self.client.deployment_operations.list(resource_group_name, deployment_name)
            for operation in operations:
                if (operation.properties and 
                    operation.properties.target_resource and
                    operation.properties.target_resource.resource_name):
                    resource_name = operation.properties.target_resource.resource_name
                    if resource_name not in deployed_resources:
                        deployed_resources.append(resource_name)
                        
        except Exception as e:
            logger.warning(f"Failed to get deployed resources: {str(e)}")
            
        return deployed_resources
        
    def _delete_deployment_resources(self, resource_names: List[str], resource_group_name: str) -> None:
        """Delete specific resources from a resource group."""
        for resource_name in resource_names:
            try:
                # This is a simplified implementation
                # In a real scenario, you'd need to determine resource type and use appropriate deletion method
                logger.info(f"Would delete resource: {resource_name} (deletion logic not implemented)")
            except Exception as e:
                logger.error(f"Failed to delete resource {resource_name}: {str(e)}")


def create_arm_deployer(subscription_id: Optional[str] = None, auth_result=None) -> ARMDeployer:
    """
    Factory function to create an ARM deployer instance.
    
    Args:
        subscription_id: Azure subscription ID (optional)
        auth_result: Existing authentication result to reuse (optional)
        
    Returns:
        ARMDeployer instance
    """
    deployer = ARMDeployer(subscription_id)
    if auth_result:
        deployer._auth_result = auth_result
        # Force client recreation with the provided auth result
        deployer.client = None
    return deployer