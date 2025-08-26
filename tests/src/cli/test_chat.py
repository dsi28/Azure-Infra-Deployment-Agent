"""
Test cases for src/cli/chat.py
"""
import pytest
from unittest.mock import patch, MagicMock, call
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.cli.chat import ChatManager


class TestChatManager:
    """Test cases for ChatManager class."""
    
    @patch('src.cli.chat.TerminalInterface')
    @patch('src.cli.chat.signal.signal')
    def test_init_sets_up_interface_and_signals(self, mock_signal, mock_interface_class):
        """
        Test that initialization creates interface and sets up signal handlers.
        
        This is the expected use case.
        """
        chat_manager = ChatManager()
        
        # Verify terminal interface was created
        mock_interface_class.assert_called_once()
        assert hasattr(chat_manager, 'interface')
        assert chat_manager.running is True
        
        # Verify signal handler was set up
        mock_signal.assert_called_once_with(signal.SIGINT, chat_manager._signal_handler)
    
    @patch('src.cli.chat.TerminalInterface')
    def test_start_displays_welcome_and_starts_loop(self, mock_interface_class):
        """
        Test that start displays welcome and begins conversation loop.
        
        This is the expected use case.
        """
        mock_interface = MagicMock()
        mock_interface_class.return_value = mock_interface
        
        chat_manager = ChatManager()
        
        # Mock the conversation loop to exit immediately
        with patch.object(chat_manager, '_conversation_loop'):
            chat_manager.start()
        
        mock_interface.display_welcome.assert_called_once()
    
    @patch('src.cli.chat.TerminalInterface')
    def test_stop_sets_running_false_and_shows_goodbye(self, mock_interface_class):
        """
        Test that stop sets running flag and displays goodbye.
        
        This is the expected use case for clean exit.
        """
        mock_interface = MagicMock()
        mock_interface_class.return_value = mock_interface
        
        chat_manager = ChatManager()
        chat_manager.stop()
        
        assert chat_manager.running is False
        mock_interface.display_goodbye.assert_called_once()
    
    @patch('src.cli.chat.TerminalInterface')
    def test_is_exit_command_recognizes_quit_variants(self, mock_interface_class):
        """
        Test that is_exit_command recognizes various exit commands.
        
        This is an edge case testing different exit command formats.
        """
        chat_manager = ChatManager()
        
        # Test various exit commands
        assert chat_manager._is_exit_command("quit") is True
        assert chat_manager._is_exit_command("QUIT") is True
        assert chat_manager._is_exit_command("  exit  ") is True
        assert chat_manager._is_exit_command("bye") is True
        assert chat_manager._is_exit_command("goodbye") is True
        assert chat_manager._is_exit_command("hello") is False
        assert chat_manager._is_exit_command("") is False
    
    @patch('src.cli.chat.TerminalInterface')
    def test_process_user_input_handles_empty_input(self, mock_interface_class):
        """
        Test that process_user_input handles empty user input appropriately.
        
        This is an edge case.
        """
        chat_manager = ChatManager()
        
        result = chat_manager._process_user_input("")
        
        assert "I'm here to help" in result
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('src.cli.chat.TerminalInterface')
    def test_signal_handler_calls_stop(self, mock_interface_class):
        """
        Test that signal handler properly calls stop method.
        
        This is a failure case testing interrupt handling.
        """
        mock_interface = MagicMock()
        mock_interface_class.return_value = mock_interface
        
        chat_manager = ChatManager()
        
        # Call signal handler directly
        chat_manager._signal_handler(signal.SIGINT, None)
        
        # Verify it displayed info and stopped
        mock_interface.display_info.assert_called_once()
        assert chat_manager.running is False
    
    @patch('src.cli.chat.TerminalInterface')
    def test_conversation_loop_exits_on_quit(self, mock_interface_class):
        """
        Test that conversation loop exits when user types quit.
        
        This tests the main conversation flow.
        """
        mock_interface = MagicMock()
        mock_interface_class.return_value = mock_interface
        
        # Mock user input to return 'quit'
        mock_interface.get_user_input.return_value = "quit"
        
        chat_manager = ChatManager()
        chat_manager._conversation_loop()
        
        # Should have stopped running
        assert chat_manager.running is False
        mock_interface.display_goodbye.assert_called_once()