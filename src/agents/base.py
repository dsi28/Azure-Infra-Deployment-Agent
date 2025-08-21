"""
Base agent classes for the Azure Infrastructure Agent.

This module provides base classes and interfaces for all agent types
including intent parsers, resource handlers, and specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentRequest(BaseModel):
    """Base request model for agent interactions."""
    
    user_input: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AgentResponse(BaseModel):
    """Base response model for agent interactions."""
    
    response: str
    confidence: float
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    This class defines the interface that all agents must implement,
    providing a consistent way to process user requests and generate responses.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Initialize the base agent.
        
        Args:
            name (str): The name of the agent.
            version (str): The version of the agent.
        """
        self.name = name
        self.version = version
        self.is_active = True
    
    @abstractmethod
    def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a user request and generate a response.
        
        Args:
            request (AgentRequest): The user request to process.
            
        Returns:
            AgentResponse: The agent's response to the request.
        """
        pass
    
    def activate(self) -> None:
        """Activate this agent for processing requests."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate this agent from processing requests."""
        self.is_active = False
    
    def get_info(self) -> Dict[str, str]:
        """
        Get basic information about this agent.
        
        Returns:
            Dict[str, str]: Agent information including name, version, and status.
        """
        return {
            "name": self.name,
            "version": self.version,
            "status": "active" if self.is_active else "inactive"
        }


class IntentParserAgent(BaseAgent):
    """
    Base class for intent parsing agents.
    
    Intent parsers are responsible for analyzing user input to determine
    what the user wants to do and extracting relevant entities.
    """
    
    def __init__(self, name: str = "IntentParser", version: str = "1.0.0"):
        super().__init__(name, version)
        self.supported_intents: List[str] = []
    
    def add_intent(self, intent: str) -> None:
        """
        Add a supported intent to this parser.
        
        Args:
            intent (str): The intent name to add.
        """
        if intent not in self.supported_intents:
            self.supported_intents.append(intent)
    
    def remove_intent(self, intent: str) -> None:
        """
        Remove a supported intent from this parser.
        
        Args:
            intent (str): The intent name to remove.
        """
        if intent in self.supported_intents:
            self.supported_intents.remove(intent)


class ResourceAgent(BaseAgent):
    """
    Base class for resource-specific agents.
    
    Resource agents handle specific Azure resource types and manage
    their configuration, validation, and deployment workflows.
    """
    
    def __init__(self, resource_type: str, name: str = None, version: str = "1.0.0"):
        super().__init__(name or f"{resource_type}Agent", version)
        self.resource_type = resource_type
        self.required_parameters: List[str] = []
        self.optional_parameters: List[str] = []
    
    def add_required_parameter(self, param: str) -> None:
        """
        Add a required parameter for this resource type.
        
        Args:
            param (str): The parameter name to add as required.
        """
        if param not in self.required_parameters:
            self.required_parameters.append(param)
    
    def add_optional_parameter(self, param: str) -> None:
        """
        Add an optional parameter for this resource type.
        
        Args:
            param (str): The parameter name to add as optional.
        """
        if param not in self.optional_parameters:
            self.optional_parameters.append(param)
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate a resource configuration.
        
        Args:
            config (Dict[str, Any]): The resource configuration to validate.
            
        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def generate_template(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an ARM template for this resource.
        
        Args:
            config (Dict[str, Any]): The resource configuration.
            
        Returns:
            Dict[str, Any]: The generated ARM template.
        """
        pass