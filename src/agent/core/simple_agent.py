"""
Main agent orchestrator for the Azure Storage Agent.

Coordinates between LLM, decision engine, memory, and user preferences
to provide intelligent storage account recommendations and deployment.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from ..llm.ollama_client import OllamaClient, create_ollama_client, OllamaResponse
from ..llm.storage_prompts import (
    STORAGE_AGENT_SYSTEM_PROMPT,
    format_extract_requirements_prompt,
    format_suggest_config_prompt,
    format_conversational_response_prompt
)
from ..memory.user_profile import UserProfile, create_user_profile
from ..decision.storage_advisor import StorageAdvisor, StorageRecommendation, create_storage_advisor


@dataclass
class AgentResponse:
    """
    Complete agent response with recommendation and conversation context.
    
    Contains the agent's natural language response, storage recommendation,
    and metadata about the interaction.
    """
    message: str
    recommendation: Optional[StorageRecommendation] = None
    success: bool = True
    error_message: Optional[str] = None
    requires_confirmation: bool = False
    suggested_name: Optional[str] = None
    context_used: Dict[str, Any] = None


class SimpleAgent:
    """
    Main storage agent orchestrator.
    
    Combines LLM conversation, decision engine recommendations, and user preferences
    to provide intelligent storage account assistance through natural conversation.
    """
    
    def __init__(
        self,
        llm_client: Optional[OllamaClient] = None,
        user_profile: Optional[UserProfile] = None,
        storage_advisor: Optional[StorageAdvisor] = None,
        data_dir: str = "data"
    ):
        """
        Initialize the storage agent.
        
        Args:
            llm_client (Optional[OllamaClient]): LLM client for conversations.
            user_profile (Optional[UserProfile]): User profile for preferences.
            storage_advisor (Optional[StorageAdvisor]): Decision engine for recommendations.
            data_dir (str): Directory for storing user data.
        """
        self.llm_client = llm_client or create_ollama_client()
        self.user_profile = user_profile or create_user_profile(data_dir)
        self.storage_advisor = storage_advisor or create_storage_advisor()
        self.conversation_active = False
        self.last_recommendation = None
        
    def is_available(self) -> bool:
        """
        Check if the agent is available and ready to respond.
        
        Returns:
            bool: True if agent components are available.
        """
        return self.llm_client.is_available()
    
    def start_conversation(self) -> AgentResponse:
        """
        Start a new storage conversation.
        
        Returns:
            AgentResponse: Welcome message and agent availability status.
        """
        self.conversation_active = True
        self.last_recommendation = None
        
        if not self.is_available():
            return AgentResponse(
                message="Hello! I'm your Azure Storage Agent, but I'm currently unavailable. "
                       "Please ensure Ollama is running with a model installed (ollama pull llama3.2:3b), "
                       "or I can fall back to workflow mode to help you.",
                success=False,
                error_message="LLM service unavailable"
            )
        
        welcome_message = (
            "Hello! I'm your Azure Storage Agent. I can help you create and configure "
            "Azure Storage Accounts through natural conversation.\n\n"
            "Just tell me what kind of storage you need - for example:\n"
            "• 'I need storage for my website images'\n"
            "• 'Create backup storage for my database'\n"
            "• 'I need cheap storage for log files'\n\n"
            "What can I help you with today?"
        )
        
        return AgentResponse(message=welcome_message)
    
    def process_message(self, user_input: str) -> AgentResponse:
        """
        Process a user message and provide intelligent response.
        
        Args:
            user_input (str): User's natural language input.
            
        Returns:
            AgentResponse: Agent response with recommendations and context.
        """
        if not user_input or not user_input.strip():
            return AgentResponse(
                message="I didn't catch that. Could you tell me what kind of storage you need?",
                success=False
            )
        
        # Check for confirmation responses
        if self.last_recommendation and self._is_confirmation(user_input):
            return self._handle_confirmation(user_input)
        
        # Check for modification requests
        if self.last_recommendation and self._is_modification_request(user_input):
            return self._handle_modification_request(user_input)
        
        # Process new storage request
        return self._process_storage_request(user_input)
    
    def _process_storage_request(self, user_input: str) -> AgentResponse:
        """
        Process a new storage request from the user.
        
        Args:
            user_input (str): User's storage request.
            
        Returns:
            AgentResponse: Response with storage recommendation.
        """
        try:
            # Get user preferences and context
            user_preferences = self.user_profile.get_context_for_conversation()["user_preferences"]
            
            # Get storage recommendation from decision engine
            recommendation = self.storage_advisor.recommend_configuration(
                user_input=user_input,
                user_preferences=user_preferences
            )
            
            # Generate suggested storage account name
            suggested_name = self.user_profile.suggest_storage_name(
                recommendation.detected_use_case
            )
            
            # Generate conversational response using LLM
            response_message = self._generate_conversational_response(
                recommendation, user_input, suggested_name
            )
            
            # Store this recommendation for potential confirmation
            self.last_recommendation = recommendation
            
            return AgentResponse(
                message=response_message,
                recommendation=recommendation,
                requires_confirmation=True,
                suggested_name=suggested_name,
                context_used=recommendation.context_used
            )
            
        except Exception as e:
            return self._handle_error(f"Error processing storage request: {str(e)}")
    
    def _generate_conversational_response(
        self, 
        recommendation: StorageRecommendation, 
        user_input: str,
        suggested_name: str
    ) -> str:
        """
        Generate natural conversational response using LLM.
        
        Args:
            recommendation (StorageRecommendation): Storage recommendation.
            user_input (str): Original user request.
            suggested_name (str): Suggested storage account name.
            
        Returns:
            str: Natural language response.
        """
        if not self.is_available():
            return self._generate_fallback_response(recommendation, suggested_name)
        
        try:
            # Prepare context for LLM
            context = {
                "user_request": user_input,
                "detected_use_case": recommendation.detected_use_case,
                "confidence": recommendation.confidence,
                "suggested_name": suggested_name
            }
            
            # Format prompt for conversational response
            prompt = format_conversational_response_prompt(
                recommendation.configuration.__dict__, 
                context
            )
            
            # Get LLM response
            llm_response = self.llm_client.generate(prompt)
            
            if llm_response.success:
                return self._enhance_llm_response(llm_response.content, recommendation, suggested_name)
            else:
                return self._generate_fallback_response(recommendation, suggested_name)
                
        except Exception:
            return self._generate_fallback_response(recommendation, suggested_name)
    
    def _enhance_llm_response(
        self, 
        llm_content: str, 
        recommendation: StorageRecommendation,
        suggested_name: str
    ) -> str:
        """
        Enhance LLM response with structured information and confirmation prompt.
        
        Args:
            llm_content (str): Raw LLM response content.
            recommendation (StorageRecommendation): Storage recommendation.
            suggested_name (str): Suggested storage name.
            
        Returns:
            str: Enhanced response with clear recommendation and confirmation.
        """
        config = recommendation.configuration
        
        # Build structured recommendation summary
        recommendation_summary = (
            f"📋 **Storage Configuration:**\n"
            f"• Performance: {config.performance}\n"
            f"• Access Tier: {config.tier}\n"
            f"• Replication: {config.replication}\n"
            f"• Suggested Name: {suggested_name}\n"
            f"• Confidence: {recommendation.confidence:.0%}\n\n"
        )
        
        # Add reasoning
        reasoning_section = f"💡 **Why this configuration?**\n{config.reasoning}\n\n"
        
        # Add confirmation prompt
        confirmation_prompt = (
            "Would you like me to proceed with this configuration? "
            "You can also say 'make it cheaper', 'make it faster', or ask for changes."
        )
        
        # Combine LLM response with structured information
        if len(llm_content.strip()) > 0:
            enhanced_response = (
                f"{llm_content.strip()}\n\n"
                f"{recommendation_summary}"
                f"{reasoning_section}"
                f"{confirmation_prompt}"
            )
        else:
            enhanced_response = (
                f"{recommendation_summary}"
                f"{reasoning_section}"
                f"{confirmation_prompt}"
            )
        
        return enhanced_response
    
    def _generate_fallback_response(
        self, 
        recommendation: StorageRecommendation,
        suggested_name: str
    ) -> str:
        """
        Generate fallback response when LLM is unavailable.
        
        Args:
            recommendation (StorageRecommendation): Storage recommendation.
            suggested_name (str): Suggested storage name.
            
        Returns:
            str: Fallback response with clear recommendation.
        """
        config = recommendation.configuration
        use_case = recommendation.detected_use_case
        
        response = (
            f"I'll help you set up storage for {use_case}. Based on your requirements, I recommend:\n\n"
            f"📋 **Configuration:**\n"
            f"• Performance: {config.performance} (cost-effective for most workloads)\n"
            f"• Access Tier: {config.tier} (appropriate for your use case)\n"
            f"• Replication: {config.replication} (balances cost and reliability)\n"
            f"• Name: {suggested_name}\n\n"
            f"💡 **Reasoning:** {config.reasoning}\n\n"
            f"Would you like to proceed with this configuration? Say 'yes' to continue, "
            f"or let me know if you'd like any changes."
        )
        
        return response
    
    def _is_confirmation(self, user_input: str) -> bool:
        """Check if user input is a confirmation."""
        confirmations = ["yes", "y", "ok", "okay", "proceed", "deploy", "create", "go ahead"]
        return user_input.lower().strip() in confirmations
    
    def _is_modification_request(self, user_input: str) -> bool:
        """Check if user input is requesting modifications."""
        modifications = [
            "cheaper", "make it cheaper", "cost", "expensive", "cheap",
            "faster", "make it faster", "performance", "speed", "slow",
            "different", "change", "modify", "alter", "adjust"
        ]
        user_lower = user_input.lower()
        return any(mod in user_lower for mod in modifications)
    
    def _handle_confirmation(self, user_input: str) -> AgentResponse:
        """
        Handle user confirmation to proceed with deployment.
        
        Args:
            user_input (str): Confirmation input.
            
        Returns:
            AgentResponse: Confirmation response ready for deployment.
        """
        if not self.last_recommendation:
            return AgentResponse(
                message="I don't have a recommendation to confirm. Please tell me what storage you need.",
                success=False
            )
        
        # Record this as a pending deployment for learning
        deployment_record = {
            "success": True,  # Will be updated after actual deployment
            "use_case": self.last_recommendation.detected_use_case,
            "access_tier": self.last_recommendation.configuration.tier,
            "performance_tier": self.last_recommendation.configuration.performance,
            "replication_type": self.last_recommendation.configuration.replication,
            "user_confirmed": True
        }
        
        self.user_profile.add_deployment_history(deployment_record)
        
        response_message = (
            f"Perfect! I'll prepare the deployment with these settings:\n\n"
            f"📋 **Final Configuration:**\n"
            f"• Performance: {self.last_recommendation.configuration.performance}\n"
            f"• Access Tier: {self.last_recommendation.configuration.tier}\n"
            f"• Replication: {self.last_recommendation.configuration.replication}\n\n"
            f"The configuration is ready for deployment. You can now use your existing "
            f"deployment tools to create the storage account with these specifications."
        )
        
        return AgentResponse(
            message=response_message,
            recommendation=self.last_recommendation,
            requires_confirmation=False
        )
    
    def _handle_modification_request(self, user_input: str) -> AgentResponse:
        """
        Handle user request to modify the recommendation.
        
        Args:
            user_input (str): Modification request.
            
        Returns:
            AgentResponse: Modified recommendation response.
        """
        if not self.last_recommendation:
            return AgentResponse(
                message="I don't have a recommendation to modify. Please tell me what storage you need.",
                success=False
            )
        
        try:
            # Analyze modification request
            user_lower = user_input.lower()
            
            # Adjust preferences based on request
            modified_preferences = self.user_profile.get_context_for_conversation()["user_preferences"].copy()
            
            if any(word in user_lower for word in ["cheaper", "cheap", "cost", "expensive"]):
                modified_preferences["cost_preference"] = "optimized"
                modification_type = "cost-optimized"
            elif any(word in user_lower for word in ["faster", "performance", "speed", "slow"]):
                modified_preferences["cost_preference"] = "performance"
                modification_type = "performance-optimized"
            else:
                modification_type = "general"
            
            # Get new recommendation with modified preferences
            original_request = f"I need storage for {self.last_recommendation.detected_use_case}"
            new_recommendation = self.storage_advisor.recommend_configuration(
                user_input=original_request,
                user_preferences=modified_preferences
            )
            
            # Generate response about the modification
            response_message = self._generate_modification_response(
                new_recommendation, modification_type
            )
            
            # Update last recommendation
            self.last_recommendation = new_recommendation
            
            return AgentResponse(
                message=response_message,
                recommendation=new_recommendation,
                requires_confirmation=True,
                context_used=new_recommendation.context_used
            )
            
        except Exception as e:
            return self._handle_error(f"Error modifying recommendation: {str(e)}")
    
    def _generate_modification_response(
        self, 
        recommendation: StorageRecommendation,
        modification_type: str
    ) -> str:
        """
        Generate response for modified recommendation.
        
        Args:
            recommendation (StorageRecommendation): New recommendation.
            modification_type (str): Type of modification requested.
            
        Returns:
            str: Response explaining the modification.
        """
        config = recommendation.configuration
        
        if modification_type == "cost-optimized":
            intro = "I've adjusted the configuration to be more cost-effective:"
        elif modification_type == "performance-optimized":
            intro = "I've optimized the configuration for better performance:"
        else:
            intro = "I've modified the configuration based on your request:"
        
        response = (
            f"{intro}\n\n"
            f"📋 **Updated Configuration:**\n"
            f"• Performance: {config.performance}\n"
            f"• Access Tier: {config.tier}\n"
            f"• Replication: {config.replication}\n\n"
            f"💡 **Reasoning:** {config.reasoning}\n\n"
            f"Does this look better? Say 'yes' to proceed or request further changes."
        )
        
        return response
    
    def _handle_error(self, error_message: str) -> AgentResponse:
        """
        Handle errors with fallback to workflow mode suggestion.
        
        Args:
            error_message (str): Error description.
            
        Returns:
            AgentResponse: Error response with fallback suggestion.
        """
        return AgentResponse(
            message=(
                "I encountered an issue processing your request. "
                "You can try rephrasing your request, or I can fall back to "
                "the standard workflow mode to help you create storage accounts.\n\n"
                f"Technical details: {error_message}"
            ),
            success=False,
            error_message=error_message
        )
    
    def get_help_message(self) -> str:
        """
        Get help message explaining agent capabilities.
        
        Returns:
            str: Help message with usage examples.
        """
        return (
            "Azure Storage Agent Help\n\n"
            "I can help you create Azure Storage Accounts through natural conversation. "
            "Here are some things you can say:\n\n"
            "**New Storage Requests:**\n"
            "• 'I need storage for my website images'\n"
            "• 'Create backup storage for my database'\n"
            "• 'I need cheap storage for old log files'\n"
            "• 'Fast storage for analytics data'\n\n"
            "**During Configuration:**\n"
            "• 'Yes' or 'Deploy' to confirm\n"
            "• 'Make it cheaper' to optimize for cost\n"
            "• 'Make it faster' to optimize for performance\n"
            "• 'Use a different name' to suggest alternatives\n\n"
            "**I remember your preferences:**\n"
            "• Preferred regions and naming patterns\n"
            "• Cost vs performance preferences\n"
            "• Previous successful configurations\n\n"
            "Just tell me what kind of storage you need!"
        )
    
    def end_conversation(self) -> AgentResponse:
        """
        End the current conversation.
        
        Returns:
            AgentResponse: Farewell message.
        """
        self.conversation_active = False
        self.last_recommendation = None
        
        return AgentResponse(
            message="Thanks for using the Azure Storage Agent! Feel free to start a new "
                   "conversation anytime you need help with storage accounts."
        )


def create_simple_agent(data_dir: str = "data") -> SimpleAgent:
    """
    Factory function to create a SimpleAgent instance.
    
    Args:
        data_dir (str): Directory for storing user data.
        
    Returns:
        SimpleAgent: Configured agent instance.
    """
    return SimpleAgent(data_dir=data_dir)