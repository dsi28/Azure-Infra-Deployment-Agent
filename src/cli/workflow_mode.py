"""
Workflow mode fallback for the agent chat system.

This module provides a simple fallback workflow mode when the agent is unavailable.
"""

from typing import Optional


class WorkflowMode:
    """
    Simple workflow mode fallback.
    
    Provides basic guidance when agent mode is not available.
    """
    
    def __init__(self):
        """Initialize workflow mode."""
        pass
    
    def start(self) -> None:
        """Start the workflow mode interface."""
        print("\n📋 **Workflow Mode - Step-by-Step Storage Creation**")
        print("🔧 This would integrate with your existing workflow system")
        print("💡 For now, please use your existing CLI workflow")
        print("\n✅ Agent mode will be available when Ollama is running")
        print("🚀 Run: ollama pull llama3.2:3b")
        print("🔄 Then restart with --agent flag")
    
    def process_request(self, user_input: str) -> Optional[str]:
        """
        Process user request in workflow mode.
        
        Args:
            user_input: User's input request
            
        Returns:
            Response message or None
        """
        return "Workflow mode: Please use your existing CLI workflow for now."