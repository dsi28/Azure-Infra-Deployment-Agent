"""
Chat interface logic for the Azure Infrastructure Agent.
"""
import signal
import sys
from typing import Optional
from .interface import TerminalInterface


class ChatManager:
    """
    Manages the conversational interface and main chat loop.
    
    Handles user input processing, conversation flow, and graceful shutdown
    for the Azure Infrastructure Agent CLI.
    """
    
    def __init__(self) -> None:
        """
        Initialize the chat manager with terminal interface.
        
        Sets up the terminal interface and configures signal handlers
        for graceful exit handling.
        """
        self.interface = TerminalInterface()
        self.running = True
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful exit on Ctrl+C.
        
        Configures SIGINT handler to allow clean shutdown when user
        presses Ctrl+C during conversation.
        """
        # Reason: Enable graceful shutdown on Ctrl+C signal
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle interrupt signals for graceful shutdown.
        
        Args:
            signum (int): The signal number received.
            frame: The current stack frame.
        """
        self.interface.display_info("\nShutdown requested...")
        self.stop()
    
    def start(self) -> None:
        """
        Start the main conversation loop.
        
        Displays welcome message and enters the main chat loop
        where users can interact with the agent.
        """
        self.interface.display_welcome()
        self._conversation_loop()
    
    def stop(self) -> None:
        """
        Stop the conversation loop and display goodbye message.
        
        Sets the running flag to False and shows farewell message.
        """
        self.running = False
        self.interface.display_goodbye()
    
    def _conversation_loop(self) -> None:
        """
        Main conversation loop for processing user input.
        
        Continuously processes user input until exit condition is met.
        Handles quit commands and forwards other input to the agent processor.
        """
        while self.running:
            try:
                user_input = self.interface.get_user_input()
                
                # Check for exit commands
                if self._is_exit_command(user_input):
                    self.stop()
                    break
                
                # Process the user input and generate response
                response = self._process_user_input(user_input)
                self.interface.display_agent_response(response)
                
            except EOFError:
                # Reason: Handle EOF gracefully (e.g., when input is redirected)
                self.interface.display_info("\nInput stream ended.")
                self.stop()
                break
            except KeyboardInterrupt:
                # Reason: Additional safety net for Ctrl+C handling
                self.interface.display_info("\nInterrupted by user.")
                self.stop()
                break
            except Exception as e:
                # Reason: Catch unexpected errors to prevent crash
                self.interface.display_error(f"An unexpected error occurred: {str(e)}")
    
    def _is_exit_command(self, user_input: str) -> bool:
        """
        Check if the user input is an exit command.
        
        Args:
            user_input (str): The user's input string.
            
        Returns:
            bool: True if the input is an exit command, False otherwise.
        """
        exit_commands = ['quit', 'exit', 'bye', 'goodbye']
        return user_input.lower().strip() in exit_commands
    
    def _process_user_input(self, user_input: str) -> str:
        """
        Process user input and generate appropriate response.
        
        Currently provides basic acknowledgment responses. This will be
        enhanced in future tasks to include intent parsing and resource handling.
        
        Args:
            user_input (str): The user's input string.
            
        Returns:
            str: The agent's response message.
        """
        # Basic response logic - will be replaced with intent parser in Task 2.1
        if not user_input.strip():
            return "I'm here to help! Please tell me what Azure resources you need."
        
        # Simple acknowledgment for now
        return f"I understand you said: '{user_input}'. " \
               f"In the next phase, I'll be able to help you deploy Azure infrastructure. " \
               f"For now, I'm just acknowledging your input!"