"""
Unit tests for deployment monitoring functionality.

Tests cover real-time monitoring, progress tracking, and callback mechanisms.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from azure.core.polling import LROPoller
from azure.mgmt.resource import ResourceManagementClient

from src.deployers.deployment_monitor import (
    DeploymentMonitor,
    DeploymentStatus,
    DeploymentResult,
    DeploymentOperation,
    DeploymentProgressCallback,
    ConsoleProgressCallback,
    DeploymentState,
    OperationStatus,
    create_deployment_monitor,
)


class TestDeploymentStatus:
    """Test DeploymentStatus model."""
    
    def test_deployment_status_creation(self):
        """Test creating a deployment status."""
        timestamp = datetime.utcnow()
        status = DeploymentStatus(
            name="test-deploy",
            status="Running",
            correlation_id="corr-123",
            timestamp=timestamp,
            provisioning_state="Accepted",
            resource_count=5,
            completed_operations=2,
            failed_operations=0,
            progress_percentage=40.0
        )
        
        assert status.name == "test-deploy"
        assert status.status == "Running"
        assert status.correlation_id == "corr-123"
        assert status.timestamp == timestamp
        assert status.provisioning_state == "Accepted"
        assert status.resource_count == 5
        assert status.completed_operations == 2
        assert status.failed_operations == 0
        assert status.progress_percentage == 40.0
        
    def test_deployment_status_defaults(self):
        """Test deployment status with default values."""
        status = DeploymentStatus(
            name="test",
            status="Unknown",
            timestamp=datetime.utcnow()
        )
        
        assert status.correlation_id is None
        assert status.provisioning_state is None
        assert status.error_message is None
        assert status.resource_count == 0
        assert status.completed_operations == 0
        assert status.failed_operations == 0
        assert status.progress_percentage == 0.0


class TestDeploymentOperation:
    """Test DeploymentOperation model."""
    
    def test_deployment_operation_creation(self):
        """Test creating a deployment operation."""
        timestamp = datetime.utcnow()
        duration = timedelta(minutes=2)
        
        operation = DeploymentOperation(
            operation_id="op-123",
            resource_name="storage-account-1",
            resource_type="Microsoft.Storage/storageAccounts",
            operation_status="Succeeded",
            timestamp=timestamp,
            duration=duration
        )
        
        assert operation.operation_id == "op-123"
        assert operation.resource_name == "storage-account-1"
        assert operation.resource_type == "Microsoft.Storage/storageAccounts"
        assert operation.operation_status == "Succeeded"
        assert operation.timestamp == timestamp
        assert operation.duration == duration
        
    def test_deployment_operation_defaults(self):
        """Test deployment operation with default values."""
        operation = DeploymentOperation(
            operation_id="op-123",
            operation_status="InProgress",
            timestamp=datetime.utcnow()
        )
        
        assert operation.resource_name is None
        assert operation.resource_type is None
        assert operation.error_message is None
        assert operation.duration is None


class TestDeploymentResult:
    """Test DeploymentResult model."""
    
    def test_deployment_result_creation(self):
        """Test creating a deployment result."""
        status = DeploymentStatus(
            name="test-deploy",
            status="Succeeded",
            timestamp=datetime.utcnow(),
            provisioning_state="Succeeded"
        )
        
        operations = [
            DeploymentOperation(
                operation_id="op-1",
                resource_name="resource-1",
                operation_status="Succeeded",
                timestamp=datetime.utcnow()
            )
        ]
        
        result = DeploymentResult(
            deployment_name="test-deploy",
            status=status,
            outputs={"output1": "value1"},
            operation_id="main-op-123",
            duration=timedelta(minutes=5),
            deployed_resources=["resource-1"],
            operations=operations
        )
        
        assert result.deployment_name == "test-deploy"
        assert result.status == status
        assert result.outputs == {"output1": "value1"}
        assert result.operation_id == "main-op-123"
        assert result.duration == timedelta(minutes=5)
        assert result.deployed_resources == ["resource-1"]
        assert len(result.operations) == 1
        
    def test_deployment_result_defaults(self):
        """Test deployment result with default values."""
        status = DeploymentStatus(
            name="test",
            status="Unknown",
            timestamp=datetime.utcnow()
        )
        
        result = DeploymentResult(
            deployment_name="test",
            status=status
        )
        
        assert result.outputs is None
        assert result.operation_id is None
        assert result.duration is None
        assert result.deployed_resources == []
        assert result.operations == []
        assert result.error_details is None


class MockProgressCallback(DeploymentProgressCallback):
    """Mock callback for testing."""
    
    def __init__(self):
        self.progress_updates = []
        self.completed_operations = []
        self.deployment_complete = None
        
    def on_progress_update(self, status: DeploymentStatus) -> None:
        self.progress_updates.append(status)
        
    def on_operation_complete(self, operation: DeploymentOperation) -> None:
        self.completed_operations.append(operation)
        
    def on_deployment_complete(self, result: DeploymentResult) -> None:
        self.deployment_complete = result


class TestConsoleProgressCallback:
    """Test ConsoleProgressCallback."""
    
    def test_progress_update_logging(self, caplog):
        """Test progress update logging."""
        callback = ConsoleProgressCallback()
        status = DeploymentStatus(
            name="test-deploy",
            status="Running",
            timestamp=datetime.utcnow(),
            resource_count=5,
            completed_operations=2,
            progress_percentage=40.0
        )
        
        callback.on_progress_update(status)
        
        assert "test-deploy" in caplog.text
        assert "40.0%" in caplog.text
        assert "2/5" in caplog.text
        
    def test_operation_complete_success_logging(self, caplog):
        """Test successful operation completion logging."""
        callback = ConsoleProgressCallback()
        operation = DeploymentOperation(
            operation_id="op-1",
            resource_name="storage-1",
            resource_type="Microsoft.Storage/storageAccounts",
            operation_status=OperationStatus.SUCCEEDED,
            timestamp=datetime.utcnow()
        )
        
        callback.on_operation_complete(operation)
        
        assert "✅" in caplog.text
        assert "storage-1" in caplog.text
        
    def test_operation_complete_failure_logging(self, caplog):
        """Test failed operation completion logging."""
        callback = ConsoleProgressCallback()
        operation = DeploymentOperation(
            operation_id="op-1",
            resource_name="storage-1",
            resource_type="Microsoft.Storage/storageAccounts",
            operation_status=OperationStatus.FAILED,
            timestamp=datetime.utcnow(),
            error_message="Storage account name already exists"
        )
        
        callback.on_operation_complete(operation)
        
        assert "❌" in caplog.text
        assert "storage-1" in caplog.text
        assert "already exists" in caplog.text
        
    def test_deployment_complete_success_logging(self, caplog):
        """Test successful deployment completion logging."""
        callback = ConsoleProgressCallback()
        status = DeploymentStatus(
            name="test-deploy",
            status="Succeeded",
            timestamp=datetime.utcnow(),
            provisioning_state=DeploymentState.SUCCEEDED
        )
        result = DeploymentResult(deployment_name="test-deploy", status=status)
        
        callback.on_deployment_complete(result)
        
        assert "🎉" in caplog.text
        assert "test-deploy" in caplog.text
        assert "successfully" in caplog.text
        
    def test_deployment_complete_failure_logging(self, caplog):
        """Test failed deployment completion logging."""
        callback = ConsoleProgressCallback()
        status = DeploymentStatus(
            name="test-deploy",
            status="Failed",
            timestamp=datetime.utcnow(),
            provisioning_state=DeploymentState.FAILED,
            error_message="Template validation failed"
        )
        result = DeploymentResult(deployment_name="test-deploy", status=status)
        
        callback.on_deployment_complete(result)
        
        assert "💥" in caplog.text
        assert "test-deploy" in caplog.text
        assert "failed" in caplog.text


class TestDeploymentMonitor:
    """Test DeploymentMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = DeploymentMonitor(poll_interval_seconds=1)
        
    def test_factory_function(self):
        """Test the factory function creates a monitor."""
        monitor = create_deployment_monitor(poll_interval_seconds=5)
        assert isinstance(monitor, DeploymentMonitor)
        assert monitor.poll_interval == 5
        
    def test_add_progress_callback(self):
        """Test adding progress callbacks."""
        callback = MockProgressCallback()
        
        self.monitor.add_progress_callback(callback)
        
        assert callback in self.monitor._callbacks
        
    @patch('time.sleep')
    def test_monitor_deployment_success(self, mock_sleep):
        """Test successful deployment monitoring."""
        # Mock deployment operation
        mock_deployment_operation = Mock(spec=LROPoller)
        mock_deployment_operation.done.side_effect = [False, False, True]  # Complete after 3 polls
        
        # Mock final deployment result
        mock_final_deployment = Mock()
        mock_properties = Mock()
        mock_properties.outputs = {"output1": {"value": "test-value"}}
        mock_properties.correlation_id = "corr-123"
        mock_final_deployment.properties = mock_properties
        mock_deployment_operation.result.return_value = mock_final_deployment
        
        # Mock client
        mock_client = Mock(spec=ResourceManagementClient)
        
        # Mock status responses
        status_responses = [
            DeploymentStatus(
                name="test-deploy",
                status="Running",
                timestamp=datetime.utcnow(),
                provisioning_state="Running",
                resource_count=3,
                completed_operations=1,
                progress_percentage=33.3
            ),
            DeploymentStatus(
                name="test-deploy", 
                status="Running",
                timestamp=datetime.utcnow(),
                provisioning_state="Running",
                resource_count=3,
                completed_operations=2,
                progress_percentage=66.6
            ),
            DeploymentStatus(
                name="test-deploy",
                status="Succeeded",
                timestamp=datetime.utcnow(),
                provisioning_state="Succeeded",
                resource_count=3,
                completed_operations=3,
                progress_percentage=100.0
            )
        ]
        
        with patch.object(self.monitor, '_get_current_status', side_effect=status_responses):
            with patch.object(self.monitor, '_get_deployment_operations', return_value=[]):
                with patch.object(self.monitor, '_get_deployed_resource_names', return_value=["resource1", "resource2"]):
                    callback = MockProgressCallback()
                    
                    result = self.monitor.monitor_deployment(
                        deployment_operation=mock_deployment_operation,
                        deployment_name="test-deploy",
                        resource_group_name="test-rg",
                        timeout_minutes=30,
                        client=mock_client,
                        progress_callback=callback
                    )
                    
                    # Verify result
                    assert result.deployment_name == "test-deploy"
                    assert result.status.provisioning_state == "Succeeded"
                    assert result.outputs == {"output1": "test-value"}
                    assert result.operation_id == "corr-123"
                    assert result.deployed_resources == ["resource1", "resource2"]
                    
                    # Verify callback was called
                    assert len(callback.progress_updates) >= 1
                    assert callback.deployment_complete is not None
                    
    @patch('time.sleep')
    def test_monitor_deployment_timeout(self, mock_sleep):
        """Test deployment monitoring timeout."""
        # Mock deployment operation that never completes
        mock_deployment_operation = Mock(spec=LROPoller)
        mock_deployment_operation.done.return_value = False
        mock_deployment_operation.cancel.return_value = None
        
        # Mock final deployment result after timeout
        mock_final_deployment = Mock()
        mock_final_deployment.properties = None
        mock_deployment_operation.result.return_value = mock_final_deployment
        
        mock_client = Mock(spec=ResourceManagementClient)
        
        # Mock status that indicates running state
        running_status = DeploymentStatus(
            name="test-deploy",
            status="Running",
            timestamp=datetime.utcnow(),
            provisioning_state="Running"
        )
        
        with patch.object(self.monitor, '_get_current_status', return_value=running_status):
            with patch.object(self.monitor, '_get_deployment_operations', return_value=[]):
                result = self.monitor.monitor_deployment(
                    deployment_operation=mock_deployment_operation,
                    deployment_name="test-deploy", 
                    resource_group_name="test-rg",
                    timeout_minutes=0.01,  # Very short timeout for testing
                    client=mock_client
                )
                
                # Should timeout but still return a result
                assert result.deployment_name == "test-deploy"
                mock_deployment_operation.cancel.assert_called_once()
                
    def test_monitor_deployment_with_operations(self):
        """Test monitoring with individual operations tracking."""
        mock_deployment_operation = Mock(spec=LROPoller)
        mock_deployment_operation.done.side_effect = [False, True]
        
        mock_final_deployment = Mock()
        mock_final_deployment.properties = None
        mock_deployment_operation.result.return_value = mock_final_deployment
        
        mock_client = Mock(spec=ResourceManagementClient)
        
        # Mock operations
        mock_operations = [
            DeploymentOperation(
                operation_id="op-1",
                resource_name="storage-1",
                resource_type="Microsoft.Storage/storageAccounts",
                operation_status=OperationStatus.SUCCEEDED,
                timestamp=datetime.utcnow()
            ),
            DeploymentOperation(
                operation_id="op-2",
                resource_name="webapp-1", 
                resource_type="Microsoft.Web/sites",
                operation_status=OperationStatus.SUCCEEDED,
                timestamp=datetime.utcnow()
            )
        ]
        
        final_status = DeploymentStatus(
            name="test-deploy",
            status="Succeeded",
            timestamp=datetime.utcnow(),
            provisioning_state="Succeeded"
        )
        
        with patch.object(self.monitor, '_get_current_status', return_value=final_status):
            with patch.object(self.monitor, '_get_deployment_operations') as mock_get_ops:
                mock_get_ops.side_effect = [mock_operations, []]  # Return ops on first call, empty on second
                with patch.object(self.monitor, '_get_deployed_resource_names', return_value=["storage-1", "webapp-1"]):
                    callback = MockProgressCallback()
                    
                    result = self.monitor.monitor_deployment(
                        deployment_operation=mock_deployment_operation,
                        deployment_name="test-deploy",
                        resource_group_name="test-rg", 
                        timeout_minutes=30,
                        client=mock_client,
                        progress_callback=callback
                    )
                    
                    assert len(result.operations) == 2
                    assert result.deployed_resources == ["storage-1", "webapp-1"]
                    assert len(callback.completed_operations) == 2
                    
    def test_monitor_deployment_exception_handling(self):
        """Test monitoring with exception handling."""
        mock_deployment_operation = Mock(spec=LROPoller)
        mock_deployment_operation.done.side_effect = Exception("Network error")
        
        mock_client = Mock(spec=ResourceManagementClient)
        
        result = self.monitor.monitor_deployment(
            deployment_operation=mock_deployment_operation,
            deployment_name="test-deploy",
            resource_group_name="test-rg",
            timeout_minutes=30,
            client=mock_client
        )
        
        assert result.deployment_name == "test-deploy"
        assert result.status.provisioning_state is None
        assert "Deployment monitoring failed" in result.status.error_message
        
    def test_get_current_status_success(self):
        """Test getting current deployment status."""
        mock_client = Mock(spec=ResourceManagementClient)
        
        # Mock deployment object
        mock_deployment = Mock()
        mock_properties = Mock()
        mock_properties.provisioning_state = "Running"
        mock_properties.correlation_id = "corr-123"
        mock_properties.timestamp = datetime.utcnow()
        mock_properties.error = None
        mock_deployment.properties = mock_properties
        
        mock_client.deployments.get.return_value = mock_deployment
        mock_client.deployment_operations.list.return_value = [Mock(), Mock(), Mock()]  # 3 operations
        
        status = self.monitor._get_current_status("test-deploy", "test-rg", mock_client)
        
        assert status.name == "test-deploy"
        assert status.status == "Running"
        assert status.provisioning_state == "Running"
        assert status.correlation_id == "corr-123"
        assert status.resource_count == 3
        assert status.error_message is None
        
    def test_get_current_status_with_error(self):
        """Test getting deployment status when deployment has errors."""
        mock_client = Mock(spec=ResourceManagementClient)
        
        mock_deployment = Mock()
        mock_properties = Mock()
        mock_properties.provisioning_state = "Failed"
        mock_error = Mock()
        mock_error.message = "Template validation failed"
        mock_properties.error = mock_error
        mock_deployment.properties = mock_properties
        
        mock_client.deployments.get.return_value = mock_deployment
        mock_client.deployment_operations.list.return_value = []
        
        status = self.monitor._get_current_status("test-deploy", "test-rg", mock_client)
        
        assert status.status == "Failed"
        assert status.error_message == "Template validation failed"
        
    def test_get_deployment_operations(self):
        """Test getting deployment operations."""
        mock_client = Mock(spec=ResourceManagementClient)
        
        # Mock Azure deployment operations
        mock_op1 = Mock()
        mock_op1.operation_id = "op-1"
        mock_op1.properties.provisioning_state = "Succeeded"
        mock_op1.properties.timestamp = datetime.utcnow()
        mock_op1.properties.target_resource.resource_name = "storage-1"
        mock_op1.properties.target_resource.resource_type = "Microsoft.Storage/storageAccounts"
        
        mock_op2 = Mock()
        mock_op2.operation_id = "op-2"
        mock_op2.properties.provisioning_state = "InProgress"
        mock_op2.properties.timestamp = datetime.utcnow()
        mock_op2.properties.target_resource.resource_name = "webapp-1"
        mock_op2.properties.target_resource.resource_type = "Microsoft.Web/sites"
        
        mock_client.deployment_operations.list.return_value = [mock_op1, mock_op2]
        
        seen_operations = {}  # Empty seen operations
        
        new_operations = self.monitor._get_deployment_operations(
            "test-deploy", "test-rg", mock_client, seen_operations
        )
        
        assert len(new_operations) == 2
        assert new_operations[0].operation_id == "op-1"
        assert new_operations[0].resource_name == "storage-1"
        assert new_operations[0].operation_status == "Succeeded"
        assert new_operations[1].operation_id == "op-2"
        assert new_operations[1].resource_name == "webapp-1"
        assert new_operations[1].operation_status == "InProgress"
        
    def test_get_deployment_operations_skip_seen(self):
        """Test that seen operations are skipped."""
        mock_client = Mock(spec=ResourceManagementClient)
        
        mock_op1 = Mock()
        mock_op1.operation_id = "op-1"
        mock_op1.properties.provisioning_state = "Succeeded"
        mock_op1.properties.timestamp = datetime.utcnow()
        mock_op1.properties.target_resource.resource_name = "storage-1"
        mock_op1.properties.target_resource.resource_type = "Microsoft.Storage/storageAccounts"
        
        mock_client.deployment_operations.list.return_value = [mock_op1]
        
        # Mark operation as already seen
        seen_operations = {
            "op-1": DeploymentOperation(
                operation_id="op-1",
                resource_name="storage-1",
                operation_status="Succeeded",
                timestamp=datetime.utcnow()
            )
        }
        
        new_operations = self.monitor._get_deployment_operations(
            "test-deploy", "test-rg", mock_client, seen_operations
        )
        
        assert len(new_operations) == 0  # Should skip seen operation
        
    def test_get_deployed_resource_names(self):
        """Test extracting deployed resource names."""
        operations = [
            DeploymentOperation(
                operation_id="op-1",
                resource_name="storage-1",
                operation_status=OperationStatus.SUCCEEDED,
                timestamp=datetime.utcnow()
            ),
            DeploymentOperation(
                operation_id="op-2", 
                resource_name="webapp-1",
                operation_status=OperationStatus.SUCCEEDED,
                timestamp=datetime.utcnow()
            ),
            DeploymentOperation(
                operation_id="op-3",
                resource_name="failed-resource",
                operation_status=OperationStatus.FAILED,  # Should be excluded
                timestamp=datetime.utcnow()
            ),
            DeploymentOperation(
                operation_id="op-4",
                resource_name=None,  # Should be excluded
                operation_status=OperationStatus.SUCCEEDED,
                timestamp=datetime.utcnow()
            )
        ]
        
        resource_names = self.monitor._get_deployed_resource_names(operations)
        
        assert len(resource_names) == 2
        assert "storage-1" in resource_names
        assert "webapp-1" in resource_names
        assert "failed-resource" not in resource_names
        
    def test_get_deployment_error_details(self):
        """Test getting detailed error information."""
        mock_client = Mock(spec=ResourceManagementClient)
        
        mock_deployment = Mock()
        mock_properties = Mock()
        mock_error = Mock()
        mock_error.code = "InvalidTemplate"
        mock_error.message = "Template validation failed"
        mock_error.target = "parameters.storageAccountName"
        mock_error.details = [{"code": "InvalidValue", "message": "Value is too long"}]
        mock_properties.error = mock_error
        mock_deployment.properties = mock_properties
        
        mock_client.deployments.get.return_value = mock_deployment
        
        error_details = self.monitor._get_deployment_error_details("test-deploy", "test-rg", mock_client)
        
        assert error_details["code"] == "InvalidTemplate"
        assert error_details["message"] == "Template validation failed"
        assert error_details["target"] == "parameters.storageAccountName"
        assert len(error_details["details"]) == 1
        
    def test_callback_exception_handling(self):
        """Test that callback exceptions don't break monitoring."""
        # Create a callback that raises an exception
        class FailingCallback(DeploymentProgressCallback):
            def on_progress_update(self, status: DeploymentStatus) -> None:
                raise Exception("Callback failed")
                
            def on_operation_complete(self, operation: DeploymentOperation) -> None:
                raise Exception("Callback failed")
                
            def on_deployment_complete(self, result: DeploymentResult) -> None:
                raise Exception("Callback failed")
        
        failing_callback = FailingCallback()
        self.monitor.add_progress_callback(failing_callback)
        
        status = DeploymentStatus(
            name="test",
            status="Running",
            timestamp=datetime.utcnow()
        )
        
        operation = DeploymentOperation(
            operation_id="op-1",
            operation_status="Succeeded",
            timestamp=datetime.utcnow()
        )
        
        result = DeploymentResult(
            deployment_name="test",
            status=status
        )
        
        # These should not raise exceptions despite callback failures
        self.monitor._notify_progress_update(status)
        self.monitor._notify_operation_complete(operation)
        self.monitor._notify_deployment_complete(result)