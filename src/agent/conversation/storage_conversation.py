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
from ...config.logging import get_logger

logger = get_logger(__name__)


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
            
            # Generate conversational introduction based on the request
            intro_message = self._generate_conversational_intro(user_input, dual_rec)
            if intro_message:
                print(f"\nAgent: {intro_message}")
            
            # Present dual recommendations to user
            self.dual_ui.present_dual_recommendations(dual_rec)
            
            # Transition to collecting user choice state
            self.context.state = ConversationState.COLLECTING_USER_CHOICE
            
            # Display choice options
            print("\nCHOICE OPTIONS:")
            if dual_rec.llm_available:
                print("1  Use AI Recommendation (LLM-based)")
                print("2  Use Rule-Based Recommendation") 
                print("3  Cancel")
                choice_message = "Select your choice (1/2/cancel): "
            else:
                print("1  Use Rule-Based Recommendation")
                print("2  Cancel")
                choice_message = "Select your choice (1/cancel): "
                
            return AgentResponse(
                message=choice_message,
                success=True,
                requires_confirmation=False
            )
            
        except Exception as e:
            # Log the actual error for debugging
            logger.error(f"Dual recommendation failed: {str(e)}", exc_info=True)
            
            # Handle dual recommendation failure gracefully
            # Try to get a rule-based recommendation only
            try:
                from ..decision.storage_advisor import create_storage_advisor
                advisor = create_storage_advisor()
                rule_rec = advisor.get_storage_recommendation(user_input, user_profile)
                
                # Create a dual recommendation with only rules component
                from ..decision.dual_recommender import DualRecommendation
                fallback_dual_rec = DualRecommendation(
                    llm_recommendation=None,
                    rules_recommendation=rule_rec.configuration,
                    llm_available=False,
                    user_input=user_input,
                    context={"fallback_mode": True, "error": str(e)}
                )
                
                # Store and present the fallback recommendation
                self.current_dual_recommendation = fallback_dual_rec
                self.dual_ui.present_dual_recommendations(fallback_dual_rec)
                
                # Transition to collecting user choice state
                self.context.state = ConversationState.COLLECTING_USER_CHOICE
                
                # Display choice options for rules only
                print("\nCHOICE OPTIONS:")
                print("1  Use Rule-Based Recommendation")
                print("2  Cancel")
                
                # Return message asking for user choice (rules only)
                return AgentResponse(
                    message="Select your choice (1/cancel): ",
                    success=True,
                    requires_confirmation=False
                )
                
            except Exception as fallback_error:
                # Last resort: return a simple error message
                self.context.state = ConversationState.ERROR
                return AgentResponse(
                    message=f"Sorry, I'm having trouble processing your storage request. Please try again or ask for help.",
                    success=False
                )
    
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
    
    def _handle_user_choice_collection(self, user_input: str) -> AgentResponse:
        """
        Handle user choice between dual recommendations.
        
        Args:
            user_input (str): User's choice input.
            
        Returns:
            AgentResponse: Response after processing user choice.
        """
        if not self.current_dual_recommendation:
            self.context.state = ConversationState.ERROR
            return AgentResponse(
                message="Sorry, I don't have any recommendations to show. Let's start over.",
                success=False
            )
        
        # Parse user choice
        choice_input = user_input.strip().lower()
        
        if choice_input in ['1']:
            if self.current_dual_recommendation.llm_available:
                choice = UserChoice.LLM
            else:
                choice = UserChoice.RULES  # When LLM unavailable, choice 1 = rules
        elif choice_input in ['2'] and self.current_dual_recommendation.llm_available:
            choice = UserChoice.RULES
        elif choice_input in ['cancel', 'c']:
            choice = UserChoice.CANCEL
        else:
            # Invalid choice, ask again
            if self.current_dual_recommendation.llm_available:
                return AgentResponse(
                    message="Invalid choice. Please enter 1 (AI), 2 (Rules), or cancel: ",
                    success=True
                )
            else:
                return AgentResponse(
                    message="Invalid choice. Please enter 1 (Rules) or cancel: ",
                    success=True
                )
        
        # Process the choice
        return self._process_user_choice(choice, None)
    
    def _handle_deployment_confirmation(self, user_input: str) -> AgentResponse:
        """
        Handle final deployment confirmation.
        
        Args:
            user_input (str): User's final confirmation or changes.
            
        Returns:
            AgentResponse: Deployment ready response or further modifications.
        """
        # If user wants to make changes, provide modification options
        if self._is_modification_request(user_input):
            self.context.state = ConversationState.MODIFYING_CONFIG
            
            config = self.context.current_recommendation
            return AgentResponse(
                message=(
                    f"What would you like to modify in your storage configuration?\n\n"
                    f"Current settings:\n"
                    f"• Access Tier: {config.get('tier', 'N/A')}\n"
                    f"• Performance: {config.get('performance', 'N/A')}\n"
                    f"• Replication: {config.get('replication', 'N/A')}\n\n"
                    f"You can say:\n"
                    f"• 'Make it cheaper' - Optimize for cost\n"
                    f"• 'Make it faster' - Optimize for performance\n"
                    f"• 'Change to Cool tier' - Specify tier changes\n"
                    f"• 'Use GRS replication' - Specify replication changes\n"
                    f"• 'Back' - Return to deployment options\n"
                    f"• 'Start over' - Begin with a new storage request"
                ),
                success=True
            )
        
        # If user confirms, show final configuration and proceed to deployment
        elif self._is_confirmation(user_input):
            # Show final configuration summary
            config = self.context.current_recommendation
            print(f"\n{'='*60}")
            print("FINAL DEPLOYMENT CONFIGURATION")
            print(f"{'='*60}")
            print(f"Access Tier: {config.get('tier', 'N/A')}")
            print(f"Performance: {config.get('performance', 'N/A')}")
            print(f"Replication: {config.get('replication', 'N/A')}")
            if config.get('reasoning'):
                print(f"Reasoning: {config['reasoning']}")
            print(f"{'='*60}")
            
            # Complete the conversation with deployment message
            self.context.state = ConversationState.COMPLETED
            return AgentResponse(
                message="Storage account configuration ready for deployment! In a real deployment, this would create the Azure storage account with the specified settings.",
                success=True,
                recommendation=config
            )
        
        # Handle other inputs
        else:
            return AgentResponse(
                message=(
                    "Please choose an option:\n"
                    "• Say 'yes' or 'deploy' to confirm deployment\n"
                    "• Say 'modify' or 'change' to make adjustments\n"  
                    "• Say 'cancel' to start over with a new request"
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
        user_input_lower = user_input.lower().strip()
        current_config = self.context.current_recommendation
        
        # Handle specific modification requests
        if 'back' in user_input_lower or 'return' in user_input_lower:
            # Go back to deployment confirmation
            self.context.state = ConversationState.CONFIRMING_DEPLOYMENT
            return AgentResponse(
                message="Returning to deployment options. Would you like me to deploy this storage account? (Say 'yes' to deploy, 'modify' to make changes, or 'cancel' to start over)",
                success=True
            )
            
        elif 'start over' in user_input_lower or 'new request' in user_input_lower:
            # Start completely over
            self.context.state = ConversationState.GATHERING_REQUIREMENTS
            self.current_dual_recommendation = None
            self.context.current_recommendation = None
            return AgentResponse(
                message="Starting over. What storage do you need?",
                success=True
            )
        
        elif 'cheaper' in user_input_lower or 'cost' in user_input_lower:
            # Optimize for cost - suggest cheaper alternatives
            modified_config = current_config.copy()
            if current_config.get('tier') == 'Hot':
                modified_config['tier'] = 'Cool'
                modified_config['reasoning'] = 'Changed to Cool tier for cost savings'
            elif current_config.get('tier') == 'Cool':
                modified_config['tier'] = 'Archive'
                modified_config['reasoning'] = 'Changed to Archive tier for maximum cost savings'
            else:
                # Already cheapest, suggest performance change
                if current_config.get('performance') == 'Premium':
                    modified_config['performance'] = 'Standard'
                    modified_config['reasoning'] = 'Changed to Standard performance for cost savings'
                
            return self._apply_configuration_change(modified_config, "cost optimization")
            
        elif 'faster' in user_input_lower or 'performance' in user_input_lower:
            # Optimize for performance
            modified_config = current_config.copy()
            if current_config.get('performance') == 'Standard':
                modified_config['performance'] = 'Premium'
                modified_config['reasoning'] = 'Changed to Premium performance for better speed'
            if current_config.get('tier') in ['Cool', 'Archive']:
                modified_config['tier'] = 'Hot'
                modified_config['reasoning'] = 'Changed to Hot tier for faster access'
                
            return self._apply_configuration_change(modified_config, "performance optimization")
        
        elif 'cool' in user_input_lower and 'tier' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['tier'] = 'Cool'
            modified_config['reasoning'] = 'Changed to Cool tier as requested'
            return self._apply_configuration_change(modified_config, "tier change to Cool")
            
        elif 'hot' in user_input_lower and 'tier' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['tier'] = 'Hot'
            modified_config['reasoning'] = 'Changed to Hot tier as requested'
            return self._apply_configuration_change(modified_config, "tier change to Hot")
            
        elif 'archive' in user_input_lower and 'tier' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['tier'] = 'Archive'
            modified_config['reasoning'] = 'Changed to Archive tier as requested'
            return self._apply_configuration_change(modified_config, "tier change to Archive")
            
        elif 'grs' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['replication'] = 'GRS'
            modified_config['reasoning'] = 'Changed to GRS replication for geo-redundancy'
            return self._apply_configuration_change(modified_config, "replication change to GRS")
            
        elif 'zrs' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['replication'] = 'ZRS'
            modified_config['reasoning'] = 'Changed to ZRS replication for zone redundancy'
            return self._apply_configuration_change(modified_config, "replication change to ZRS")
            
        elif 'lrs' in user_input_lower:
            modified_config = current_config.copy()
            modified_config['replication'] = 'LRS'
            modified_config['reasoning'] = 'Changed to LRS replication for cost efficiency'
            return self._apply_configuration_change(modified_config, "replication change to LRS")
        
        else:
            # Unrecognized modification request
            return AgentResponse(
                message=(
                    "I didn't understand that modification request. Please try:\n"
                    "• 'Make it cheaper' or 'Make it faster'\n"
                    "• 'Change to [Cool/Hot/Archive] tier'\n"
                    "• 'Use [LRS/GRS/ZRS] replication'\n"
                    "• 'Back' to return to deployment options\n"
                    "• 'Start over' for a new storage request"
                ),
                success=True
            )
    
    def _apply_configuration_change(self, modified_config: dict, change_description: str) -> AgentResponse:
        """Apply a configuration change and return to confirmation state."""
        self.context.current_recommendation = modified_config
        self.context.state = ConversationState.CONFIRMING_DEPLOYMENT
        
        return AgentResponse(
            message=(
                f"Configuration updated ({change_description})!\n\n"
                f"New settings:\n"
                f"• Access Tier: {modified_config.get('tier', 'N/A')}\n"
                f"• Performance: {modified_config.get('performance', 'N/A')}\n"
                f"• Replication: {modified_config.get('replication', 'N/A')}\n\n"
                f"Would you like me to deploy this storage account? (Say 'yes' to deploy, 'modify' to make more changes, or 'cancel' to start over)"
            ),
            success=True,
            recommendation=modified_config
        )
    
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
    
    def _generate_conversational_intro(self, user_input: str, dual_rec) -> str:
        """
        Generate a conversational introduction to the dual recommendations.
        
        Args:
            user_input (str): User's original request.
            dual_rec: Dual recommendation object.
            
        Returns:
            str: Conversational introduction message.
        """
        # Extract use case from input for personalized response
        user_input_lower = user_input.lower()
        
        if 'website' in user_input_lower or 'web' in user_input_lower or 'images' in user_input_lower:
            use_case = "website content"
            context = "fast access for users"
        elif 'backup' in user_input_lower or 'database' in user_input_lower:
            use_case = "backup storage"
            context = "reliable data protection"
        elif 'log' in user_input_lower or 'cheap' in user_input_lower or 'archive' in user_input_lower:
            use_case = "archival storage"
            context = "cost-effective long-term storage"
        elif 'video' in user_input_lower or 'fast' in user_input_lower or 'performance' in user_input_lower:
            use_case = "high-performance storage"
            context = "fast access and processing"
        elif 'analytics' in user_input_lower or 'data' in user_input_lower:
            use_case = "data analytics"
            context = "efficient data processing"
        else:
            use_case = "storage"
            context = "your requirements"
        
        # Generate contextual intro message
        if dual_rec.llm_available and dual_rec.get_agreement_score() >= 0.67:
            return f"Perfect! I'll help you set up {use_case} optimized for {context}. Both my AI analysis and rule-based recommendations agree on the best approach:"
        elif dual_rec.llm_available and dual_rec.get_agreement_score() < 0.33:
            return f"Interesting! For {use_case} optimized for {context}, I have two different approaches. My AI analysis suggests a different strategy than the standard rules:"
        elif dual_rec.llm_available:
            return f"Great! I'll set up {use_case} for {context}. I have both AI-powered and rule-based recommendations with some interesting differences:"
        else:
            return f"I'll help you create {use_case} optimized for {context}. Here's my rule-based recommendation:"
    
    def _handle_dual_recommendation_presentation(self, user_input: str) -> AgentResponse:
        """
        Handle dual recommendation presentation state.
        
        Args:
            user_input (str): User's response to dual recommendations.
            
        Returns:
            AgentResponse: Response based on user's choice or feedback.
        """
        # This state should not be reached with the new flow, fallback to error
        self.context.state = ConversationState.ERROR
        return AgentResponse(
            message="Something went wrong. Let's start over.",
            success=False
        )
    
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
        
        # Parse user choice
        choice_input = user_input.strip().lower()
        
        if choice_input in ['1']:
            if self.current_dual_recommendation.llm_available:
                choice = UserChoice.LLM
            else:
                choice = UserChoice.RULES  # When LLM unavailable, choice 1 = rules
        elif choice_input in ['2'] and self.current_dual_recommendation.llm_available:
            choice = UserChoice.RULES
        elif choice_input in ['cancel', 'c']:
            choice = UserChoice.CANCEL
        else:
            # Invalid choice, ask again
            if self.current_dual_recommendation.llm_available:
                return AgentResponse(
                    message="Invalid choice. Please enter 1 (AI), 2 (Rules), or cancel: ",
                    success=True
                )
            else:
                return AgentResponse(
                    message="Invalid choice. Please enter 1 (Rules) or cancel: ",
                    success=True
                )
        
        # Process the choice
        return self._process_user_choice(choice, None)
    
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
    
    def _process_user_choice(self, choice: UserChoice, custom_config: Optional[Dict[str, Any]]) -> AgentResponse:
        """
        Process user's choice for dual recommendations.
        
        Args:
            choice (UserChoice): User's recommendation choice.
            custom_config (Optional[Dict[str, Any]]): Custom configuration if provided.
            
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
        
        # Process the choice
        if choice == UserChoice.CANCEL:
            # Reset conversation state for new request
            self.context.state = ConversationState.GATHERING_REQUIREMENTS
            self.current_dual_recommendation = None
            self.context.current_recommendation = None
            
            return AgentResponse(
                message="Configuration cancelled. What storage do you need?",
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
            message="Configuration selected! Would you like me to deploy this storage account? (Say 'yes' to deploy, 'modify' to make changes, or 'cancel' to start over)",
            success=True,
            requires_confirmation=True,
            recommendation=final_config
        )


def create_storage_conversation(data_dir: str = "data") -> StorageConversation:
    """
    Factory function to create a StorageConversation instance.
    
    Args:
        data_dir (str): Directory for storing conversation data.
        
    Returns:
        StorageConversation: Configured conversation manager.
    """
    return StorageConversation(data_dir=data_dir)