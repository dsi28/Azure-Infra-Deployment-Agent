"""
Azure authentication management for the Infrastructure Agent.

This module handles various Azure authentication methods including Azure CLI,
Service Principal, and Managed Identity authentication. It provides validation
and clear error messaging for authentication issues.
"""

import os
import subprocess
import json
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

from azure.identity import (
    DefaultAzureCredential,
    AzureCliCredential, 
    ClientSecretCredential,
    ManagedIdentityCredential,
)
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient
from pydantic import BaseModel, Field

from ..config.logging import get_logger

logger = get_logger(__name__)


class AuthenticationMethod(str, Enum):
    """Supported Azure authentication methods."""
    
    AZURE_CLI = "azure_cli"
    SERVICE_PRINCIPAL = "service_principal"
    MANAGED_IDENTITY = "managed_identity"
    DEFAULT = "default"


class AuthenticationResult(BaseModel):
    """Result of Azure authentication attempt."""
    
    success: bool = Field(description="Whether authentication was successful")
    method: Optional[AuthenticationMethod] = Field(
        default=None, description="Authentication method used"
    )
    subscription_id: Optional[str] = Field(
        default=None, description="Azure subscription ID"
    )
    tenant_id: Optional[str] = Field(
        default=None, description="Azure tenant ID"
    )
    user_info: Optional[Dict[str, Any]] = Field(
        default=None, description="User or service principal information"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if authentication failed"
    )
    credential: Optional[TokenCredential] = Field(
        default=None, description="Azure credential object", exclude=True
    )


