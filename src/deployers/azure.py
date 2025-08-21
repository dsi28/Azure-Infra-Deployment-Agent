"""
Azure deployment module for Azure Infrastructure Agent.

This module handles Azure authentication, ARM template deployment,
and deployment monitoring using the Azure SDK for Python.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from azure.identity import DefaultAzureCredential, AzureCliCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from pydantic import BaseModel

from ..config.settings import get_settings
from ..config.logging import get_logger, ContextLogger

logger = get_logger(__name__)


class DeploymentStatus(BaseModel):
    """Model for deployment status information."""
    
    name: str
    status: str
    correlation_id: Optional[str] = None
    timestamp: datetime
    provisioning_state: Optional[str] = None
    error_message: Optional[str] = None
    resource_count: int = 0


class DeploymentResult(BaseModel):
    """Model for deployment results."""
    
    deployment_name: str
    status: DeploymentStatus
    outputs: Optional[Dict[str, Any]] = None
    operation_id: Optional[str] = None
    duration: Optional[timedelta] = None
    deployed_resources: List[str] = []


class AzureAuthenticator:
    """
    Handles Azure authentication using multiple methods.
    
    This class manages authentication with Azure using Azure CLI,
    service principal, or default credential chain.
    """
    
    def __init__(self):
        """Initialize the Azure authenticator."""
        self.settings = get_settings()
        self.credential = None
        self._authenticated = False
        self.logger = ContextLogger(__name__)
    
    def authenticate(self) -> bool:
        """
        Authenticate with Azure using the configured method.
        
        Returns:
            bool: True if authentication successful, False otherwise.
        """
        auth_method = self.settings.get_auth_method()
        self.logger.set_context(auth_method=auth_method)
        
        try:
            if auth_method == "service_principal":
                self.credential = ClientSecretCredential(
                    tenant_id=self.settings.azure.tenant_id,
                    client_id=self.settings.azure.client_id,
                    client_secret=self.settings.azure.client_secret
                )
                self.logger.info("Using service principal authentication")
                
            elif auth_method == "azure_cli":
                self.credential = AzureCliCredential()
                self.logger.info("Using Azure CLI authentication")
                
            else:
                # Fall back to default credential chain
                self.credential = DefaultAzureCredential()
                self.logger.info("Using default credential chain")
            
            # Test the credential by getting a token
            token = self.credential.get_token("https://management.azure.com/.default")
            if token:
                self._authenticated = True
                self.logger.info("Azure authentication successful")
                return True
                
        except Exception as e:
            self.logger.error(f"Azure authentication failed: {e}")
            self._authenticated = False
        
        return False
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated with Azure.
        
        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._authenticated
    
    def get_credential(self):
        """
        Get the current Azure credential.
        
        Returns:
            The Azure credential object or None if not authenticated.
        """
        if not self.is_authenticated():
            self.authenticate()
        
        return self.credential if self.is_authenticated() else None


class AzureDeployer:
    """
    Main class for deploying ARM templates to Azure.
    
    This class handles template deployment, monitoring, and result reporting
    using the Azure Resource Management client.
    """
    
    def __init__(self, subscription_id: Optional[str] = None):
        """
        Initialize the Azure deployer.
        
        Args:
            subscription_id (Optional[str]): Azure subscription ID override.
        """
        self.settings = get_settings()
        self.subscription_id = subscription_id or self.settings.azure.subscription_id
        self.authenticator = AzureAuthenticator()
        self.client: Optional[ResourceManagementClient] = None
        self.logger = ContextLogger(__name__)
        
        if not self.subscription_id:
            raise ValueError("Azure subscription ID must be provided")
    
    def _ensure_authenticated(self) -> None:
        """Ensure Azure authentication and client initialization."""
        if not self.authenticator.is_authenticated():
            if not self.authenticator.authenticate():
                raise Exception("Failed to authenticate with Azure")
        
        if not self.client:
            credential = self.authenticator.get_credential()
            self.client = ResourceManagementClient(credential, self.subscription_id)
    
    def ensure_resource_group_exists(self, resource_group_name: str, location: str) -> bool:
        """
        Ensure that a resource group exists, creating it if necessary.
        
        Args:
            resource_group_name (str): Name of the resource group.
            location (str): Azure region for the resource group.
            
        Returns:
            bool: True if resource group exists or was created successfully.
        """
        self._ensure_authenticated()
        self.logger.set_context(resource_group=resource_group_name, location=location)
        
        try:
            # Check if resource group exists
            rg = self.client.resource_groups.get(resource_group_name)
            self.logger.info(f"Resource group '{resource_group_name}' already exists")
            return True
            
        except ResourceNotFoundError:
            # Create resource group
            try:
                rg_params = {
                    'location': location,
                    'tags': {
                        'created_by': 'azure-infrastructure-agent',
                        'created_at': datetime.utcnow().isoformat()
                    }
                }
                
                self.client.resource_groups.create_or_update(
                    resource_group_name, rg_params
                )
                self.logger.info(f"Created resource group '{resource_group_name}' in '{location}'")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to create resource group: {e}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error checking resource group: {e}")
            return False
    
    def deploy_template(self, 
                       deployment_name: str,
                       resource_group_name: str,
                       template: Dict[str, Any],
                       parameters: Optional[Dict[str, Any]] = None,
                       mode: str = "Incremental") -> DeploymentResult:
        """
        Deploy an ARM template to Azure.
        
        Args:
            deployment_name (str): Name for the deployment.
            resource_group_name (str): Target resource group.
            template (Dict[str, Any]): ARM template content.
            parameters (Optional[Dict[str, Any]]): Template parameters.
            mode (str): Deployment mode ('Incremental' or 'Complete').
            
        Returns:
            DeploymentResult: The deployment result.
        """
        self._ensure_authenticated()
        self.logger.set_context(
            deployment=deployment_name,
            resource_group=resource_group_name,
            mode=mode
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Prepare deployment properties
            deployment_mode = DeploymentMode.incremental if mode.lower() == 'incremental' else DeploymentMode.complete
            
            deployment_properties = {
                'mode': deployment_mode,
                'template': template,
                'parameters': self._format_parameters(parameters or {})
            }
            
            self.logger.info(f"Starting deployment '{deployment_name}' in '{resource_group_name}'")
            
            # Start the deployment
            deployment_operation = self.client.deployments.begin_create_or_update(
                resource_group_name=resource_group_name,
                deployment_name=deployment_name,
                parameters={'properties': deployment_properties}
            )
            
            # Monitor deployment progress
            deployment = deployment_operation.result(timeout=self.settings.app.max_deployment_timeout)
            end_time = datetime.utcnow()
            
            # Get deployment status
            status = self._get_deployment_status(deployment_name, resource_group_name)
            
            # Extract outputs
            outputs = {}
            if deployment.properties and deployment.properties.outputs:
                outputs = {k: v.get('value') for k, v in deployment.properties.outputs.items()}
            
            # Get deployed resources
            deployed_resources = self._get_deployed_resources(deployment_name, resource_group_name)
            
            result = DeploymentResult(
                deployment_name=deployment_name,
                status=status,
                outputs=outputs,
                operation_id=deployment.properties.correlation_id if deployment.properties else None,
                duration=end_time - start_time,
                deployed_resources=deployed_resources
            )
            
            if status.provisioning_state == "Succeeded":
                self.logger.info(f"Deployment '{deployment_name}' completed successfully")
            else:
                self.logger.warning(f"Deployment '{deployment_name}' completed with status: {status.provisioning_state}")
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = str(e)
            
            # Try to get more detailed error information
            try:
                status = self._get_deployment_status(deployment_name, resource_group_name)
                if status.error_message:
                    error_message = status.error_message
            except:
                pass
            
            self.logger.error(f"Deployment '{deployment_name}' failed: {error_message}")
            
            return DeploymentResult(
                deployment_name=deployment_name,
                status=DeploymentStatus(
                    name=deployment_name,
                    status="Failed",
                    timestamp=end_time,
                    provisioning_state="Failed",
                    error_message=error_message
                ),
                duration=end_time - start_time
            )
    
    def _format_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format parameters for ARM template deployment.
        
        Args:
            parameters (Dict[str, Any]): Raw parameters.
            
        Returns:
            Dict[str, Any]: Formatted parameters for ARM deployment.
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
    
    def _get_deployment_status(self, deployment_name: str, resource_group_name: str) -> DeploymentStatus:
        """
        Get detailed deployment status information.
        
        Args:
            deployment_name (str): Name of the deployment.
            resource_group_name (str): Resource group name.
            
        Returns:
            DeploymentStatus: Current deployment status.
        """
        try:
            deployment = self.client.deployments.get(resource_group_name, deployment_name)
            properties = deployment.properties
            
            error_message = None
            if properties and properties.error:
                error_message = properties.error.message
            
            return DeploymentStatus(
                name=deployment_name,
                status=deployment.properties.provisioning_state if properties else "Unknown",
                correlation_id=properties.correlation_id if properties else None,
                timestamp=properties.timestamp if properties else datetime.utcnow(),
                provisioning_state=properties.provisioning_state if properties else None,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return DeploymentStatus(
                name=deployment_name,
                status="Unknown",
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
    
    def _get_deployed_resources(self, deployment_name: str, resource_group_name: str) -> List[str]:
        """
        Get list of resources deployed by this deployment.
        
        Args:
            deployment_name (str): Name of the deployment.
            resource_group_name (str): Resource group name.
            
        Returns:
            List[str]: List of deployed resource names.
        """
        deployed_resources = []
        
        try:
            operations = self.client.deployment_operations.list(resource_group_name, deployment_name)
            for operation in operations:
                if operation.properties and operation.properties.target_resource:
                    resource_name = operation.properties.target_resource.resource_name
                    if resource_name and resource_name not in deployed_resources:
                        deployed_resources.append(resource_name)
        
        except Exception as e:
            logger.warning(f"Failed to get deployed resources: {e}")
        
        return deployed_resources
    
    def validate_template(self, 
                         resource_group_name: str,
                         template: Dict[str, Any],
                         parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate an ARM template without deploying it.
        
        Args:
            resource_group_name (str): Target resource group.
            template (Dict[str, Any]): ARM template content.
            parameters (Optional[Dict[str, Any]]): Template parameters.
            
        Returns:
            bool: True if template is valid, False otherwise.
        """
        self._ensure_authenticated()
        
        try:
            validation_properties = {
                'mode': DeploymentMode.incremental,
                'template': template,
                'parameters': self._format_parameters(parameters or {})
            }
            
            result = self.client.deployments.validate(
                resource_group_name=resource_group_name,
                deployment_name="validation",
                parameters={'properties': validation_properties}
            )
            
            if result.error:
                self.logger.error(f"Template validation failed: {result.error.message}")
                return False
            
            self.logger.info("Template validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Template validation error: {e}")
            return False
    
    def delete_deployment(self, deployment_name: str, resource_group_name: str) -> bool:
        """
        Delete a deployment (not the resources, just the deployment record).
        
        Args:
            deployment_name (str): Name of the deployment to delete.
            resource_group_name (str): Resource group name.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        self._ensure_authenticated()
        
        try:
            self.client.deployments.delete(resource_group_name, deployment_name)
            self.logger.info(f"Deleted deployment '{deployment_name}' from '{resource_group_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete deployment: {e}")
            return False