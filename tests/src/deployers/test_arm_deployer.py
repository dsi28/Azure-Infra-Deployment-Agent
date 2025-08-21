"""
Unit tests for ARM deployment functionality.

Tests cover deployment validation, execution, rollback, and error handling scenarios.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from azure.mgmt.resource.resources.models import DeploymentMode, DeploymentProperties

from src.deployers.arm_deployer import (
    ARMDeployer,
    DeploymentConfig,
    ValidationResult,
    RollbackConfig,
    create_arm_deployer,
)
from src.deployers.deployment_monitor import DeploymentStatus, DeploymentResult
from src.auth.azure_auth import AuthenticationResult, AuthenticationMethod


class TestDeploymentConfig:
    """Test DeploymentConfig model."""
    
    def test_deployment_config_creation(self):
        """Test creating a deployment configuration."""
        template = {"resources": []}
        parameters = {"param1": "value1"}
        
        config = DeploymentConfig(
            deployment_name="test-deployment",
            resource_group_name="test-rg",
            location="East US",
            template=template,
            parameters=parameters,
            mode="Incremental",
            timeout_minutes=45
        )
        
        assert config.deployment_name == "test-deployment"
        assert config.resource_group_name == "test-rg"
        assert config.location == "East US"
        assert config.template == template
        assert config.parameters == parameters
        assert config.mode == "Incremental"
        assert config.timeout_minutes == 45
        
    def test_deployment_config_defaults(self):
        """Test deployment configuration with default values."""
        config = DeploymentConfig(
            deployment_name="test",
            resource_group_name="test-rg",
            location="East US",
            template={}
        )
        
        assert config.parameters == {}
        assert config.mode == "Incremental"
        assert config.tags == {}
        assert config.timeout_minutes == 30


class TestValidationResult:
    """Test ValidationResult model."""
    
    def test_validation_success(self):
        """Test successful validation result."""
        result = ValidationResult(
            is_valid=True,
            resource_count=3,
            warnings=["No outputs section"]
        )
        
        assert result.is_valid is True
        assert result.error_message is None
        assert result.resource_count == 3
        assert len(result.warnings) == 1
        
    def test_validation_failure(self):
        """Test failed validation result."""
        result = ValidationResult(
            is_valid=False,
            error_message="Invalid template syntax"
        )
        
        assert result.is_valid is False
        assert result.error_message == "Invalid template syntax"
        assert result.resource_count == 0


class TestRollbackConfig:
    """Test RollbackConfig model."""
    
    def test_rollback_config_defaults(self):
        """Test rollback configuration with defaults."""
        config = RollbackConfig()
        
        assert config.target_deployment_name is None
        assert config.delete_resources is False
        assert config.preserve_data is True
        assert config.rollback_timeout_minutes == 15


class TestARMDeployer:
    """Test ARMDeployer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployer = ARMDeployer()
        
    def test_factory_function(self):
        """Test the factory function creates a deployer."""
        deployer = create_arm_deployer("test-subscription")
        assert isinstance(deployer, ARMDeployer)
        assert deployer.subscription_id == "test-subscription"
        
    @patch('src.deployers.arm_deployer.AzureAuthenticator')
    def test_ensure_authenticated_success(self, mock_authenticator_class):
        """Test successful authentication setup."""
        # Mock authenticator
        mock_authenticator = Mock()
        mock_auth_result = AuthenticationResult(
            success=True,
            method=AuthenticationMethod.AZURE_CLI,
            subscription_id="test-sub",
            credential=Mock()
        )
        mock_authenticator.authenticate.return_value = mock_auth_result
        mock_authenticator_class.return_value = mock_authenticator
        
        # Mock ResourceManagementClient
        with patch('src.deployers.arm_deployer.ResourceManagementClient') as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            self.deployer._ensure_authenticated()
            
            assert self.deployer._auth_result == mock_auth_result
            assert self.deployer.subscription_id == "test-sub"
            assert self.deployer.client == mock_client_instance
            
    @patch('src.deployers.arm_deployer.AzureAuthenticator')
    def test_ensure_authenticated_failure(self, mock_authenticator_class):
        """Test authentication failure."""
        mock_authenticator = Mock()
        mock_auth_result = AuthenticationResult(
            success=False,
            error_message="Auth failed"
        )
        mock_authenticator.authenticate.return_value = mock_auth_result
        mock_authenticator_class.return_value = mock_authenticator
        
        with pytest.raises(Exception, match="Failed to authenticate with Azure"):
            self.deployer._ensure_authenticated()
            
    def test_validate_template_success(self):
        """Test successful template validation."""
        config = DeploymentConfig(
            deployment_name="test",
            resource_group_name="test-rg",
            location="East US",
            template={"resources": [{"type": "Microsoft.Storage/storageAccounts"}]}
        )
        
        # Mock successful authentication
        with patch.object(self.deployer, '_ensure_authenticated'):
            # Mock client validation
            mock_client = Mock()
            mock_validation_result = Mock()
            mock_validation_result.error = None
            mock_client.deployments.validate.return_value = mock_validation_result
            self.deployer.client = mock_client
            
            result = self.deployer.validate_template(config)
            
            assert result.is_valid is True
            assert result.resource_count == 1
            assert "No outputs section" in result.warnings
            
    def test_validate_template_failure(self):
        """Test template validation failure."""
        config = DeploymentConfig(
            deployment_name="test",
            resource_group_name="test-rg", 
            location="East US",
            template={}
        )
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_validation_result = Mock()
            mock_error = Mock()
            mock_error.message = "Invalid template"
            mock_validation_result.error = mock_error
            mock_client.deployments.validate.return_value = mock_validation_result
            self.deployer.client = mock_client
            
            result = self.deployer.validate_template(config)
            
            assert result.is_valid is False
            assert result.error_message == "Invalid template"
            
    def test_ensure_resource_group_exists_already_exists(self):
        """Test resource group existence check when RG already exists."""
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_rg = Mock()
            mock_client.resource_groups.get.return_value = mock_rg
            self.deployer.client = mock_client
            
            result = self.deployer.ensure_resource_group_exists("existing-rg", "East US")
            
            assert result is True
            mock_client.resource_groups.get.assert_called_once_with("existing-rg")
            
    def test_ensure_resource_group_create_new(self):
        """Test creating a new resource group."""
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_client.resource_groups.get.side_effect = ResourceNotFoundError("Not found")
            mock_client.resource_groups.create_or_update.return_value = Mock()
            self.deployer.client = mock_client
            
            result = self.deployer.ensure_resource_group_exists("new-rg", "East US", {"env": "test"})
            
            assert result is True
            mock_client.resource_groups.create_or_update.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_client.resource_groups.create_or_update.call_args
            assert call_args[0][0] == "new-rg"  # resource group name
            rg_params = call_args[0][1]
            assert rg_params["location"] == "East US"
            assert "env" in rg_params["tags"]
            assert "created_by" in rg_params["tags"]
            
    @patch('src.deployers.arm_deployer.DeploymentMonitor')
    def test_deploy_success(self, mock_monitor_class):
        """Test successful deployment."""
        config = DeploymentConfig(
            deployment_name="test-deploy",
            resource_group_name="test-rg",
            location="East US",
            template={"resources": []},
            parameters={"param1": "value1"}
        )
        
        # Mock deployment result
        mock_result = DeploymentResult(
            deployment_name="test-deploy",
            status=DeploymentStatus(
                name="test-deploy",
                status="Succeeded",
                timestamp=datetime.utcnow(),
                provisioning_state="Succeeded"
            )
        )
        
        # Mock monitor
        mock_monitor = Mock()
        mock_monitor.monitor_deployment.return_value = mock_result
        mock_monitor_class.return_value = mock_monitor
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            with patch.object(self.deployer, 'ensure_resource_group_exists', return_value=True):
                mock_client = Mock()
                mock_operation = Mock()
                mock_client.deployments.begin_create_or_update.return_value = mock_operation
                self.deployer.client = mock_client
                
                result = self.deployer.deploy(config)
                
                assert result.deployment_name == "test-deploy"
                assert result.status.provisioning_state == "Succeeded"
                
    def test_deploy_resource_group_creation_fails(self):
        """Test deployment when resource group creation fails."""
        config = DeploymentConfig(
            deployment_name="test-deploy",
            resource_group_name="test-rg",
            location="East US",
            template={}
        )
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            with patch.object(self.deployer, 'ensure_resource_group_exists', return_value=False):
                result = self.deployer.deploy(config)
                
                assert result.status.provisioning_state == "Failed"
                assert "Failed to ensure resource group exists" in result.status.error_message
                
    def test_rollback_deployment_by_deletion(self):
        """Test rollback by deletion."""
        config = RollbackConfig(delete_resources=True)
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            with patch.object(self.deployer, '_get_deployed_resources', return_value=["resource1", "resource2"]):
                with patch.object(self.deployer, '_delete_deployment_resources'):
                    mock_client = Mock()
                    mock_client.deployments.delete.return_value = None
                    self.deployer.client = mock_client
                    
                    result = self.deployer.rollback_deployment("test-deploy", "test-rg", config)
                    
                    assert result.status.provisioning_state == "Succeeded"
                    assert result.deployment_name == "rollback-test-deploy"
                    
    def test_rollback_deployment_to_previous(self):
        """Test rollback to previous deployment."""
        config = RollbackConfig(target_deployment_name="previous-deploy")
        
        # Mock previous deployment
        mock_previous_deployment = Mock()
        mock_properties = Mock()
        mock_properties.template = {"resources": []}
        mock_properties.parameters = {"param1": {"value": "old_value"}}
        mock_previous_deployment.properties = mock_properties
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            with patch.object(self.deployer, 'deploy') as mock_deploy:
                mock_client = Mock()
                mock_client.deployments.get.return_value = mock_previous_deployment
                self.deployer.client = mock_client
                
                # Mock successful rollback deployment
                mock_rollback_result = DeploymentResult(
                    deployment_name="rollback-12345678",
                    status=DeploymentStatus(
                        name="rollback-12345678",
                        status="Succeeded",
                        timestamp=datetime.utcnow(),
                        provisioning_state="Succeeded"
                    )
                )
                mock_deploy.return_value = mock_rollback_result
                
                result = self.deployer.rollback_deployment("current-deploy", "test-rg", config)
                
                assert result.status.provisioning_state == "Succeeded"
                mock_deploy.assert_called_once()
                
    def test_get_deployment_history(self):
        """Test getting deployment history."""
        # Mock deployment objects
        mock_deployment1 = Mock()
        mock_deployment1.name = "deploy-1"
        mock_deployment1.properties.timestamp = datetime.utcnow()
        mock_deployment1.properties.provisioning_state = "Succeeded"
        mock_deployment1.properties.mode = DeploymentMode.incremental
        mock_deployment1.properties.correlation_id = "corr-1"
        
        mock_deployment2 = Mock()
        mock_deployment2.name = "deploy-2"
        mock_deployment2.properties.timestamp = datetime.utcnow() - timedelta(hours=1)
        mock_deployment2.properties.provisioning_state = "Failed"
        mock_deployment2.properties.mode = DeploymentMode.incremental
        mock_deployment2.properties.correlation_id = "corr-2"
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_client.deployments.list_by_resource_group.return_value = [mock_deployment1, mock_deployment2]
            self.deployer.client = mock_client
            
            history = self.deployer.get_deployment_history("test-rg", limit=5)
            
            assert len(history) == 2
            assert history[0]["name"] == "deploy-1"
            assert history[0]["provisioning_state"] == "Succeeded"
            assert history[1]["name"] == "deploy-2"
            assert history[1]["provisioning_state"] == "Failed"
            
    def test_format_parameters(self):
        """Test parameter formatting for ARM templates."""
        # Test raw parameters
        raw_params = {"param1": "value1", "param2": 123}
        formatted = self.deployer._format_parameters(raw_params)
        
        assert formatted["param1"] == {"value": "value1"}
        assert formatted["param2"] == {"value": 123}
        
        # Test already formatted parameters
        arm_params = {"param1": {"value": "value1"}, "param2": {"value": 123}}
        formatted = self.deployer._format_parameters(arm_params)
        
        assert formatted == arm_params
        
    def test_extract_parameters(self):
        """Test extracting parameters from ARM format."""
        arm_params = {
            "param1": {"value": "value1"},
            "param2": {"value": 123},
            "param3": "direct_value"  # Non-ARM format
        }
        
        extracted = self.deployer._extract_parameters(arm_params)
        
        assert extracted["param1"] == "value1"
        assert extracted["param2"] == 123
        assert extracted["param3"] == "direct_value"
        
    def test_count_template_resources(self):
        """Test counting resources in ARM template."""
        template = {
            "resources": [
                {"type": "Microsoft.Storage/storageAccounts"},
                {"type": "Microsoft.Web/sites"},
                {"type": "Microsoft.Web/serverfarms"}
            ]
        }
        
        count = self.deployer._count_template_resources(template)
        assert count == 3
        
        # Test empty template
        empty_template = {}
        count = self.deployer._count_template_resources(empty_template)
        assert count == 0
        
    def test_analyze_template_warnings(self):
        """Test template analysis for warnings."""
        # Template with potential issues
        template = {
            "resources": [{"type": "Microsoft.Storage/storageAccounts"}],
            "variables": {"adminPassword": "hardcoded123"}
        }
        
        warnings = self.deployer._analyze_template_warnings(template)
        
        assert any("no parameters section" in warning.lower() for warning in warnings)
        assert any("no outputs section" in warning.lower() for warning in warnings)
        assert any("hardcoded passwords" in warning.lower() for warning in warnings)
        
    def test_get_deployed_resources(self):
        """Test getting deployed resources from operations."""
        mock_operation1 = Mock()
        mock_operation1.properties.target_resource.resource_name = "storage1"
        
        mock_operation2 = Mock()
        mock_operation2.properties.target_resource.resource_name = "webapp1"
        
        mock_operation3 = Mock()
        mock_operation3.properties.target_resource = None  # No target resource
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_client.deployment_operations.list.return_value = [
                mock_operation1, mock_operation2, mock_operation3
            ]
            self.deployer.client = mock_client
            
            resources = self.deployer._get_deployed_resources("test-deploy", "test-rg")
            
            assert "storage1" in resources
            assert "webapp1" in resources
            assert len(resources) == 2


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployer = ARMDeployer()
        
    def test_deploy_with_exception(self):
        """Test deployment when an exception occurs."""
        config = DeploymentConfig(
            deployment_name="test-deploy",
            resource_group_name="test-rg",
            location="East US",
            template={}
        )
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            with patch.object(self.deployer, 'ensure_resource_group_exists', return_value=True):
                mock_client = Mock()
                mock_client.deployments.begin_create_or_update.side_effect = Exception("Deployment failed")
                self.deployer.client = mock_client
                
                result = self.deployer.deploy(config)
                
                assert result.status.provisioning_state == "Failed"
                assert "Deployment failed" in result.status.error_message
                
    def test_rollback_with_exception(self):
        """Test rollback when an exception occurs."""
        config = RollbackConfig()
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_client.deployments.delete.side_effect = Exception("Delete failed")
            self.deployer.client = mock_client
            
            result = self.deployer.rollback_deployment("test-deploy", "test-rg", config)
            
            assert result.status.provisioning_state == "Failed"
            assert "Rollback failed" in result.status.error_message
            
    def test_validation_with_exception(self):
        """Test template validation when an exception occurs."""
        config = DeploymentConfig(
            deployment_name="test",
            resource_group_name="test-rg",
            location="East US", 
            template={}
        )
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            mock_client = Mock()
            mock_client.deployments.validate.side_effect = Exception("Validation error")
            self.deployer.client = mock_client
            
            result = self.deployer.validate_template(config)
            
            assert result.is_valid is False
            assert "Validation error" in result.error_message


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployer = ARMDeployer("test-subscription")
        
    def test_full_deployment_workflow(self):
        """Test complete deployment workflow from validation to completion."""
        template = {
            "parameters": {"storageAccountName": {"type": "string"}},
            "resources": [{"type": "Microsoft.Storage/storageAccounts"}],
            "outputs": {"storageAccountId": {"type": "string", "value": "[resourceId('Microsoft.Storage/storageAccounts', parameters('storageAccountName'))]"}}
        }
        
        config = DeploymentConfig(
            deployment_name="storage-deploy",
            resource_group_name="test-rg",
            location="East US",
            template=template,
            parameters={"storageAccountName": "teststorage123"}
        )
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            # Mock successful validation
            with patch.object(self.deployer.client, 'deployments') as mock_deployments:
                mock_validation_result = Mock()
                mock_validation_result.error = None
                mock_deployments.validate.return_value = mock_validation_result
                
                validation_result = self.deployer.validate_template(config)
                
                assert validation_result.is_valid is True
                assert validation_result.resource_count == 1
                assert len(validation_result.warnings) == 0  # Template has parameters and outputs
                
    def test_deployment_with_rollback_scenario(self):
        """Test deployment failure followed by rollback."""
        config = DeploymentConfig(
            deployment_name="failed-deploy",
            resource_group_name="test-rg",
            location="East US",
            template={"resources": []}
        )
        
        rollback_config = RollbackConfig(delete_resources=True)
        
        with patch.object(self.deployer, '_ensure_authenticated'):
            # Simulate failed deployment
            with patch.object(self.deployer, 'ensure_resource_group_exists', return_value=True):
                with patch.object(self.deployer, '_get_deployed_resources', return_value=["failed-resource"]):
                    mock_client = Mock()
                    mock_client.deployments.delete.return_value = None
                    self.deployer.client = mock_client
                    
                    # Perform rollback
                    rollback_result = self.deployer.rollback_deployment("failed-deploy", "test-rg", rollback_config)
                    
                    assert rollback_result.status.provisioning_state == "Succeeded"
                    assert rollback_result.deployment_name == "rollback-failed-deploy"