class AzureAuthenticator:
    """
    Manages Azure authentication across different methods.
    
    Handles Azure CLI, Service Principal, and Managed Identity authentication
    with comprehensive validation and error handling.
    """
    
    def __init__(self) -> None:
        """Initialize the Azure authenticator."""
        self._cached_result: Optional[AuthenticationResult] = None
        self._cache_expiry: Optional[datetime] = None
        
    def authenticate(
        self, 
        preferred_method: Optional[AuthenticationMethod] = None,
        force_refresh: bool = False
    ) -> AuthenticationResult:
        """
        Authenticate with Azure using the specified or best available method.
        
        Args:
            preferred_method: Preferred authentication method to try first
            force_refresh: Force refresh of cached authentication
            
        Returns:
            AuthenticationResult with success status and details
        """
        # Return cached result if valid and not forcing refresh
        if (not force_refresh and 
            self._cached_result and 
            self._cached_result.success and
            self._cache_expiry and 
            datetime.now() < self._cache_expiry):
            logger.debug("Using cached authentication result")
            return self._cached_result
            
        logger.info("Starting Azure authentication process")
        
        # Try preferred method first if specified
        if preferred_method:
            result = self._try_authentication_method(preferred_method)
            if result.success:
                self._cache_result(result)
                return result
                
        # Try methods in order of preference
        methods_to_try = [
            AuthenticationMethod.AZURE_CLI,
            AuthenticationMethod.SERVICE_PRINCIPAL,
            AuthenticationMethod.MANAGED_IDENTITY,
            AuthenticationMethod.DEFAULT,
        ]
        
        # Remove preferred method from list if already tried
        if preferred_method and preferred_method in methods_to_try:
            methods_to_try.remove(preferred_method)
            
        for method in methods_to_try:
            result = self._try_authentication_method(method)
            if result.success:
                self._cache_result(result)
                return result
                
        # All methods failed
        error_msg = (
            "All Azure authentication methods failed. Please ensure you are "
            "logged in via 'az login' or have proper service principal credentials configured."
        )
        logger.error(error_msg)
        
        return AuthenticationResult(
            success=False,
            error_message=error_msg
        )
        
    def _try_authentication_method(self, method: AuthenticationMethod) -> AuthenticationResult:
        """
        Try a specific authentication method.
        
        Args:
            method: Authentication method to attempt
            
        Returns:
            AuthenticationResult with attempt details
        """
        logger.debug(f"Trying authentication method: {method}")
        
        try:
            if method == AuthenticationMethod.AZURE_CLI:
                return self._authenticate_azure_cli()
            elif method == AuthenticationMethod.SERVICE_PRINCIPAL:
                return self._authenticate_service_principal()
            elif method == AuthenticationMethod.MANAGED_IDENTITY:
                return self._authenticate_managed_identity()
            elif method == AuthenticationMethod.DEFAULT:
                return self._authenticate_default()
            else:
                return AuthenticationResult(
                    success=False,
                    error_message=f"Unsupported authentication method: {method}"
                )
        except Exception as e:
            logger.warning(f"Authentication method {method} failed: {str(e)}")
            return AuthenticationResult(
                success=False,
                method=method,
                error_message=f"Authentication failed: {str(e)}"
            )
            
    def _authenticate_azure_cli(self) -> AuthenticationResult:
        """
        Authenticate using Azure CLI credentials.
        
        Returns:
            AuthenticationResult with CLI authentication details
        """
        # Check if Azure CLI is installed and user is logged in
        cli_check = self._check_azure_cli_status()
        if not cli_check[0]:
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.AZURE_CLI,
                error_message=cli_check[1]
            )
            
        try:
            credential = AzureCliCredential()
            
            # Test the credential by getting subscription info
            subscription_client = SubscriptionClient(credential)
            subscriptions = list(subscription_client.subscriptions.list())
            
            if not subscriptions:
                return AuthenticationResult(
                    success=False,
                    method=AuthenticationMethod.AZURE_CLI,
                    error_message="No Azure subscriptions found for the current user"
                )
                
            # Get current subscription info
            current_sub = subscriptions[0]  # Use first subscription as default
            
            # Get additional user info from Azure CLI
            user_info = self._get_azure_cli_user_info()
            
            logger.info(f"Successfully authenticated via Azure CLI for subscription: {current_sub.subscription_id}")
            
            return AuthenticationResult(
                success=True,
                method=AuthenticationMethod.AZURE_CLI,
                subscription_id=current_sub.subscription_id,
                tenant_id=current_sub.tenant_id,
                user_info=user_info,
                credential=credential
            )
            
        except ClientAuthenticationError as e:
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.AZURE_CLI,
                error_message=f"Azure CLI authentication failed: {str(e)}"
            )
            
    def _authenticate_service_principal(self) -> AuthenticationResult:
        """
        Authenticate using Service Principal credentials from environment variables.
        
        Returns:
            AuthenticationResult with service principal authentication details
        """
        # Check for required environment variables
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET") 
        tenant_id = os.getenv("AZURE_TENANT_ID")
        
        if not all([client_id, client_secret, tenant_id]):
            missing_vars = []
            if not client_id:
                missing_vars.append("AZURE_CLIENT_ID")
            if not client_secret:
                missing_vars.append("AZURE_CLIENT_SECRET")
            if not tenant_id:
                missing_vars.append("AZURE_TENANT_ID")
                
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.SERVICE_PRINCIPAL,
                error_message=f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            
        try:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Test the credential
            subscription_client = SubscriptionClient(credential)
            subscriptions = list(subscription_client.subscriptions.list())
            
            if not subscriptions:
                return AuthenticationResult(
                    success=False,
                    method=AuthenticationMethod.SERVICE_PRINCIPAL,
                    error_message="No Azure subscriptions accessible with this service principal"
                )
                
            current_sub = subscriptions[0]
            
            logger.info(f"Successfully authenticated via Service Principal for subscription: {current_sub.subscription_id}")
            
            return AuthenticationResult(
                success=True,
                method=AuthenticationMethod.SERVICE_PRINCIPAL,
                subscription_id=current_sub.subscription_id,
                tenant_id=tenant_id,
                user_info={"client_id": client_id},
                credential=credential
            )
            
        except ClientAuthenticationError as e:
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.SERVICE_PRINCIPAL,
                error_message=f"Service Principal authentication failed: {str(e)}"
            )
            
    def _authenticate_managed_identity(self) -> AuthenticationResult:
        """
        Authenticate using Managed Identity (for Azure resources).
        
        Returns:
            AuthenticationResult with managed identity authentication details
        """
        try:
            credential = ManagedIdentityCredential()
            
            # Test the credential
            subscription_client = SubscriptionClient(credential)
            subscriptions = list(subscription_client.subscriptions.list())
            
            if not subscriptions:
                return AuthenticationResult(
                    success=False,
                    method=AuthenticationMethod.MANAGED_IDENTITY,
                    error_message="No Azure subscriptions accessible with managed identity"
                )
                
            current_sub = subscriptions[0]
            
            logger.info(f"Successfully authenticated via Managed Identity for subscription: {current_sub.subscription_id}")
            
            return AuthenticationResult(
                success=True,
                method=AuthenticationMethod.MANAGED_IDENTITY,
                subscription_id=current_sub.subscription_id,
                tenant_id=current_sub.tenant_id,
                user_info={"managed_identity": True},
                credential=credential
            )
            
        except ClientAuthenticationError as e:
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.MANAGED_IDENTITY,
                error_message=f"Managed Identity authentication failed: {str(e)}"
            )
            
    def _authenticate_default(self) -> AuthenticationResult:
        """
        Authenticate using DefaultAzureCredential (tries multiple methods).
        
        Returns:
            AuthenticationResult with default authentication details
        """
        try:
            credential = DefaultAzureCredential()
            
            # Test the credential
            subscription_client = SubscriptionClient(credential)
            subscriptions = list(subscription_client.subscriptions.list())
            
            if not subscriptions:
                return AuthenticationResult(
                    success=False,
                    method=AuthenticationMethod.DEFAULT,
                    error_message="No Azure subscriptions accessible with default credentials"
                )
                
            current_sub = subscriptions[0]
            
            logger.info(f"Successfully authenticated via DefaultAzureCredential for subscription: {current_sub.subscription_id}")
            
            return AuthenticationResult(
                success=True,
                method=AuthenticationMethod.DEFAULT,
                subscription_id=current_sub.subscription_id,
                tenant_id=current_sub.tenant_id,
                user_info={"default_credential": True},
                credential=credential
            )
            
        except ClientAuthenticationError as e:
            return AuthenticationResult(
                success=False,
                method=AuthenticationMethod.DEFAULT,
                error_message=f"Default credential authentication failed: {str(e)}"
            )
            
    def _check_azure_cli_status(self) -> Tuple[bool, str]:
        """
        Check if Azure CLI is installed and user is logged in.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if az command is available
            result = subprocess.run(
                ["az", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "Azure CLI is not installed or not in PATH"
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Azure CLI is not installed or not accessible"
            
        try:
            # Check if user is logged in
            result = subprocess.run(
                ["az", "account", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "Not logged in to Azure CLI. Please run 'az login'"
                
            return True, "Azure CLI is available and logged in"
            
        except subprocess.TimeoutExpired:
            return False, "Azure CLI command timed out"
            
    def _get_azure_cli_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get user information from Azure CLI.
        
        Returns:
            Dictionary with user information or None if failed
        """
        try:
            result = subprocess.run(
                ["az", "account", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                return {
                    "name": account_info.get("user", {}).get("name"),
                    "type": account_info.get("user", {}).get("type"),
                    "subscription_name": account_info.get("name"),
                    "environment_name": account_info.get("environmentName"),
                }
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            logger.warning("Failed to get Azure CLI user information")
            
        return None
        
    def _cache_result(self, result: AuthenticationResult) -> None:
        """
        Cache successful authentication result.
        
        Args:
            result: Authentication result to cache
        """
        if result.success:
            self._cached_result = result
            # Cache for 1 hour
            self._cache_expiry = datetime.now() + timedelta(hours=1)
            logger.debug("Cached authentication result")
            
    def validate_subscription_access(
        self, 
        subscription_id: str,
        auth_result: Optional[AuthenticationResult] = None
    ) -> Tuple[bool, str]:
        """
        Validate access to a specific Azure subscription.
        
        Args:
            subscription_id: Azure subscription ID to validate
            auth_result: Existing authentication result (will authenticate if None)
            
        Returns:
            Tuple of (success, message)
        """
        if not auth_result:
            auth_result = self.authenticate()
            
        if not auth_result.success:
            return False, f"Authentication failed: {auth_result.error_message}"
            
        try:
            # Test access by trying to list resource groups
            resource_client = ResourceManagementClient(
                auth_result.credential,
                subscription_id
            )
            
            # This will raise an exception if subscription is not accessible
            list(resource_client.resource_groups.list())
            
            logger.info(f"Successfully validated access to subscription: {subscription_id}")
            return True, f"Access validated for subscription: {subscription_id}"
            
        except Exception as e:
            error_msg = f"Access denied to subscription {subscription_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_available_subscriptions(
        self, 
        auth_result: Optional[AuthenticationResult] = None
    ) -> List[Dict[str, str]]:
        """
        Get list of available Azure subscriptions.
        
        Args:
            auth_result: Existing authentication result (will authenticate if None)
            
        Returns:
            List of subscription dictionaries with id, name, and state
        """
        if not auth_result:
            auth_result = self.authenticate()
            
        if not auth_result.success:
            logger.error(f"Cannot get subscriptions: {auth_result.error_message}")
            return []
            
        try:
            subscription_client = SubscriptionClient(auth_result.credential)
            subscriptions = []
            
            for sub in subscription_client.subscriptions.list():
                subscriptions.append({
                    "id": sub.subscription_id,
                    "name": sub.display_name,
                    "state": sub.state.value if sub.state else "Unknown"
                })
                
            logger.info(f"Found {len(subscriptions)} available subscriptions")
            return subscriptions
            
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {str(e)}")
            return []


def create_azure_authenticator() -> AzureAuthenticator:
    """
    Factory function to create an Azure authenticator instance.
    
    Returns:
        AzureAuthenticator instance
    """
    return AzureAuthenticator()