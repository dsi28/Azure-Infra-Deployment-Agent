"""
Agent-based chat interface for Azure Storage Agent.

Provides a conversational interface for storage account creation and management,
integrating with the existing workflow system as a fallback option.
"""

import sys
from typing import Optional
from ..agent.conversation.storage_conversation import StorageConversation, create_storage_conversation
from ..agent.core.simple_agent import SimpleAgent, create_simple_agent
from .workflow_mode import WorkflowMode


class AgentChat:
    """
    Agent-powered chat interface for storage account management.
    
    Provides natural conversation capabilities with fallback to workflow mode
    when the agent is unavailable or encounters errors.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize agent chat interface.
        
        Args:
            data_dir (str): Directory for storing user data and preferences.
        """
        self.data_dir = data_dir
        self.storage_conversation = None
        self.workflow_mode = None
        self.agent_available = False
        
    def start(self) -> None:
        """
        Start the agent chat interface.
        
        Checks agent availability and initializes conversation or falls back to workflow.
        """
        print("Azure Storage Agent - Initializing...")
        
        # Initialize agent components
        try:
            agent = create_simple_agent(self.data_dir)
            self.agent_available = agent.is_available()
            
            if self.agent_available:
                self.storage_conversation = create_storage_conversation(self.data_dir)
                self._start_agent_mode()
            else:
                self._fallback_to_workflow()
                
        except Exception as e:
            print(f"WARNING: Agent initialization failed: {str(e)}")
            self._fallback_to_workflow()
    
    def _start_agent_mode(self) -> None:
        """Start agent conversation mode."""
        print("Agent mode activated - Ollama LLM available")
        print("TIP: You can say 'workflow' to switch to step-by-step mode anytime")
        print("-" * 60)
        
        # Start new conversation
        response = self.storage_conversation.start_new_conversation()
        print(f"Agent: {response.message}")
        
        # Main conversation loop
        self._conversation_loop()
    
    def _conversation_loop(self) -> None:
        """Main conversation loop for agent interactions."""
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()
                
                # Handle special commands
                if self._handle_special_commands(user_input):
                    continue
                
                if not user_input:
                    print("Agent: I'm here when you're ready. What storage do you need?")
                    continue
                
                # Process user input through agent
                response = self.storage_conversation.process_user_input(user_input)
                
                # Display agent response
                self._display_agent_response(response)
                
                # Handle agent errors with fallback
                if not response.success and self._should_fallback(response):
                    self._offer_workflow_fallback()
                
                # Check if conversation is complete
                if not self.storage_conversation.is_conversation_active():
                    self._handle_conversation_completion()
                    break
                    
            except KeyboardInterrupt:
                self._handle_exit()
                break
            except Exception as e:
                print(f"\nWARNING: Unexpected error: {str(e)}")
                self._offer_workflow_fallback()
    
    def _display_agent_response(self, response) -> None:
        """
        Display agent response with appropriate formatting.
        
        Args:
            response: AgentResponse object with message and metadata.
        """
        print(f"\nAgent: {response.message}")
        
        # Show additional context if available
        if response.recommendation and response.requires_confirmation:
            print("\nTIP: This recommendation is based on your request and preferences.")
        
        if hasattr(response, 'suggested_name') and response.suggested_name:
            print(f"Suggested name: {response.suggested_name}")
            
            # Check if we have dual recommendations to present
            if (hasattr(self.storage_conversation, 'current_dual_recommendation') and 
                self.storage_conversation.current_dual_recommendation):
                self._present_recommendation_choices()
    
    def _present_recommendation_choices(self) -> None:
        """
        Present the user with choices between different recommendation types.
        """
        dual_rec = self.storage_conversation.current_dual_recommendation
        
        print("\n" + "="*60)
        print("RECOMMENDATION CHOICES")
        print("="*60)
        
        print("1. RULE-BASED RECOMMENDATION:")
        print(f"   • Access Tier: {dual_rec.rules_recommendation.tier}")
        print(f"   • Performance: {dual_rec.rules_recommendation.performance}")
        print(f"   • Replication: {dual_rec.rules_recommendation.replication}")
        print(f"   • Reasoning: {dual_rec.rules_recommendation.reasoning}")
        
        if dual_rec.llm_available and dual_rec.llm_recommendation:
            print("\n2. AI RECOMMENDATION (includes your preferences):")
            print(f"   • Access Tier: {dual_rec.llm_recommendation.tier}")
            print(f"   • Performance: {dual_rec.llm_recommendation.performance}")
            print(f"   • Replication: {dual_rec.llm_recommendation.replication}")
            print(f"   • Reasoning: {dual_rec.llm_recommendation.reasoning}")
            print(f"   • Confidence: {dual_rec.llm_recommendation.confidence:.1%}")
        else:
            print("\n2. AI RECOMMENDATION: Unavailable (LLM offline)")
        
        print("\n" + "="*60)
        
        # Get user choice
        while True:
            try:
                if dual_rec.llm_available:
                    choice = input(f"\nSelect your preference (1-Rules, 2-AI): ").strip()
                    valid_choices = ['1', '2']
                else:
                    choice = input(f"\nSelect your preference (1 for Rules): ").strip()
                    valid_choices = ['1']
                
                if choice in valid_choices:
                    self._apply_chosen_recommendation(choice, dual_rec)
                    break
                else:
                    print(f"ERROR: Please enter a valid choice: {', '.join(valid_choices)}")
            except (ValueError, KeyboardInterrupt):
                print("ERROR: Invalid input. Please try again.")
    
    
    def _apply_chosen_recommendation(self, choice: str, dual_rec) -> None:
        """
        Apply the user's chosen recommendation.
        
        Args:
            choice (str): User's choice (1 or 2).
            dual_rec: Dual recommendation object.
        """
        if choice == '1':
            # Apply rules recommendation
            config = {
                'tier': dual_rec.rules_recommendation.tier,
                'performance': dual_rec.rules_recommendation.performance,
                'replication': dual_rec.rules_recommendation.replication,
                'reasoning': dual_rec.rules_recommendation.reasoning
            }
            print("Applied RULE-BASED recommendation")
            
        elif choice == '2' and dual_rec.llm_available:
            # Apply AI recommendation
            config = {
                'tier': dual_rec.llm_recommendation.tier,
                'performance': dual_rec.llm_recommendation.performance,
                'replication': dual_rec.llm_recommendation.replication,
                'reasoning': dual_rec.llm_recommendation.reasoning
            }
            print("Applied AI recommendation (includes your preferences)")
            
        else:
            print("ERROR: Invalid choice")
            return
        
        # Record the choice for learning
        from ..agent.conversation.dual_recommendation_ui import UserChoice
        user_choice_map = {'1': UserChoice.RULES, '2': UserChoice.LLM}
        
        if hasattr(self.storage_conversation, 'feedback_tracker'):
            self.storage_conversation.feedback_tracker.record_feedback(
                dual_rec,
                user_choice_map.get(choice, UserChoice.RULES),
                config
            )
        
        # Update the conversation with chosen config
        self.storage_conversation.context.current_recommendation = config
        
        print(f"\nConfiguration applied:")
        print(f"   • Access Tier: {config['tier']}")
        print(f"   • Performance: {config['performance']}")
        print(f"   • Replication: {config['replication']}")
        print(f"   • Reasoning: {config['reasoning']}")
        print("\nReady to deploy! Say 'yes' to proceed.")
    
    def _handle_special_commands(self, user_input: str) -> bool:
        """
        Handle special commands like help, exit, workflow mode.
        
        Args:
            user_input (str): User's input to check for special commands.
            
        Returns:
            bool: True if a special command was handled.
        """
        command = user_input.lower().strip()
        
        if command in ['exit', 'quit', 'bye', 'goodbye']:
            self._handle_exit()
            return True
        
        elif command in ['help', '?']:
            self._show_help()
            return True
        
        elif command in ['workflow', 'step-by-step', 'manual']:
            self._switch_to_workflow()
            return True
        
        elif command in ['status', 'summary']:
            self._show_conversation_summary()
            return True
        
        elif command in ['restart', 'start over', 'new conversation']:
            self._restart_conversation()
            return True
        
        return False
    
    def _show_help(self) -> None:
        """Show help information for agent chat."""
        help_text = """
Azure Storage Agent - Help

**Natural Storage Requests:**
• "I need storage for my website images"
• "Create backup storage for my database" 
• "I need cheap storage for log files"
• "Set up fast storage for analytics"

**During Configuration:**
• "Yes" or "Deploy" to confirm
• "Make it cheaper" to optimize for cost
• "Make it faster" to optimize for performance
• "Use a different name" for alternatives

**Special Commands:**
• help - Show this help
• workflow - Switch to step-by-step mode
• status - Show conversation summary
• restart - Start a new conversation
• exit - End the session

**Tips:**
• Be specific about your storage use case
• I remember your preferences across sessions
• I can explain my recommendations
• Say "workflow" if you prefer step-by-step guidance
        """
        print(help_text)
    
    def _show_conversation_summary(self) -> None:
        """Show current conversation summary."""
        if self.storage_conversation:
            summary = self.storage_conversation.get_conversation_summary()
            print(f"\nConversation Summary:")
            print(f"• State: {summary['state']}")
            print(f"• Interactions: {summary['interaction_count']}")
            print(f"• Has Recommendation: {summary['has_recommendation']}")
            if summary['conversation_duration_minutes']:
                print(f"• Duration: {summary['conversation_duration_minutes']:.1f} minutes")
        else:
            print("No active conversation to summarize.")
    
    def _restart_conversation(self) -> None:
        """Restart the current conversation."""
        if self.storage_conversation:
            response = self.storage_conversation.start_new_conversation()
            print(f"\nStarting fresh conversation...")
            print(f"Agent: {response.message}")
        else:
            print("No conversation to restart.")
    
    def _switch_to_workflow(self) -> None:
        """Switch to workflow mode."""
        print("\nSwitching to workflow mode...")
        self._fallback_to_workflow()
    
    def _should_fallback(self, response) -> bool:
        """
        Determine if we should offer fallback to workflow mode.
        
        Args:
            response: AgentResponse to evaluate.
            
        Returns:
            bool: True if fallback should be offered.
        """
        # Offer fallback for repeated errors or LLM unavailability
        return (
            not response.success and 
            response.error_message and
            ("unavailable" in response.error_message.lower() or
             "error" in response.error_message.lower())
        )
    
    def _offer_workflow_fallback(self) -> None:
        """Offer user the option to switch to workflow mode."""
        print("\nWould you like to switch to step-by-step workflow mode? (y/n)")
        choice = input("You: ").strip().lower()
        
        if choice in ['y', 'yes', 'ok', 'workflow']:
            self._fallback_to_workflow()
    
    def _fallback_to_workflow(self) -> None:
        """Fall back to workflow mode when agent is unavailable."""
        print("\nSwitching to workflow mode...")
        print("Step-by-step storage account creation")
        print("-" * 50)
        
        # Initialize and start workflow mode
        self.workflow_mode = WorkflowMode(self.data_dir)
        self.workflow_mode.start()
    
    def _handle_conversation_completion(self) -> None:
        """Handle completed conversations."""
        if self.storage_conversation:
            response = self.storage_conversation.end_conversation()
            print(f"\nAgent: {response.message}")
        
        # Offer to start new conversation or exit
        print("\nWould you like to:")
        print("1. Start a new conversation")
        print("2. Switch to workflow mode") 
        print("3. Exit")
        
        choice = input("\nChoose (1-3): ").strip()
        
        if choice == '1':
            self._restart_conversation()
            self._conversation_loop()
        elif choice == '2':
            self._fallback_to_workflow()
        else:
            self._handle_exit()
    
    def _handle_exit(self) -> None:
        """Handle graceful exit."""
        if self.storage_conversation and self.storage_conversation.is_conversation_active():
            # End conversation gracefully
            self.storage_conversation.end_conversation()
        
        print("\nThanks for using Azure Storage Agent!")
        print("TIP: Run with --agent flag anytime to restart")
        sys.exit(0)


class WorkflowMode:
    """
    Placeholder for workflow mode integration.
    
    This would integrate with the existing workflow system when agent mode
    is unavailable or when user explicitly requests step-by-step guidance.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize workflow mode.
        
        Args:
            data_dir (str): Directory for storing user data.
        """
        self.data_dir = data_dir
    
    def start(self) -> None:
        """Start workflow mode."""
        print("Workflow Mode - Step-by-Step Storage Creation")
        print("NOTICE: This would integrate with your existing workflow system")
        print("TIP: For now, please use your existing CLI workflow")
        print("\nAgent mode will be available when Ollama is running")
        print("RUN: ollama pull llama3.2:3b")
        print("Then restart with --agent flag")


def create_agent_chat(data_dir: str = "data") -> AgentChat:
    """
    Factory function to create AgentChat instance.
    
    Args:
        data_dir (str): Directory for storing user data.
        
    Returns:
        AgentChat: Configured agent chat interface.
    """
    return AgentChat(data_dir)