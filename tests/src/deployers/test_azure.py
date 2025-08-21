"""
Unit tests for deployers.azure module.

Tests for Azure deployment functionality including AzureAuthenticator,
AzureDeployer, and various deployment scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.deployers.azure import (
    AzureAuthenticator,
    AzureDeployer,
    DeploymentStatus,
    DeploymentResult
)


class TestDeploymentStatus:
    """Test cases for DeploymentStatus model."""
    
    def test_deployment_status_creation_success(self):
        """Test successful DeploymentStatus creation."""
        now = datetime.utcnow()
        status = DeploymentStatus(
            name="test-deployment",
            status="Succeeded",
            correlation_id="corr-123",
            timestamp=now,
            provisioning_state="Succeeded",
            error_message=None,
            resource_count=3
        )
        
        assert status.name == "test-deployment"
        assert status.status == "Succeeded"
        assert status.correlation_id == "corr-123"
        assert status.timestamp == now
        assert status.provisioning_state == "Succeeded"
        assert status.error_message is None
        assert status.resource_count == 3
    
    def test_deployment_status_minimal_creation(self):
        """Test DeploymentStatus creation with minimal fields."""
        now = datetime.utcnow()
        status = DeploymentStatus(
            name="test-deployment",
            status="Running",
            timestamp=now
        )
        
        assert status.name == "test-deployment"
        assert status.status == "Running"
        assert status.timestamp == now
        assert status.correlation_id is None
        assert status.provisioning_state is None
        assert status.error_message is None
        assert status.resource_count == 0


class TestDeploymentResult:
    """Test cases for DeploymentResult model."""
    
    def test_deployment_result_creation_success(self):
        """Test successful DeploymentResult creation."""
        now = datetime.utcnow()
        status = DeploymentStatus(
            name="test-deployment",
            status="Succeeded",
            timestamp=now
        )
        
        result = DeploymentResult(
            deployment_name="test-deployment",
            status=status,
            outputs={"storage_name": "teststorage123"},
            operation_id="op-123",
            duration=timedelta(minutes=5),
            deployed_resources=["storage-account-1", "blob-container-1"]
        )
        
        assert result.deployment_name == "test-deployment"
        assert result.status == status
        assert result.outputs == {"storage_name": "teststorage123"}
        assert result.operation_id == "op-123"
        assert result.duration == timedelta(minutes=5)
        assert result.deployed_resources == ["storage-account-1", "blob-container-1"]
    
    def test_deployment_result_minimal_creation(self):
        """Test DeploymentResult creation with minimal fields."""
        now = datetime.utcnow()
        status = DeploymentStatus(
            name="test-deployment",
            status="Failed",
            timestamp=now
        )
        
        result = DeploymentResult(
            deployment_name="test-deployment",
            status=status
        )
        
        assert result.deployment_name == "test-deployment"
        assert result.status == status
        assert result.outputs is None
        assert result.operation_id is None
        assert result.duration is None
        assert result.deployed_resources == []


class TestAzureAuthenticator:
    """Test cases for AzureAuthenticator class."""
    
    @patch('src.deployers.azure.get_settings')
    def test_azure_authenticator_initialization(self, mock_get_settings):
        """Test AzureAuthenticator initialization."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        authenticator = AzureAuthenticator()
        
        assert authenticator.credential is None
        assert authenticator._authenticated is False
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.ClientSecretCredential')
    def test_authenticate_service_principal_success(self, mock_credential_class, mock_get_settings):
        """Test successful service principal authentication."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.get_auth_method.return_value = "service_principal"
        mock_settings.azure.tenant_id = "tenant-123"
        mock_settings.azure.client_id = "client-123"
        mock_settings.azure.client_secret = "secret-123"
        mock_get_settings.return_value = mock_settings
        
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        authenticator = AzureAuthenticator()
        
        result = authenticator.authenticate()
        
        assert result is True
        assert authenticator._authenticated is True
        assert authenticator.credential == mock_credential
        mock_credential_class.assert_called_once_with(
            tenant_id="tenant-123",
            client_id="client-123",
            client_secret="secret-123"
        )
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.AzureCliCredential')
    def test_authenticate_azure_cli_success(self, mock_credential_class, mock_get_settings):
        """Test successful Azure CLI authentication."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.get_auth_method.return_value = "azure_cli"
        mock_get_settings.return_value = mock_settings
        
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        authenticator = AzureAuthenticator()
        
        result = authenticator.authenticate()
        
        assert result is True
        assert authenticator._authenticated is True
        assert authenticator.credential == mock_credential
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.DefaultAzureCredential')
    def test_authenticate_default_credential_success(self, mock_credential_class, mock_get_settings):
        """Test successful default credential authentication."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.get_auth_method.return_value = "none"
        mock_get_settings.return_value = mock_settings
        
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        authenticator = AzureAuthenticator()
        
        result = authenticator.authenticate()
        
        assert result is True
        assert authenticator._authenticated is True
        assert authenticator.credential == mock_credential
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.DefaultAzureCredential')
    def test_authenticate_failure(self, mock_credential_class, mock_get_settings):
        """Test authentication failure."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.get_auth_method.return_value = "none"
        mock_get_settings.return_value = mock_settings
        
        mock_credential = Mock()
        mock_credential.get_token.side_effect = Exception("Auth failed")
        mock_credential_class.return_value = mock_credential
        
        authenticator = AzureAuthenticator()
        
        result = authenticator.authenticate()
        
        assert result is False
        assert authenticator._authenticated is False
    
    @patch('src.deployers.azure.get_settings')
    def test_is_authenticated_true(self, mock_get_settings):
        """Test is_authenticated returns True when authenticated."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        authenticator = AzureAuthenticator()
        authenticator._authenticated = True
        
        assert authenticator.is_authenticated() is True
    
    @patch('src.deployers.azure.get_settings')
    def test_is_authenticated_false(self, mock_get_settings):
        """Test is_authenticated returns False when not authenticated."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        authenticator = AzureAuthenticator()
        
        assert authenticator.is_authenticated() is False
    
    @patch('src.deployers.azure.get_settings')
    def test_get_credential_authenticated(self, mock_get_settings):
        """Test get_credential when authenticated."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        authenticator = AzureAuthenticator()
        mock_credential = Mock()
        authenticator.credential = mock_credential
        authenticator._authenticated = True
        
        credential = authenticator.get_credential()
        
        assert credential == mock_credential
    
    @patch('src.deployers.azure.get_settings')
    def test_get_credential_not_authenticated(self, mock_get_settings):
        """Test get_credential when not authenticated."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        authenticator = AzureAuthenticator()
        
        with patch.object(authenticator, 'authenticate', return_value=False):
            credential = authenticator.get_credential()
            
            assert credential is None


