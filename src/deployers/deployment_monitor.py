"""
Deployment monitoring and status tracking for Azure Infrastructure Agent.

This module provides real-time monitoring of Azure ARM template deployments
with detailed status reporting and progress tracking.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentExtended
from azure.core.polling import LROPoller
from pydantic import BaseModel, Field

from ..config.logging import get_logger

logger = get_logger(__name__)


class DeploymentState(str, Enum):
    """Deployment state enumeration."""
    
    NOT_STARTED = "NotStarted"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"
    ACCEPTED = "Accepted"
    UPDATING = "Updating"


class OperationStatus(str, Enum):
    """Deployment operation status enumeration."""
    
    IN_PROGRESS = "InProgress"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"


class DeploymentStatus(BaseModel):
    """Detailed deployment status information."""
    
    name: str = Field(description="Deployment name")
    status: str = Field(description="Overall deployment status")
    correlation_id: Optional[str] = Field(default=None, description="Azure correlation ID")
    timestamp: datetime = Field(description="Status timestamp")
    provisioning_state: Optional[str] = Field(default=None, description="Provisioning state")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    resource_count: int = Field(default=0, description="Number of resources being deployed")
    completed_operations: int = Field(default=0, description="Number of completed operations")
    failed_operations: int = Field(default=0, description="Number of failed operations")
    progress_percentage: float = Field(default=0.0, description="Deployment progress percentage")


class DeploymentOperation(BaseModel):
    """Individual deployment operation details."""
    
    operation_id: str = Field(description="Operation ID")
    resource_name: Optional[str] = Field(default=None, description="Target resource name")
    resource_type: Optional[str] = Field(default=None, description="Target resource type")
    operation_status: str = Field(description="Operation status")
    timestamp: datetime = Field(description="Operation timestamp")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    duration: Optional[timedelta] = Field(default=None, description="Operation duration")


class DeploymentResult(BaseModel):
    """Complete deployment result information."""
    
    deployment_name: str = Field(description="Deployment name")
    status: DeploymentStatus = Field(description="Final deployment status")
    outputs: Optional[Dict[str, Any]] = Field(default=None, description="Deployment outputs")
    operation_id: Optional[str] = Field(default=None, description="Azure operation ID")
    duration: Optional[timedelta] = Field(default=None, description="Total deployment duration")
    deployed_resources: List[str] = Field(default_factory=list, description="List of deployed resources")
    operations: List[DeploymentOperation] = Field(default_factory=list, description="Individual operations")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed error information")


class DeploymentProgressCallback:
    """Callback interface for deployment progress updates."""
    
    def on_progress_update(self, status: DeploymentStatus) -> None:
        """
        Called when deployment progress is updated.
        
        Args:
            status: Current deployment status
        """
        pass
        
    def on_operation_complete(self, operation: DeploymentOperation) -> None:
        """
        Called when an individual operation completes.
        
        Args:
            operation: Completed operation details
        """
        pass
        
    def on_deployment_complete(self, result: DeploymentResult) -> None:
        """
        Called when the entire deployment completes.
        
        Args:
            result: Final deployment result
        """
        pass


class ConsoleProgressCallback(DeploymentProgressCallback):
    """Console-based progress callback implementation."""
    
    def on_progress_update(self, status: DeploymentStatus) -> None:
        """Log progress updates to console."""
        logger.info(
            f"Deployment '{status.name}': {status.progress_percentage:.1f}% "
            f"({status.completed_operations}/{status.resource_count} operations completed)"
        )
        
    def on_operation_complete(self, operation: DeploymentOperation) -> None:
        """Log completed operations."""
        if operation.operation_status == OperationStatus.SUCCEEDED:
            logger.info(f"✅ {operation.resource_type}: {operation.resource_name}")
        elif operation.operation_status == OperationStatus.FAILED:
            logger.error(f"❌ {operation.resource_type}: {operation.resource_name} - {operation.error_message}")
            
    def on_deployment_complete(self, result: DeploymentResult) -> None:
        """Log deployment completion."""
        if result.status.provisioning_state == DeploymentState.SUCCEEDED:
            logger.info(f"🎉 Deployment '{result.deployment_name}' completed successfully!")
        else:
            logger.error(f"💥 Deployment '{result.deployment_name}' failed: {result.status.error_message}")


class DeploymentMonitor:
    """
    Real-time deployment monitoring and status tracking.
    
    Monitors Azure ARM template deployments and provides detailed progress
    updates, operation tracking, and completion status.
    """
    
    def __init__(self, poll_interval_seconds: int = 10) -> None:
        """
        Initialize the deployment monitor.
        
        Args:
            poll_interval_seconds: How often to poll for status updates
        """
        self.poll_interval = poll_interval_seconds
        self._callbacks: List[DeploymentProgressCallback] = []
        
    def add_progress_callback(self, callback: DeploymentProgressCallback) -> None:
        """
        Add a progress callback for deployment updates.
        
        Args:
            callback: Callback to receive progress updates
        """
        self._callbacks.append(callback)
        
    def monitor_deployment(
        self,
        deployment_operation: LROPoller,
        deployment_name: str,
        resource_group_name: str,
        timeout_minutes: int,
        client: ResourceManagementClient,
        progress_callback: Optional[DeploymentProgressCallback] = None
    ) -> DeploymentResult:
        """
        Monitor a deployment operation with real-time status updates.
        
        Args:
            deployment_operation: Azure LRO poller for the deployment
            deployment_name: Name of the deployment
            resource_group_name: Resource group name
            timeout_minutes: Maximum time to wait for completion
            client: Azure Resource Management client
            progress_callback: Optional callback for progress updates
            
        Returns:
            DeploymentResult with final status and details
        """
        logger.info(f"Starting deployment monitoring for: {deployment_name}")
        
        start_time = datetime.utcnow()
        timeout = timedelta(minutes=timeout_minutes)
        
        # Add default console callback if none provided
        if progress_callback:
            self.add_progress_callback(progress_callback)
        elif not self._callbacks:
            self.add_progress_callback(ConsoleProgressCallback())
            
        # Track operations we've already seen
        seen_operations: Dict[str, DeploymentOperation] = {}
        
        try:
            while not deployment_operation.done():
                current_time = datetime.utcnow()
                
                # Check timeout
                if current_time - start_time > timeout:
                    logger.error(f"Deployment '{deployment_name}' timed out after {timeout_minutes} minutes")
                    deployment_operation.cancel()
                    break
                    
                # Get current status
                status = self._get_current_status(deployment_name, resource_group_name, client)
                
                # Get operation details
                new_operations = self._get_deployment_operations(
                    deployment_name, resource_group_name, client, seen_operations
                )
                
                # Update seen operations
                for op in new_operations:
                    seen_operations[op.operation_id] = op
                    self._notify_operation_complete(op)
                    
                # Update progress
                status.completed_operations = len([op for op in seen_operations.values() 
                                                 if op.operation_status in [OperationStatus.SUCCEEDED, OperationStatus.FAILED]])
                status.failed_operations = len([op for op in seen_operations.values() 
                                              if op.operation_status == OperationStatus.FAILED])
                
                if status.resource_count > 0:
                    status.progress_percentage = (status.completed_operations / status.resource_count) * 100
                    
                # Notify progress callbacks
                self._notify_progress_update(status)
                
                # Check if deployment is complete
                if status.provisioning_state in [DeploymentState.SUCCEEDED, DeploymentState.FAILED, DeploymentState.CANCELED]:
                    break
                    
                # Wait before next poll
                time.sleep(self.poll_interval)
                
            # Get final result
            final_deployment = deployment_operation.result()
            final_status = self._get_current_status(deployment_name, resource_group_name, client)
            
            # Extract outputs
            outputs = {}
            if final_deployment.properties and final_deployment.properties.outputs:
                outputs = {k: v.get('value') for k, v in final_deployment.properties.outputs.items()}
                
            # Get all deployed resources
            deployed_resources = self._get_deployed_resource_names(list(seen_operations.values()))
            
            # Create final result
            result = DeploymentResult(
                deployment_name=deployment_name,
                status=final_status,
                outputs=outputs,
                operation_id=final_deployment.properties.correlation_id if final_deployment.properties else None,
                duration=datetime.utcnow() - start_time,
                deployed_resources=deployed_resources,
                operations=list(seen_operations.values())
            )
            
            # Add error details if deployment failed
            if final_status.provisioning_state == DeploymentState.FAILED:
                result.error_details = self._get_deployment_error_details(
                    deployment_name, resource_group_name, client
                )
                
            # Notify completion
            self._notify_deployment_complete(result)
            
            return result
            
        except Exception as e:
            # Handle monitoring errors
            error_message = f"Deployment monitoring failed: {str(e)}"
            logger.error(error_message)
            
            error_status = DeploymentStatus(
                name=deployment_name,
                status="Failed",
                timestamp=datetime.utcnow(),
                provisioning_state="Failed",
                error_message=error_message
            )
            
            return DeploymentResult(
                deployment_name=deployment_name,
                status=error_status,
                duration=datetime.utcnow() - start_time,
                operations=list(seen_operations.values())
            )
            
    def _get_current_status(self, deployment_name: str, resource_group_name: str, client: ResourceManagementClient) -> DeploymentStatus:
        """Get current deployment status from Azure."""
        try:
            deployment = client.deployments.get(resource_group_name, deployment_name)
            properties = deployment.properties
            
            error_message = None
            if properties and properties.error:
                error_message = properties.error.message
                
            # Count total operations to track progress
            resource_count = 0
            try:
                operations = client.deployment_operations.list(resource_group_name, deployment_name)
                resource_count = sum(1 for _ in operations)
            except:
                pass
                
            return DeploymentStatus(
                name=deployment_name,
                status=properties.provisioning_state if properties else "Unknown",
                correlation_id=properties.correlation_id if properties else None,
                timestamp=properties.timestamp if properties else datetime.utcnow(),
                provisioning_state=properties.provisioning_state if properties else None,
                error_message=error_message,
                resource_count=resource_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {str(e)}")
            return DeploymentStatus(
                name=deployment_name,
                status="Unknown",
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
            
    def _get_deployment_operations(
        self, 
        deployment_name: str, 
        resource_group_name: str, 
        client: ResourceManagementClient,
        seen_operations: Dict[str, DeploymentOperation]
    ) -> List[DeploymentOperation]:
        """Get new deployment operations since last check."""
        new_operations = []
        
        try:
            operations = client.deployment_operations.list(resource_group_name, deployment_name)
            
            for op in operations:
                operation_id = op.operation_id
                
                # Skip if we've already seen this operation
                if operation_id in seen_operations:
                    continue
                    
                # Extract operation details
                properties = op.properties
                target_resource = properties.target_resource if properties else None
                
                operation = DeploymentOperation(
                    operation_id=operation_id,
                    resource_name=target_resource.resource_name if target_resource else None,
                    resource_type=target_resource.resource_type if target_resource else None,
                    operation_status=properties.provisioning_state if properties else "Unknown",
                    timestamp=properties.timestamp if properties else datetime.utcnow(),
                    error_message=properties.status_message if properties and hasattr(properties, 'status_message') else None
                )
                
                new_operations.append(operation)
                
        except Exception as e:
            logger.warning(f"Failed to get deployment operations: {str(e)}")
            
        return new_operations
        
    def _get_deployed_resource_names(self, operations: List[DeploymentOperation]) -> List[str]:
        """Extract unique resource names from deployment operations."""
        resource_names = []
        for op in operations:
            if (op.resource_name and 
                op.operation_status == OperationStatus.SUCCEEDED and
                op.resource_name not in resource_names):
                resource_names.append(op.resource_name)
        return resource_names
        
    def _get_deployment_error_details(self, deployment_name: str, resource_group_name: str, client: ResourceManagementClient) -> Dict[str, Any]:
        """Get detailed error information for a failed deployment."""
        error_details = {}
        
        try:
            deployment = client.deployments.get(resource_group_name, deployment_name)
            if deployment.properties and deployment.properties.error:
                error = deployment.properties.error
                error_details = {
                    "code": error.code,
                    "message": error.message,
                    "target": getattr(error, 'target', None),
                    "details": getattr(error, 'details', [])
                }
                
        except Exception as e:
            logger.warning(f"Failed to get error details: {str(e)}")
            
        return error_details
        
    def _notify_progress_update(self, status: DeploymentStatus) -> None:
        """Notify all callbacks of progress update."""
        for callback in self._callbacks:
            try:
                callback.on_progress_update(status)
            except Exception as e:
                logger.warning(f"Progress callback failed: {str(e)}")
                
    def _notify_operation_complete(self, operation: DeploymentOperation) -> None:
        """Notify all callbacks of operation completion."""
        for callback in self._callbacks:
            try:
                callback.on_operation_complete(operation)
            except Exception as e:
                logger.warning(f"Operation callback failed: {str(e)}")
                
    def _notify_deployment_complete(self, result: DeploymentResult) -> None:
        """Notify all callbacks of deployment completion."""
        for callback in self._callbacks:
            try:
                callback.on_deployment_complete(result)
            except Exception as e:
                logger.warning(f"Completion callback failed: {str(e)}")


def create_deployment_monitor(poll_interval_seconds: int = 10) -> DeploymentMonitor:
    """
    Factory function to create a deployment monitor instance.
    
    Args:
        poll_interval_seconds: How often to poll for status updates
        
    Returns:
        DeploymentMonitor instance
    """
    return DeploymentMonitor(poll_interval_seconds)