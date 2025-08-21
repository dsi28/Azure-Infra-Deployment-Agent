"""
Test cases for src/main.py
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main


class TestMain:
    """Test cases for main module."""

    @patch('main.ChatManager')
    def test_main_starts_chat_manager(self, mock_chat_manager_class):
        """
        Test that main function creates and starts ChatManager.
        
        This is the expected use case.
        """
        mock_chat_manager = MagicMock()
        mock_chat_manager_class.return_value = mock_chat_manager
        
        runner = CliRunner()
        result = runner.invoke(main, catch_exceptions=False)
        
        mock_chat_manager_class.assert_called_once()
        mock_chat_manager.start.assert_called_once()
        assert result.exit_code == 0

    def test_main_shows_version(self):
        """
        Test that main function shows version when --version flag is used.
        
        This is an edge case for CLI functionality.
        """
        runner = CliRunner()
        result = runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert "Azure Infrastructure Agent" in result.output
        assert "1.0.0" in result.output

    @patch('main.ChatManager', side_effect=Exception("ChatManager failed"))
    def test_main_handles_chat_manager_failure(self, mock_chat_manager_class):
        """
        Test behavior when ChatManager initialization fails.
        
        This is a failure case to test exception handling.
        """
        runner = CliRunner()
        result = runner.invoke(main)
        
        assert result.exit_code == 1  # Abort exit code
        assert "Error starting Azure Infrastructure Agent" in result.output