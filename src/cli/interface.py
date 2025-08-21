"""
Terminal interface handling using Rich for enhanced output.
"""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


class TerminalInterface:
    """
    Handles terminal interaction with Rich formatting.
    
    Provides methods for displaying formatted output and collecting user input
    with enhanced visual styling for better user experience.
    """
    
    def __init__(self) -> None:
        """
        Initialize the terminal interface with Rich console.
        
        Sets up the Rich console instance for formatted output.
        """
        self.console = Console()
    
    def display_welcome(self) -> None:
        """
        Display the welcome message when the agent starts.
        
        Shows a formatted welcome panel with application information and basic usage.
        """
        welcome_text = Text()
        welcome_text.append("Azure Infrastructure Agent", style="bold blue")
        welcome_text.append("\n\nI can help you deploy Azure infrastructure through natural language.")
        welcome_text.append("\n\nType your requests in plain English, or type 'quit' to exit.", style="italic")
        
        panel = Panel(
            welcome_text,
            title="🚀 Welcome",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def get_user_input(self, prompt_text: str = "You") -> str:
        """
        Get input from the user with a formatted prompt.
        
        Args:
            prompt_text (str): The text to display in the prompt. Defaults to "You".
            
        Returns:
            str: The user's input string.
        """
        return Prompt.ask(f"[bold green]{prompt_text}[/bold green]")
    
    def display_agent_response(self, message: str) -> None:
        """
        Display the agent's response with formatting.
        
        Args:
            message (str): The response message to display.
        """
        response_text = Text(message, style="cyan")
        panel = Panel(
            response_text,
            title="🤖 Agent",
            border_style="cyan",
            padding=(0, 1)
        )
        self.console.print(panel)
    
    def display_error(self, error_message: str) -> None:
        """
        Display error messages with appropriate styling.
        
        Args:
            error_message (str): The error message to display.
        """
        error_text = Text(error_message, style="red")
        panel = Panel(
            error_text,
            title="❌ Error",
            border_style="red",
            padding=(0, 1)
        )
        self.console.print(panel)
    
    def display_info(self, info_message: str) -> None:
        """
        Display informational messages with styling.
        
        Args:
            info_message (str): The information message to display.
        """
        info_text = Text(info_message, style="yellow")
        panel = Panel(
            info_text,
            title="ℹ️ Info",
            border_style="yellow",
            padding=(0, 1)
        )
        self.console.print(panel)
    
    def display_goodbye(self) -> None:
        """
        Display goodbye message when exiting.
        
        Shows a farewell message when the user exits the application.
        """
        goodbye_text = Text("Thank you for using Azure Infrastructure Agent!", style="bold blue")
        panel = Panel(
            goodbye_text,
            title="👋 Goodbye",
            border_style="blue",
            padding=(0, 1)
        )
        self.console.print(panel)