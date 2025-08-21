"""
Unit tests for Azure authentication functionality.

Tests cover all authentication methods, error handling, and validation scenarios.
"""

import pytest
import os
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from azure.core.exceptions import ClientAuthenticationError
from azure.mgmt.subscription.models import Subscription, SubscriptionState

from src.auth.azure_auth import (
    AzureAuthenticator,
    AuthenticationResult,
    AuthenticationMethod,
    create_azure_authenticator,
)


class TestAuthenticationResult:
    """Test AuthenticationResult model."""
    
    def test_successful_result_creation(self):
        """Test creating a successful authentication result."""
        result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub-123",
            tenant_id="test-tenant-456",
            user_info={"name": "test@example.com"}
        )
        
        assert result.success is True
        assert result.method == AuthenticationMethod.AZURE_CLI
        assert result.subscription_id == "test-sub-123"
        assert result.tenant_id == "test-tenant-456"
        assert result.user_info["name"] == "test@example.com"
        assert result.error_message is None
        
    def test_failed_result_creation(self):
        """Test creating a failed authentication result."""
        result = AuthenticationResult(
            success=False,
            method=AuthenticationMethod.SERVICE_PRINCIPAL,
            error_message="Authentication failed"
        )
        
        assert result.success is False
        assert result.method == AuthenticationMethod.SERVICE_PRINCIPAL
        assert result.error_message == "Authentication failed"
        assert result.subscription_id is None
        assert result.user_info is None