class TestAzureDeployer:
    """Test cases for AzureDeployer class."""
    
    @patch('src.deployers.azure.get_settings')
    def test_azure_deployer_initialization_success(self, mock_get_settings):
        """Test successful AzureDeployer initialization."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        assert deployer.subscription_id == "sub-123"
        assert deployer.client is None
        assert isinstance(deployer.authenticator, AzureAuthenticator)
    
    @patch('src.deployers.azure.get_settings')
    def test_azure_deployer_initialization_custom_subscription(self, mock_get_settings):
        """Test AzureDeployer initialization with custom subscription."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer(subscription_id="custom-sub-123")
        
        assert deployer.subscription_id == "custom-sub-123"
    
    @patch('src.deployers.azure.get_settings')
    def test_azure_deployer_initialization_no_subscription_failure(self, mock_get_settings):
        """Test AzureDeployer initialization without subscription fails."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = None
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(ValueError, match="Azure subscription ID must be provided"):
            AzureDeployer()
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.ResourceManagementClient')
    def test_ensure_authenticated_success(self, mock_client_class, mock_get_settings):
        """Test successful authentication and client initialization."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock authenticator
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        deployer.authenticator.get_credential = Mock(return_value="mock-credential")
        
        deployer._ensure_authenticated()
        
        mock_client_class.assert_called_once_with("mock-credential", "sub-123")
        assert deployer.client is not None
    
    @patch('src.deployers.azure.get_settings')
    def test_ensure_authenticated_failure(self, mock_get_settings):
        """Test authentication failure."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock authenticator failure
        deployer.authenticator.is_authenticated = Mock(return_value=False)
        deployer.authenticator.authenticate = Mock(return_value=False)
        
        with pytest.raises(Exception, match="Failed to authenticate with Azure"):
            deployer._ensure_authenticated()
    
    @patch('src.deployers.azure.get_settings')
    def test_ensure_resource_group_exists_already_exists(self, mock_get_settings):
        """Test resource group existence check when it already exists."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock client and authenticator
        mock_rg = Mock()
        mock_client = Mock()
        mock_client.resource_groups.get.return_value = mock_rg
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        result = deployer.ensure_resource_group_exists("test-rg", "East US")
        
        assert result is True
        mock_client.resource_groups.get.assert_called_once_with("test-rg")
    
    @patch('src.deployers.azure.get_settings')
    def test_ensure_resource_group_exists_create_new(self, mock_get_settings):
        """Test resource group creation when it doesn't exist."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock client and authenticator
        from azure.core.exceptions import ResourceNotFoundError
        mock_client = Mock()
        mock_client.resource_groups.get.side_effect = ResourceNotFoundError("Not found")
        mock_client.resource_groups.create_or_update.return_value = Mock()
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        result = deployer.ensure_resource_group_exists("test-rg", "East US")
        
        assert result is True
        mock_client.resource_groups.create_or_update.assert_called_once()
        args, kwargs = mock_client.resource_groups.create_or_update.call_args
        assert args[0] == "test-rg"
        assert args[1]["location"] == "East US"
    
    @patch('src.deployers.azure.get_settings')
    def test_format_parameters_success(self, mock_get_settings):
        """Test parameter formatting for ARM deployment."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Test raw parameters
        raw_params = {
            "storageAccountName": "teststorage",
            "location": "East US"
        }
        
        formatted = deployer._format_parameters(raw_params)
        
        expected = {
            "storageAccountName": {"value": "teststorage"},
            "location": {"value": "East US"}
        }
        assert formatted == expected
    
    @patch('src.deployers.azure.get_settings')
    def test_format_parameters_already_formatted(self, mock_get_settings):
        """Test parameter formatting with already formatted parameters."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Test already formatted parameters
        formatted_params = {
            "storageAccountName": {"value": "teststorage"},
            "location": {"value": "East US"}
        }
        
        result = deployer._format_parameters(formatted_params)
        
        assert result == formatted_params
    
    @patch('src.deployers.azure.get_settings')
    def test_get_deployment_status_success(self, mock_get_settings):
        """Test successful deployment status retrieval."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock deployment object
        mock_properties = Mock()
        mock_properties.provisioning_state = "Succeeded"
        mock_properties.correlation_id = "corr-123"
        mock_properties.timestamp = datetime.utcnow()
        mock_properties.error = None
        
        mock_deployment = Mock()
        mock_deployment.properties = mock_properties
        
        mock_client = Mock()
        mock_client.deployments.get.return_value = mock_deployment
        deployer.client = mock_client
        
        status = deployer._get_deployment_status("test-deployment", "test-rg")
        
        assert isinstance(status, DeploymentStatus)
        assert status.name == "test-deployment"
        assert status.status == "Succeeded"
        assert status.correlation_id == "corr-123"
        assert status.provisioning_state == "Succeeded"
        assert status.error_message is None
    
    @patch('src.deployers.azure.get_settings')
    def test_get_deployment_status_with_error(self, mock_get_settings):
        """Test deployment status retrieval with error."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock deployment object with error
        mock_error = Mock()
        mock_error.message = "Deployment failed"
        
        mock_properties = Mock()
        mock_properties.provisioning_state = "Failed"
        mock_properties.correlation_id = "corr-123"
        mock_properties.timestamp = datetime.utcnow()
        mock_properties.error = mock_error
        
        mock_deployment = Mock()
        mock_deployment.properties = mock_properties
        
        mock_client = Mock()
        mock_client.deployments.get.return_value = mock_deployment
        deployer.client = mock_client
        
        status = deployer._get_deployment_status("test-deployment", "test-rg")
        
        assert status.provisioning_state == "Failed"
        assert status.error_message == "Deployment failed"
    
    @patch('src.deployers.azure.get_settings')
    def test_get_deployed_resources_success(self, mock_get_settings):
        """Test successful deployed resources retrieval."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock deployment operations
        mock_resource1 = Mock()
        mock_resource1.resource_name = "storage-account-1"
        
        mock_resource2 = Mock()
        mock_resource2.resource_name = "blob-container-1"
        
        mock_operation1 = Mock()
        mock_operation1.properties.target_resource = mock_resource1
        
        mock_operation2 = Mock()
        mock_operation2.properties.target_resource = mock_resource2
        
        mock_client = Mock()
        mock_client.deployment_operations.list.return_value = [mock_operation1, mock_operation2]
        deployer.client = mock_client
        
        resources = deployer._get_deployed_resources("test-deployment", "test-rg")
        
        assert resources == ["storage-account-1", "blob-container-1"]
    
    @patch('src.deployers.azure.get_settings')
    def test_validate_template_success(self, mock_get_settings):
        """Test successful template validation."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock validation result
        mock_result = Mock()
        mock_result.error = None
        
        mock_client = Mock()
        mock_client.deployments.validate.return_value = mock_result
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        template = {"$schema": "test", "resources": []}
        parameters = {"param1": "value1"}
        
        result = deployer.validate_template("test-rg", template, parameters)
        
        assert result is True
    
    @patch('src.deployers.azure.get_settings')
    def test_validate_template_failure(self, mock_get_settings):
        """Test template validation failure."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        # Mock validation result with error
        mock_error = Mock()
        mock_error.message = "Template is invalid"
        
        mock_result = Mock()
        mock_result.error = mock_error
        
        mock_client = Mock()
        mock_client.deployments.validate.return_value = mock_result
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        template = {"$schema": "test", "resources": []}
        
        result = deployer.validate_template("test-rg", template)
        
        assert result is False
    
    @patch('src.deployers.azure.get_settings')
    def test_delete_deployment_success(self, mock_get_settings):
        """Test successful deployment deletion."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        mock_client = Mock()
        mock_client.deployments.delete.return_value = None
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        result = deployer.delete_deployment("test-deployment", "test-rg")
        
        assert result is True
        mock_client.deployments.delete.assert_called_once_with("test-rg", "test-deployment")
    
    @patch('src.deployers.azure.get_settings')
    def test_delete_deployment_failure(self, mock_get_settings):
        """Test deployment deletion failure."""
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_get_settings.return_value = mock_settings
        
        deployer = AzureDeployer()
        
        mock_client = Mock()
        mock_client.deployments.delete.side_effect = Exception("Delete failed")
        deployer.client = mock_client
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        
        result = deployer.delete_deployment("test-deployment", "test-rg")
        
        assert result is False


class TestAzureDeployerIntegration:
    """Integration tests for AzureDeployer."""
    
    @patch('src.deployers.azure.get_settings')
    @patch('src.deployers.azure.ResourceManagementClient')
    def test_deploy_template_success_flow(self, mock_client_class, mock_get_settings):
        """Test successful deployment flow end-to-end."""
        # Setup settings mock
        mock_settings = Mock()
        mock_settings.azure.subscription_id = "sub-123"
        mock_settings.app.max_deployment_timeout = 1800
        mock_get_settings.return_value = mock_settings
        
        # Setup client mocks
        mock_deployment_operation = Mock()
        
        mock_properties = Mock()
        mock_properties.provisioning_state = "Succeeded"
        mock_properties.correlation_id = "corr-123"
        mock_properties.outputs = {"storage_name": {"value": "teststorage123"}}
        
        mock_deployment_result = Mock()
        mock_deployment_result.properties = mock_properties
        mock_deployment_operation.result.return_value = mock_deployment_result
        
        mock_client = Mock()
        mock_client.deployments.begin_create_or_update.return_value = mock_deployment_operation
        mock_client_class.return_value = mock_client
        
        deployer = AzureDeployer()
        
        # Mock authenticator
        deployer.authenticator.is_authenticated = Mock(return_value=True)
        deployer.authenticator.get_credential = Mock(return_value="mock-credential")
        
        # Mock other methods
        deployer._get_deployment_status = Mock(return_value=DeploymentStatus(
            name="test-deployment",
            status="Succeeded",
            timestamp=datetime.utcnow(),
            provisioning_state="Succeeded"
        ))
        deployer._get_deployed_resources = Mock(return_value=["storage-account-1"])
        
        template = {"$schema": "test", "resources": []}
        parameters = {"storageAccountName": "teststorage"}
        
        result = deployer.deploy_template("test-deployment", "test-rg", template, parameters)
        
        assert isinstance(result, DeploymentResult)
        assert result.deployment_name == "test-deployment"
        assert result.status.status == "Succeeded"
        assert result.outputs == {"storage_name": "teststorage123"}
        assert result.deployed_resources == ["storage-account-1"]