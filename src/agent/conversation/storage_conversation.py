"""
Storage-focused conversation flow management.

Handles the conversational aspects of storage account creation,
maintaining context and guiding users through configuration decisions.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from ..core.simple_agent import SimpleAgent, AgentResponse, create_simple_agent
from ..memory.user_profile import UserProfile
from ..decision.dual_recommender import DualRecommendationEngine, create_dual_recommender
from ..conversation.dual_recommendation_ui import DualRecommendationUI, UserChoice, create_dual_recommendation_ui
from ..learning.recommendation_feedback import RecommendationPreferenceTracker, create_recommendation_tracker


class ConversationState(Enum):
    """States in the storage conversation flow."""
    INITIAL = "initial"
    GATHERING_REQUIREMENTS = "gathering_requirements"
    PRESENTING_DUAL_RECOMMENDATION = "presenting_dual_recommendation"
    COLLECTING_USER_CHOICE = "collecting_user_choice"
    CONFIRMING_DEPLOYMENT = "confirming_deployment"
    MODIFYING_CONFIG = "modifying_config"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ConversationContext:
    """
    Context for ongoing storage conversation.
    
    Tracks conversation state, user requirements, and interaction history
    to maintain coherent dialogue flow.
    """
    state: ConversationState = ConversationState.INITIAL
    user_requirements: Dict[str, Any] = None
    current_recommendation: Any = None
    interaction_count: int = 0
    last_user_input: str = ""
    conversation_id: str = ""
    started_at: datetime = None


class StorageConversation:
    """
    Manages storage-focused conversation flow.
    
    Provides structured conversation management for storage account creation,
    guiding users through requirements gathering, recommendation review, and deployment.
    """
    
    def __init__(self, agent: Optional[SimpleAgent] = None, data_dir: str = "data"):
        """
        Initialize storage conversation manager.
        
        Args:
            agent (Optional[SimpleAgent]): Storage agent for processing.
            data_dir (str): Directory for storing conversation data.
        """
        self.agent = agent or create_simple_agent(data_dir)
        self.context = ConversationContext()
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize dual recommendation components
        self.dual_engine = create_dual_recommender()
        self.dual_ui = create_dual_recommendation_ui()
        self.feedback_tracker = create_recommendation_tracker()
        
        # Store current dual recommendation for choice processing
        self.current_dual_recommendation = None
        
    def start_new_conversation(self) -> AgentResponse:
        """
        Start a new storage conversation.
        
        Returns:
            AgentResponse: Welcome message and conversation initialization.
        """
        # Generate conversation ID
        self.context.conversation_id = f"storage_conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.context.started_at = datetime.now()
        self.context.state = ConversationState.INITIAL
        self.context.interaction_count = 0
        self.conversation_history = []
        
        # Start agent conversation
        response = self.agent.start_conversation()
        
        # Record interaction
        self._record_interaction("system", response.message, response)
        
        if response.success:
            self.context.state = ConversationState.GATHERING_REQUIREMENTS
        else:
            self.context.state = ConversationState.ERROR
            
        return response
    
    def process_user_input(self, user_input: str) -> AgentResponse:
        """
        Process user input and advance conversation flow.
        
        Args:
            user_input (str): User's message or input.
            
        Returns:
            AgentResponse: Agent's response with updated conversation state.
        """
        self.context.last_user_input = user_input
        self.context.interaction_count += 1
        
        # Record user input
        self._record_interaction("user", user_input)
        
        # Process based on current conversation state
        if self.context.state == ConversationState.INITIAL:
            response = self._handle_initial_state(user_input)
        elif self.context.state == ConversationState.GATHERING_REQUIREMENTS:
            response = self._handle_requirements_gathering(user_input)
        elif self.context.state == ConversationState.PRESENTING_DUAL_RECOMMENDATION:
            response = self._handle_dual_recommendation_presentation(user_input)
        elif self.context.state == ConversationState.COLLECTING_USER_CHOICE:
            response = self._handle_user_choice_collection(user_input)
        elif self.context.state == ConversationState.CONFIRMING_DEPLOYMENT:
            response = self._handle_deployment_confirmation(user_input)
        elif self.context.state == ConversationState.MODIFYING_CONFIG:
            response = self._handle_configuration_modification(user_input)
        else:
            response = self._handle_error_state(user_input)
        
        # Record agent response
        self._record_interaction("agent", response.message, response)
        
        return response
    
    def _handle_initial_state(self, user_input: str) -> AgentResponse:
        """Handle conversation in initial state."""
        self.context.state = ConversationState.GATHERING_REQUIREMENTS
        return self._handle_requirements_gathering(user_input)
    
    def _handle_requirements_gathering(self, user_input: str) -> AgentResponse:
        """
        Handle requirements gathering phase.
        
        Args:
            user_input (str): User's storage requirements.
            
        Returns:
            AgentResponse: Response with storage recommendation or follow-up questions.
        """
        # Check for help requests
        if any(word in user_input.lower() for word in ["help", "what can you do", "how", "guide"]):
            return AgentResponse(
                message=self.agent.get_help_message()
            )
        
        # Get dual recommendation using both LLM and rules
        try:
            user_profile = self.agent.get_user_profile() if hasattr(self.agent, 'get_user_profile') else None
            dual_rec = self.dual_engine.get_dual_recommendation(user_input, user_profile)
            
            # Store dual recommendation for choice processing
            self.current_dual_recommendation = dual_rec
            
            # Present dual recommendations to user
            self.dual_ui.present_dual_recommendations(dual_rec)
            
            # Move to choice collection state
            self.context.state = ConversationState.COLLECTING_USER_CHOICE
            
            return AgentResponse(
                message="Please review the recommendations above and make your choice.",
                success=True,
                requires_confirmation=False
            )
            
        except Exception as e:
            # Fallback to original agent processing
            response = self.agent.process_message(user_input)
            
            if response.success and response.recommendation:
                # We have a recommendation - move to presentation state
                self.context.state = ConversationState.PRESENTING_DUAL_RECOMMENDATION
                self.context.current_recommendation = response.recommendation
                
                # Extract user requirements from the response context
                if response.context_used:
                    self.context.user_requirements = {
                        "detected_use_case": response.recommendation.detected_use_case,
                        "confidence": response.recommendation.confidence,
                        "keywords_found": response.context_used.get("detected_keywords", []),
                        "context_hints": response.context_used.get("context_hints", {})
                    }
            elif not response.success:
                self.context.state = ConversationState.ERROR
                
            return response
    
    def _handle_recommendation_review(self, user_input: str) -> AgentResponse:
        """
        Handle recommendation review and user feedback.
        
        Args:
            user_input (str): User's response to recommendation.
            
        Returns:
            AgentResponse: Response based on user's feedback.
        """
        # Check for confirmation
        if self._is_confirmation(user_input):
            self.context.state = ConversationState.CONFIRMING_DEPLOYMENT
            return self.agent.process_message(user_input)
        
        # Check for modification requests
        elif self._is_modification_request(user_input):
            self.context.state = ConversationState.MODIFYING_CONFIG
            return self.agent.process_message(user_input)
        
        # Check for new requirements (starting over)
        elif self._is_new_storage_request(user_input):
            self.context.state = ConversationState.GATHERING_REQUIREMENTS
            self.context.current_recommendation = None
            return self.agent.process_message(user_input)
        
        # Handle unclear responses
        else:
            return AgentResponse(
                message=(
                    "I'm not sure how to interpret that. You can:\n"
                    "• Say 'yes' to proceed with the current configuration\n"
                    "• Ask for changes like 'make it cheaper' or 'make it faster'\n"
                    "• Start over with a new storage request\n"
                    "• Say 'help' for more options\n\n"
                    "What would you like to do?"
                )
            )
    
    def _handle_deployment_confirmation(self, user_input: str) -> AgentResponse:
        """
        Handle final deployment confirmation.
        
        Args:
            user_input (str): User's final confirmation or changes.
            
        Returns:
            AgentResponse: Deployment ready response or further modifications.
        """
        # If user wants to make changes, go back to modification
        if self._is_modification_request(user_input):
            self.context.state = ConversationState.MODIFYING_CONFIG
            return self.agent.process_message(user_input)
        
        # If user confirms, complete the conversation
        elif self._is_confirmation(user_input):
            response = self.agent.process_message(user_input)
            if response.success:
                self.context.state = ConversationState.COMPLETED
            return response
        
        # Handle other inputs
        else:
            return AgentResponse(
                message=(
                    "Ready to deploy! Say 'yes' to confirm the deployment, "
                    "or let me know if you'd like to make any final changes."
                )
            )
    
    def _handle_configuration_modification(self, user_input: str) -> AgentResponse:
        """
        Handle configuration modification requests.
        
        Args:
            user_input (str): User's modification request.
            
        Returns:
            AgentResponse: Modified configuration response.
        """
        response = self.agent.process_message(user_input)
        
        if response.success and response.recommendation:
            # Updated recommendation received, go back to review
            self.context.state = ConversationState.PRESENTING_RECOMMENDATION
            self.context.current_recommendation = response.recommendation
        elif not response.success:
            self.context.state = ConversationState.ERROR
            
        return response
    
    def _handle_error_state(self, user_input: str) -> AgentResponse:
        """
        Handle conversation in error state.
        
        Args:
            user_input (str): User input during error.
            
        Returns:
            AgentResponse: Error handling response.
        """
        # Try to recover by starting fresh
        if any(word in user_input.lower() for word in ["start over", "restart", "new", "fresh"]):
            return self.start_new_conversation()
        
        # Provide help
        elif any(word in user_input.lower() for word in ["help", "what now"]):
            return AgentResponse(
                message=(
                    "It looks like we ran into an issue. You can:\n"
                    "• Say 'start over' to begin a fresh conversation\n"
                    "• Tell me what storage you need (e.g., 'I need storage for images')\n"
                    "• Say 'help' for guidance on what I can do\n\n"
                    "What would you like to try?"
                )
            )
        
        # Try to process as new request
        else:
            self.context.state = ConversationState.GATHERING_REQUIREMENTS
            return self._handle_requirements_gathering(user_input)
    
    def _is_confirmation(self, user_input: str) -> bool:
        """Check if user input is a confirmation."""
        confirmations = [
            "yes", "y", "ok", "okay", "proceed", "deploy", "create", "go ahead",
            "confirm", "looks good", "perfect", "that's right"
        ]
        return user_input.lower().strip() in confirmations
    
    def _is_modification_request(self, user_input: str) -> bool:
        """Check if user input is requesting modifications."""
        modifications = [
            "cheaper", "make it cheaper", "cost", "expensive", "cheap", "save money",
            "faster", "make it faster", "performance", "speed", "slow", "quicker",
            "different", "change", "modify", "alter", "adjust", "update",
            "better", "improve", "optimize", "tweak"
        ]
        user_lower = user_input.lower()
        return any(mod in user_lower for mod in modifications)
    
    def _is_new_storage_request(self, user_input: str) -> bool:
        """Check if user input is a new storage request."""
        storage_keywords = [
            "i need", "create", "make", "set up", "deploy", "new storage",
            "storage for", "storage account", "blob storage", "file storage"
        ]
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in storage_keywords)
    
    def _record_interaction(
        self, 
        speaker: str, 
        message: str, 
        response_data: Optional[AgentResponse] = None
    ) -> None:
        """
        Record conversation interaction for history tracking.
        
        Args:
            speaker (str): Who is speaking ("user", "agent", "system").
            message (str): The message content.
            response_data (Optional[AgentResponse]): Additional response metadata.
        """
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message,
            "conversation_state": self.context.state.value,
            "interaction_count": self.context.interaction_count
        }
        
        if response_data:
            interaction.update({
                "success": response_data.success,
                "requires_confirmation": response_data.requires_confirmation,
                "has_recommendation": response_data.recommendation is not None,
                "error_message": response_data.error_message
            })
            
        self.conversation_history.append(interaction)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get summary of current conversation.
        
        Returns:
            Dict[str, Any]: Conversation summary with key metrics and status.
        """
        return {
            "conversation_id": self.context.conversation_id,
            "state": self.context.state.value,
            "started_at": self.context.started_at.isoformat() if self.context.started_at else None,
            "interaction_count": self.context.interaction_count,
            "has_recommendation": self.context.current_recommendation is not None,
            "user_requirements": self.context.user_requirements,
            "total_interactions": len(self.conversation_history),
            "conversation_duration_minutes": self._get_conversation_duration_minutes()
        }
    
    def _get_conversation_duration_minutes(self) -> Optional[float]:
        """Calculate conversation duration in minutes."""
        if not self.context.started_at:
            return None
        
        duration = datetime.now() - self.context.started_at
        return duration.total_seconds() / 60.0
    
    def export_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Export complete conversation history.
        
        Returns:
            List[Dict[str, Any]]: Complete interaction history.
        """
        return self.conversation_history.copy()
    
    def is_conversation_active(self) -> bool:
        """
        Check if conversation is currently active.
        
        Returns:
            bool: True if conversation is in progress.
        """
        active_states = [
            ConversationState.GATHERING_REQUIREMENTS,
            ConversationState.PRESENTING_DUAL_RECOMMENDATION,
            ConversationState.COLLECTING_USER_CHOICE,
            ConversationState.CONFIRMING_DEPLOYMENT,
            ConversationState.MODIFYING_CONFIG
        ]
        return self.context.state in active_states
    
    def _handle_dual_recommendation_presentation(self, user_input: str) -> AgentResponse:
        """
        Handle dual recommendation presentation state.
        
        Args:
            user_input (str): User's response to dual recommendations.
            
        Returns:
            AgentResponse: Response based on user's choice or feedback.
        """
        # This is primarily handled by the UI, redirect to choice collection
        self.context.state = ConversationState.COLLECTING_USER_CHOICE
        return self._handle_user_choice_collection(user_input)
    
    def _handle_user_choice_collection(self, user_input: str) -> AgentResponse:
        """
        Handle user choice collection for dual recommendations.
        
        Args:
            user_input (str): User's choice input.
            
        Returns:
            AgentResponse: Response after processing user choice.
        """
        if not self.current_dual_recommendation:
            # No dual recommendation available, fallback to error
            self.context.state = ConversationState.ERROR
            return AgentResponse(
                message="Sorry, I don't have any recommendations to show. Let's start over.",
                success=False
            )
        
        try:
            # Get user choice through UI
            choice, custom_config = self.dual_ui.get_user_choice(self.current_dual_recommendation)
            
            # Process the choice
            if choice == UserChoice.CANCEL:
                return AgentResponse(
                    message="Configuration cancelled. Would you like to start over with a new storage request?",
                    success=True
                )
            
            # Determine final configuration based on choice
            if choice == UserChoice.LLM and self.current_dual_recommendation.llm_recommendation:
                final_config = {
                    'tier': self.current_dual_recommendation.llm_recommendation.tier,
                    'performance': self.current_dual_recommendation.llm_recommendation.performance,
                    'replication': self.current_dual_recommendation.llm_recommendation.replication,
                    'reasoning': self.current_dual_recommendation.llm_recommendation.reasoning
                }
            elif choice == UserChoice.RULES:
                rules_rec = self.current_dual_recommendation.rules_recommendation
                final_config = {
                    'tier': rules_rec.tier,
                    'performance': rules_rec.performance,
                    'replication': rules_rec.replication,
                    'reasoning': rules_rec.reasoning
                }
            else:
                # Invalid choice
                return AgentResponse(
                    message="Invalid choice. Please try again.",
                    success=False
                )
            
            # Record feedback for learning
            self.feedback_tracker.record_feedback(
                self.current_dual_recommendation,
                choice,
                final_config
            )
            
            # Show final selection
            self.dual_ui.show_final_selection(choice, final_config)
            
            # Store the final configuration
            self.context.current_recommendation = final_config
            self.context.state = ConversationState.CONFIRMING_DEPLOYMENT
            
            return AgentResponse(
                message="Configuration selected! Would you like me to deploy this storage account?",
                success=True,
                requires_confirmation=True,
                recommendation=final_config
            )
            
        except Exception as e:
            self.context.state = ConversationState.ERROR
            return AgentResponse(
                message=f"Sorry, there was an error processing your choice: {str(e)}",
                success=False
            )
    
    def end_conversation(self) -> AgentResponse:
        """
        End the current conversation gracefully.
        
        Returns:
            AgentResponse: Farewell message.
        """
        response = self.agent.end_conversation()
        self.context.state = ConversationState.COMPLETED
        
        self._record_interaction("system", "Conversation ended", response)
        
        return response


def create_storage_conversation(data_dir: str = "data") -> StorageConversation:
    """
    Factory function to create a StorageConversation instance.
    
    Args:
        data_dir (str): Directory for storing conversation data.
        
    Returns:
        StorageConversation: Configured conversation manager.
    """
    return StorageConversation(data_dir=data_dir)