class TestAzureAuthenticator:
    """Test AzureAuthenticator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.authenticator = AzureAuthenticator()
        
    def test_factory_function(self):
        """Test the factory function creates an authenticator."""
        auth = create_azure_authenticator()
        assert isinstance(auth, AzureAuthenticator)
        
    @patch('src.auth.azure_auth.AzureAuthenticator._try_authentication_method')
    def test_authenticate_with_preferred_method_success(self, mock_try_auth):
        """Test authentication with successful preferred method."""
        # Setup mock to return successful result
        mock_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub"
        )
        mock_try_auth.return_value = mock_result
        
        result = self.authenticator.authenticate(
            preferred_method=AuthenticationMethod.AZURE_CLI
        )
        
        assert result.success is True
        assert result.method == AuthenticationMethod.AZURE_CLI
        mock_try_auth.assert_called_once_with(AuthenticationMethod.AZURE_CLI)
        
    @patch('src.auth.azure_auth.AzureAuthenticator._try_authentication_method')
    def test_authenticate_fallback_methods(self, mock_try_auth):
        """Test authentication falls back to other methods when preferred fails."""
        # First call (preferred method) fails, second succeeds
        mock_try_auth.side_effect = [
            AuthenticationResult(success=False, error_message="CLI failed"),
            AuthenticationResult(
                success=True, 
                method=AuthenticationMethod.SERVICE_PRINCIPAL,
                subscription_id="test-sub"
            )
        ]
        
        result = self.authenticator.authenticate(
            preferred_method=AuthenticationMethod.AZURE_CLI
        )
        
        assert result.success is True
        assert result.method == AuthenticationMethod.SERVICE_PRINCIPAL
        assert mock_try_auth.call_count == 2
        
    @patch('src.auth.azure_auth.AzureAuthenticator._try_authentication_method')
    def test_authenticate_all_methods_fail(self, mock_try_auth):
        """Test authentication when all methods fail."""
        # All methods return failure
        mock_try_auth.return_value = AuthenticationResult(
            success=False, 
            error_message="Method failed"
        )
        
        result = self.authenticator.authenticate()
        
        assert result.success is False
        assert "All Azure authentication methods failed" in result.error_message
        
    def test_authenticate_cached_result(self):
        """Test that cached authentication result is returned when valid."""
        # Set up a cached result
        cached_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="cached-sub"
        )
        self.authenticator._cached_result = cached_result
        self.authenticator._cache_expiry = datetime.now() + timedelta(minutes=30)
        
        result = self.authenticator.authenticate()
        
        assert result == cached_result
        assert result.subscription_id == "cached-sub"
        
    def test_authenticate_force_refresh_ignores_cache(self):
        """Test that force_refresh ignores cached results."""
        # Set up a cached result
        cached_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="cached-sub"
        )
        self.authenticator._cached_result = cached_result
        self.authenticator._cache_expiry = datetime.now() + timedelta(minutes=30)
        
        with patch.object(self.authenticator, '_try_authentication_method') as mock_try:
            new_result = AuthenticationResult(
                success=True,
                method=AuthenticationMethod.SERVICE_PRINCIPAL,
                subscription_id="new-sub"
            )
            mock_try.return_value = new_result
            
            result = self.authenticator.authenticate(force_refresh=True)
            
            assert result.subscription_id == "new-sub"
            mock_try.assert_called()
            
    @patch('subprocess.run')
    def test_check_azure_cli_status_success(self, mock_run):
        """Test successful Azure CLI status check."""
        # Mock successful az --version and az account show
        mock_run.side_effect = [
            Mock(returncode=0, stdout="azure-cli 2.40.0"),
            Mock(returncode=0, stdout='{"name": "test"}')
        ]
        
        success, message = self.authenticator._check_azure_cli_status()
        
        assert success is True
        assert "available and logged in" in message
        
    @patch('subprocess.run')
    def test_check_azure_cli_status_not_installed(self, mock_run):
        """Test Azure CLI status check when CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        success, message = self.authenticator._check_azure_cli_status()
        
        assert success is False
        assert "not installed" in message
        
    @patch('subprocess.run')
    def test_check_azure_cli_status_not_logged_in(self, mock_run):
        """Test Azure CLI status check when user is not logged in."""
        # az --version succeeds, az account show fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout="azure-cli 2.40.0"),
            Mock(returncode=1, stderr="Please run 'az login'")
        ]
        
        success, message = self.authenticator._check_azure_cli_status()
        
        assert success is False
        assert "az login" in message
        
    @patch('subprocess.run')
    def test_get_azure_cli_user_info_success(self, mock_run):
        """Test successful retrieval of Azure CLI user info."""
        account_data = {
            "user": {"name": "test@example.com", "type": "user"},
            "name": "Test Subscription",
            "environmentName": "AzureCloud"
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(account_data)
        )
        
        user_info = self.authenticator._get_azure_cli_user_info()
        
        assert user_info is not None
        assert user_info["name"] == "test@example.com"
        assert user_info["subscription_name"] == "Test Subscription"
        
    @patch('subprocess.run')
    def test_get_azure_cli_user_info_failure(self, mock_run):
        """Test Azure CLI user info retrieval failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Error")
        
        user_info = self.authenticator._get_azure_cli_user_info()
        
        assert user_info is None
        
    @patch('src.auth.azure_auth.AzureCliCredential')
    @patch('src.auth.azure_auth.SubscriptionClient')
    def test_authenticate_azure_cli_success(self, mock_sub_client, mock_credential):
        """Test successful Azure CLI authentication."""
        # Mock credential and subscription client
        mock_cred = Mock()
        mock_credential.return_value = mock_cred
        
        mock_subscription = Mock()
        mock_subscription.subscription_id = "test-sub-123"
        mock_subscription.tenant_id = "test-tenant-456"
        
        mock_client = Mock()
        mock_client.subscriptions.list.return_value = [mock_subscription]
        mock_sub_client.return_value = mock_client
        
        # Mock CLI status check
        with patch.object(self.authenticator, '_check_azure_cli_status') as mock_check:
            mock_check.return_value = (True, "CLI available")
            
            with patch.object(self.authenticator, '_get_azure_cli_user_info') as mock_user:
                mock_user.return_value = {"name": "test@example.com"}
                
                result = self.authenticator._authenticate_azure_cli()
                
        assert result.success is True
        assert result.method == AuthenticationMethod.AZURE_CLI
        assert result.subscription_id == "test-sub-123"
        assert result.tenant_id == "test-tenant-456"
        
    @patch('src.auth.azure_auth.AzureCliCredential')
    def test_authenticate_azure_cli_no_subscriptions(self, mock_credential):
        """Test Azure CLI authentication with no accessible subscriptions."""
        mock_cred = Mock()
        mock_credential.return_value = mock_cred
        
        with patch('src.auth.azure_auth.SubscriptionClient') as mock_sub_client:
            mock_client = Mock()
            mock_client.subscriptions.list.return_value = []  # No subscriptions
            mock_sub_client.return_value = mock_client
            
            with patch.object(self.authenticator, '_check_azure_cli_status') as mock_check:
                mock_check.return_value = (True, "CLI available")
                
                result = self.authenticator._authenticate_azure_cli()
                
        assert result.success is False
        assert "No Azure subscriptions found" in result.error_message
        
    @patch('src.auth.azure_auth.ClientSecretCredential')
    @patch('src.auth.azure_auth.SubscriptionClient')
    def test_authenticate_service_principal_success(self, mock_sub_client, mock_credential):
        """Test successful service principal authentication."""
        # Set environment variables
        env_vars = {
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-secret",
            "AZURE_TENANT_ID": "test-tenant-id"
        }
        
        with patch.dict(os.environ, env_vars):
            mock_cred = Mock()
            mock_credential.return_value = mock_cred
            
            mock_subscription = Mock()
            mock_subscription.subscription_id = "test-sub-123"
            
            mock_client = Mock()
            mock_client.subscriptions.list.return_value = [mock_subscription]
            mock_sub_client.return_value = mock_client
            
            result = self.authenticator._authenticate_service_principal()
            
        assert result.success is True
        assert result.method == AuthenticationMethod.SERVICE_PRINCIPAL
        assert result.subscription_id == "test-sub-123"
        assert result.tenant_id == "test-tenant-id"
        
    def test_authenticate_service_principal_missing_env_vars(self):
        """Test service principal authentication with missing environment variables."""
        # Clear environment variables
        env_vars = {
            "AZURE_CLIENT_ID": None,
            "AZURE_CLIENT_SECRET": None,
            "AZURE_TENANT_ID": None
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            result = self.authenticator._authenticate_service_principal()
            
        assert result.success is False
        assert "Missing required environment variables" in result.error_message
        assert "AZURE_CLIENT_ID" in result.error_message
        
    @patch('src.auth.azure_auth.ManagedIdentityCredential')
    @patch('src.auth.azure_auth.SubscriptionClient')
    def test_authenticate_managed_identity_success(self, mock_sub_client, mock_credential):
        """Test successful managed identity authentication."""
        mock_cred = Mock()
        mock_credential.return_value = mock_cred
        
        mock_subscription = Mock()
        mock_subscription.subscription_id = "test-sub-123"
        mock_subscription.tenant_id = "test-tenant-456"
        
        mock_client = Mock()
        mock_client.subscriptions.list.return_value = [mock_subscription]
        mock_sub_client.return_value = mock_client
        
        result = self.authenticator._authenticate_managed_identity()
        
        assert result.success is True
        assert result.method == AuthenticationMethod.MANAGED_IDENTITY
        assert result.subscription_id == "test-sub-123"
        
    @patch('src.auth.azure_auth.ResourceManagementClient')
    def test_validate_subscription_access_success(self, mock_resource_client):
        """Test successful subscription access validation."""
        mock_auth_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub",
            credential=Mock()
        )
        
        mock_client = Mock()
        mock_client.resource_groups.list.return_value = []
        mock_resource_client.return_value = mock_client
        
        success, message = self.authenticator.validate_subscription_access(
            "test-sub", mock_auth_result
        )
        
        assert success is True
        assert "Access validated" in message
        
    @patch('src.auth.azure_auth.ResourceManagementClient')
    def test_validate_subscription_access_denied(self, mock_resource_client):
        """Test subscription access validation when access is denied."""
        mock_auth_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub",
            credential=Mock()
        )
        
        mock_resource_client.side_effect = ClientAuthenticationError("Access denied")
        
        success, message = self.authenticator.validate_subscription_access(
            "test-sub", mock_auth_result
        )
        
        assert success is False
        assert "Access denied" in message
        
    @patch('src.auth.azure_auth.SubscriptionClient')
    def test_get_available_subscriptions_success(self, mock_sub_client):
        """Test successful retrieval of available subscriptions."""
        mock_auth_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            credential=Mock()
        )
        
        mock_sub1 = Mock()
        mock_sub1.subscription_id = "sub-1"
        mock_sub1.display_name = "Subscription 1"
        mock_sub1.state = SubscriptionState.ENABLED
        
        mock_sub2 = Mock()
        mock_sub2.subscription_id = "sub-2"
        mock_sub2.display_name = "Subscription 2"
        mock_sub2.state = SubscriptionState.DISABLED
        
        mock_client = Mock()
        mock_client.subscriptions.list.return_value = [mock_sub1, mock_sub2]
        mock_sub_client.return_value = mock_client
        
        subscriptions = self.authenticator.get_available_subscriptions(mock_auth_result)
        
        assert len(subscriptions) == 2
        assert subscriptions[0]["id"] == "sub-1"
        assert subscriptions[0]["name"] == "Subscription 1"
        assert subscriptions[0]["state"] == "Enabled"
        
    def test_get_available_subscriptions_auth_failure(self):
        """Test get available subscriptions when authentication fails."""
        mock_auth_result = AuthenticationResult(
            success=False,
            error_message="Auth failed"
        )
        
        subscriptions = self.authenticator.get_available_subscriptions(mock_auth_result)
        
        assert subscriptions == []
        
    def test_cache_result(self):
        """Test caching of successful authentication result."""
        result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub"
        )
        
        self.authenticator._cache_result(result)
        
        assert self.authenticator._cached_result == result
        assert self.authenticator._cache_expiry is not None
        assert self.authenticator._cache_expiry > datetime.now()
        
    def test_cache_result_failure_not_cached(self):
        """Test that failed authentication results are not cached."""
        result = AuthenticationResult(
            success=False,
            error_message="Failed"
        )
        
        self.authenticator._cache_result(result)
        
        assert self.authenticator._cached_result is None
        assert self.authenticator._cache_expiry is None


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.authenticator = AzureAuthenticator()
        
    def test_unsupported_authentication_method(self):
        """Test handling of unsupported authentication method.""" 
        # This should not happen in practice due to enum, but test edge case
        with patch('src.auth.azure_auth.AuthenticationMethod') as mock_method:
            mock_method.INVALID = "invalid_method"
            
            result = self.authenticator._try_authentication_method("invalid_method")
            
            assert result.success is False
            assert "Unsupported authentication method" in result.error_message
            
    @patch('src.auth.azure_auth.AzureCliCredential')
    def test_authentication_exception_handling(self, mock_credential):
        """Test handling of unexpected exceptions during authentication."""
        mock_credential.side_effect = Exception("Unexpected error")
        
        result = self.authenticator._try_authentication_method(
            AuthenticationMethod.AZURE_CLI
        )
        
        assert result.success is False
        assert "Authentication failed" in result.error_message
        assert "Unexpected error" in result.error_message


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures.""" 
        self.authenticator = AzureAuthenticator()
        
    @patch.object(AzureAuthenticator, '_authenticate_azure_cli')
    @patch.object(AzureAuthenticator, '_authenticate_service_principal') 
    def test_cli_fails_fallback_to_service_principal(self, mock_sp, mock_cli):
        """Test realistic scenario where CLI auth fails but SP succeeds."""
        # CLI auth fails
        mock_cli.return_value = AuthenticationResult(
            success=False,
            method=AuthenticationMethod.AZURE_CLI,
            error_message="Not logged in to Azure CLI"
        )
        
        # Service principal succeeds
        mock_sp.return_value = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.SERVICE_PRINCIPAL,
            subscription_id="test-sub",
            tenant_id="test-tenant"
        )
        
        result = self.authenticator.authenticate()
        
        assert result.success is True
        assert result.method == AuthenticationMethod.SERVICE_PRINCIPAL
        
    @patch.object(AzureAuthenticator, 'authenticate')
    def test_subscription_validation_without_auth_result(self, mock_auth):
        """Test subscription validation that triggers authentication.""" 
        mock_auth.return_value = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            credential=Mock()
        )
        
        with patch('src.auth.azure_auth.ResourceManagementClient') as mock_client:
            mock_resource_client = Mock()
            mock_resource_client.resource_groups.list.return_value = []
            mock_client.return_value = mock_resource_client
            
            success, message = self.authenticator.validate_subscription_access("test-sub")
            
            assert success is True
            mock_auth.assert_called_once()