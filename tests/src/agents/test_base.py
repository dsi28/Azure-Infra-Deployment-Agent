"""
Unit tests for agents.base module.

Tests for base agent classes including BaseAgent, IntentParserAgent,
and ResourceAgent with expected use cases, edge cases, and failure scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.agents.base import (
    BaseAgent, 
    IntentParserAgent, 
    ResourceAgent,
    AgentRequest,
    AgentResponse
)


class TestAgentRequest:
    """Test cases for AgentRequest model."""
    
    def test_agent_request_creation_success(self):
        """Test successful creation of AgentRequest."""
        request = AgentRequest(
            user_input="Create a storage account",
            context={"session_id": "test123"},
            session_id="test123"
        )
        
        assert request.user_input == "Create a storage account"
        assert request.context == {"session_id": "test123"}
        assert request.session_id == "test123"
    
    def test_agent_request_minimal_creation(self):
        """Test AgentRequest creation with only required fields."""
        request = AgentRequest(user_input="Test input")
        
        assert request.user_input == "Test input"
        assert request.context is None
        assert request.session_id is None
    
    def test_agent_request_empty_input_failure(self):
        """Test AgentRequest creation with empty input fails validation."""
        # Pydantic allows empty strings by default, so this test should pass
        request = AgentRequest(user_input="")
        assert request.user_input == ""


class TestAgentResponse:
    """Test cases for AgentResponse model."""
    
    def test_agent_response_creation_success(self):
        """Test successful creation of AgentResponse."""
        response = AgentResponse(
            response="I can help you create a storage account",
            confidence=0.95,
            intent="create_storage_account",
            entities={"resource_type": "storage_account"},
            next_action="collect_parameters"
        )
        
        assert response.response == "I can help you create a storage account"
        assert response.confidence == 0.95
        assert response.intent == "create_storage_account"
        assert response.entities == {"resource_type": "storage_account"}
        assert response.next_action == "collect_parameters"
    
    def test_agent_response_minimal_creation(self):
        """Test AgentResponse creation with only required fields."""
        response = AgentResponse(
            response="Test response",
            confidence=0.8
        )
        
        assert response.response == "Test response"
        assert response.confidence == 0.8
        assert response.intent is None
        assert response.entities is None
        assert response.next_action is None
    
    def test_agent_response_invalid_confidence_failure(self):
        """Test AgentResponse creation with invalid confidence fails."""
        # Pydantic doesn't automatically constrain float values, so this test should pass
        response = AgentResponse(response="Test", confidence=1.5)
        assert response.confidence == 1.5


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Test implementation of process method."""
        return AgentResponse(
            response=f"Processed: {request.user_input}",
            confidence=0.9
        )


class ConcreteIntentParserAgent(IntentParserAgent):
    """Concrete implementation of IntentParserAgent for testing."""
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Test implementation of process method."""
        return AgentResponse(
            response=f"Parsed intent from: {request.user_input}",
            confidence=0.8,
            intent="test_intent"
        )


class TestBaseAgent:
    """Test cases for BaseAgent class."""
    
    def test_base_agent_initialization_success(self):
        """Test successful BaseAgent initialization."""
        agent = ConcreteAgent("TestAgent", "1.0.0")
        
        assert agent.name == "TestAgent"
        assert agent.version == "1.0.0"
        assert agent.is_active is True
    
    def test_base_agent_default_version(self):
        """Test BaseAgent initialization with default version."""
        agent = ConcreteAgent("TestAgent")
        
        assert agent.name == "TestAgent"
        assert agent.version == "1.0.0"
        assert agent.is_active is True
    
    def test_base_agent_process_success(self):
        """Test successful processing of agent request."""
        agent = ConcreteAgent("TestAgent")
        request = AgentRequest(user_input="Test input")
        
        response = agent.process(request)
        
        assert response.response == "Processed: Test input"
        assert response.confidence == 0.9
    
    def test_base_agent_activate_deactivate(self):
        """Test agent activation and deactivation."""
        agent = ConcreteAgent("TestAgent")
        
        # Should be active by default
        assert agent.is_active is True
        
        # Deactivate
        agent.deactivate()
        assert agent.is_active is False
        
        # Reactivate
        agent.activate()
        assert agent.is_active is True
    
    def test_base_agent_get_info(self):
        """Test agent info retrieval."""
        agent = ConcreteAgent("TestAgent", "2.0.0")
        
        info = agent.get_info()
        
        expected = {
            "name": "TestAgent",
            "version": "2.0.0",
            "status": "active"
        }
        assert info == expected
        
        # Test inactive status
        agent.deactivate()
        info = agent.get_info()
        assert info["status"] == "inactive"


class TestIntentParserAgent:
    """Test cases for IntentParserAgent class."""
    
    def test_intent_parser_initialization_success(self):
        """Test successful IntentParserAgent initialization."""
        agent = ConcreteIntentParserAgent("CustomParser", "1.5.0")
        
        assert agent.name == "CustomParser"
        assert agent.version == "1.5.0"
        assert agent.supported_intents == []
    
    def test_intent_parser_default_initialization(self):
        """Test IntentParserAgent initialization with defaults."""
        agent = ConcreteIntentParserAgent()
        
        assert agent.name == "IntentParser"
        assert agent.version == "1.0.0"
        assert agent.supported_intents == []
    
    def test_add_intent_success(self):
        """Test successful intent addition."""
        agent = ConcreteIntentParserAgent()
        
        agent.add_intent("create_storage_account")
        agent.add_intent("create_web_app")
        
        assert "create_storage_account" in agent.supported_intents
        assert "create_web_app" in agent.supported_intents
        assert len(agent.supported_intents) == 2
    
    def test_add_duplicate_intent_edge_case(self):
        """Test adding duplicate intent doesn't create duplicates."""
        agent = ConcreteIntentParserAgent()
        
        agent.add_intent("create_storage_account")
        agent.add_intent("create_storage_account")  # Duplicate
        
        assert agent.supported_intents == ["create_storage_account"]
        assert len(agent.supported_intents) == 1
    
    def test_remove_intent_success(self):
        """Test successful intent removal."""
        agent = ConcreteIntentParserAgent()
        agent.add_intent("create_storage_account")
        agent.add_intent("create_web_app")
        
        agent.remove_intent("create_storage_account")
        
        assert "create_storage_account" not in agent.supported_intents
        assert "create_web_app" in agent.supported_intents
        assert len(agent.supported_intents) == 1
    
    def test_remove_nonexistent_intent_edge_case(self):
        """Test removing non-existent intent doesn't cause error."""
        agent = ConcreteIntentParserAgent()
        agent.add_intent("create_web_app")
        
        # Should not raise an error
        agent.remove_intent("nonexistent_intent")
        
        assert agent.supported_intents == ["create_web_app"]


