"""
Test cases for src/cli/interface.py
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from cli.interface import TerminalInterface


class TestTerminalInterface:
    """Test cases for TerminalInterface class."""
    
    def test_init_creates_console(self):
        """
        Test that initialization creates a Rich console instance.
        
        This is the expected use case.
        """
        interface = TerminalInterface()
        assert hasattr(interface, 'console')
        assert interface.console is not None
    
    @patch('cli.interface.Console')
    def test_display_welcome_prints_panel(self, mock_console_class):
        """
        Test that display_welcome prints a welcome panel.
        
        This is the expected use case for starting the application.
        """
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        interface = TerminalInterface()
        interface.display_welcome()
        
        mock_console.print.assert_called_once()
        # Verify a Panel was passed to print
        call_args = mock_console.print.call_args[0]
        assert len(call_args) == 1
    
    @patch('cli.interface.Prompt.ask')
    def test_get_user_input_returns_string(self, mock_ask):
        """
        Test that get_user_input returns user input string.
        
        This is the expected use case.
        """
        mock_ask.return_value = "test input"
        interface = TerminalInterface()
        
        result = interface.get_user_input()
        
        assert result == "test input"
        mock_ask.assert_called_once()
    
    @patch('cli.interface.Console')
    def test_display_agent_response_with_message(self, mock_console_class):
        """
        Test that display_agent_response prints formatted message.
        
        This is the expected use case.
        """
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        interface = TerminalInterface()
        interface.display_agent_response("Test response")
        
        mock_console.print.assert_called_once()
    
    @patch('cli.interface.Console')
    def test_display_error_with_empty_message(self, mock_console_class):
        """
        Test that display_error handles empty error message.
        
        This is an edge case.
        """
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        interface = TerminalInterface()
        interface.display_error("")
        
        mock_console.print.assert_called_once()
    
    @patch('cli.interface.Console')
    @patch('cli.interface.Panel', side_effect=Exception("Panel creation failed"))
    def test_display_info_handles_panel_failure(self, mock_panel, mock_console_class):
        """
        Test behavior when Panel creation fails.
        
        This is a failure case.
        """
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        interface = TerminalInterface()
        
        with pytest.raises(Exception, match="Panel creation failed"):
            interface.display_info("Test info")