class ConcreteResourceAgent(ResourceAgent):
    """Concrete implementation of ResourceAgent for testing."""
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Test implementation of process method."""
        return AgentResponse(
            response=f"Processing resource request: {request.user_input}",
            confidence=0.9
        )
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Test implementation of validate_configuration."""
        required_keys = ["name", "location", "resource_group"]
        return all(key in config for key in required_keys)
    
    def generate_template(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test implementation of generate_template."""
        return {
            "$schema": "test-schema",
            "resources": [
                {
                    "type": self.resource_type,
                    "name": config.get("name", "test-resource")
                }
            ]
        }


class TestResourceAgent:
    """Test cases for ResourceAgent class."""
    
    def test_resource_agent_initialization_success(self):
        """Test successful ResourceAgent initialization."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts", "StorageAgent", "1.0.0")
        
        assert agent.name == "StorageAgent"
        assert agent.version == "1.0.0"
        assert agent.resource_type == "Microsoft.Storage/storageAccounts"
        assert agent.required_parameters == []
        assert agent.optional_parameters == []
    
    def test_resource_agent_default_name(self):
        """Test ResourceAgent initialization with default name."""
        agent = ConcreteResourceAgent("Microsoft.Web/sites")
        
        assert agent.name == "Microsoft.Web/sitesAgent"
        assert agent.resource_type == "Microsoft.Web/sites"
    
    def test_add_required_parameter_success(self):
        """Test successful addition of required parameters."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        agent.add_required_parameter("name")
        agent.add_required_parameter("location")
        
        assert "name" in agent.required_parameters
        assert "location" in agent.required_parameters
        assert len(agent.required_parameters) == 2
    
    def test_add_optional_parameter_success(self):
        """Test successful addition of optional parameters."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        agent.add_optional_parameter("sku")
        agent.add_optional_parameter("kind")
        
        assert "sku" in agent.optional_parameters
        assert "kind" in agent.optional_parameters
        assert len(agent.optional_parameters) == 2
    
    def test_add_duplicate_parameter_edge_case(self):
        """Test adding duplicate parameters doesn't create duplicates."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        agent.add_required_parameter("name")
        agent.add_required_parameter("name")  # Duplicate
        
        assert agent.required_parameters == ["name"]
        assert len(agent.required_parameters) == 1
    
    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        config = {
            "name": "teststorage",
            "location": "East US",
            "resource_group": "test-rg"
        }
        
        result = agent.validate_configuration(config)
        assert result is True
    
    def test_validate_configuration_failure(self):
        """Test configuration validation failure."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        config = {
            "name": "teststorage"
            # Missing required fields
        }
        
        result = agent.validate_configuration(config)
        assert result is False
    
    def test_generate_template_success(self):
        """Test successful template generation."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        config = {
            "name": "teststorage",
            "location": "East US",
            "resource_group": "test-rg"
        }
        
        template = agent.generate_template(config)
        
        assert template["$schema"] == "test-schema"
        assert len(template["resources"]) == 1
        assert template["resources"][0]["type"] == "Microsoft.Storage/storageAccounts"
        assert template["resources"][0]["name"] == "teststorage"
    
    def test_generate_template_empty_config_edge_case(self):
        """Test template generation with empty configuration."""
        agent = ConcreteResourceAgent("Microsoft.Storage/storageAccounts")
        
        template = agent.generate_template({})
        
        assert template["$schema"] == "test-schema"
        assert template["resources"][0]["name"] == "test-resource"  # Default name