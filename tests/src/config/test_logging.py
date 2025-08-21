"""
Unit tests for config.logging module.

Tests for logging configuration including setup_logging, ContextLogger,
and various logging scenarios.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from src.config.logging import (
    setup_logging,
    get_logger,
    ContextLogger,
    _configure_third_party_loggers
)


class TestSetupLogging:
    """Test cases for setup_logging function."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)
    
    def teardown_method(self):
        """Clean up test environment."""
        # Clear handlers after each test
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_defaults(self, mock_get_settings):
        """Test setup_logging with default settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.app.log_level = "INFO"
        mock_settings.get_log_file_path.return_value = None
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = False
        mock_get_settings.return_value = mock_settings
        
        logger = setup_logging()
        
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # Console handler only
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_with_rich_console(self, mock_get_settings):
        """Test setup_logging with Rich console enabled."""
        mock_settings = Mock()
        mock_settings.app.log_level = "DEBUG"
        mock_settings.get_log_file_path.return_value = None
        mock_settings.app.enable_rich_console = True
        mock_settings.app.enable_file_logging = False
        mock_settings.app.console_width = 120
        mock_get_settings.return_value = mock_settings
        
        with patch('src.config.logging.RichHandler') as mock_rich_handler:
            logger = setup_logging()
            
            mock_rich_handler.assert_called_once()
            assert logger.level == logging.DEBUG
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_with_file_handler(self, mock_get_settings):
        """Test setup_logging with file handler."""
        temp_dir = tempfile.mkdtemp()
        log_file = Path(temp_dir) / "test.log"
        
        mock_settings = Mock()
        mock_settings.app.log_level = "INFO"
        mock_settings.get_log_file_path.return_value = log_file
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = True
        mock_get_settings.return_value = mock_settings
        
        try:
            logger = setup_logging()
            
            assert len(logger.handlers) == 2  # Console + File
            assert log_file.parent.exists()
        finally:
            shutil.rmtree(temp_dir)
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_file_creation_failure(self, mock_get_settings):
        """Test setup_logging when file creation fails."""
        # Use invalid path
        log_file = Path("/invalid/path/test.log")
        
        mock_settings = Mock()
        mock_settings.app.log_level = "INFO"
        mock_settings.get_log_file_path.return_value = log_file
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = True
        mock_get_settings.return_value = mock_settings
        
        logger = setup_logging()
        
        # Should only have console handler (file handler creation failed)
        assert len(logger.handlers) == 1
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_overrides(self, mock_get_settings):
        """Test setup_logging with parameter overrides."""
        mock_settings = Mock()
        mock_settings.app.log_level = "INFO"
        mock_settings.get_log_file_path.return_value = None
        mock_settings.app.enable_rich_console = True
        mock_settings.app.enable_file_logging = False
        mock_get_settings.return_value = mock_settings
        
        logger = setup_logging(
            log_level="ERROR",
            enable_rich=False
        )
        
        assert logger.level == logging.ERROR
        # Should use console handler (not Rich) due to override
        assert len(logger.handlers) == 1
    
    @patch('src.config.logging.get_settings')
    def test_setup_logging_invalid_log_level(self, mock_get_settings):
        """Test setup_logging with invalid log level."""
        mock_settings = Mock()
        mock_settings.app.log_level = "INVALID_LEVEL"
        mock_settings.get_log_file_path.return_value = None
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = False
        mock_get_settings.return_value = mock_settings
        
        logger = setup_logging()
        
        # Should fall back to INFO level
        assert logger.level == logging.INFO


class TestGetLogger:
    """Test cases for get_logger function."""
    
    def test_get_logger_success(self):
        """Test successful logger retrieval."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2
    
    def test_get_logger_same_name_returns_same_instance(self):
        """Test getting logger with same name returns same instance."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2


class TestContextLogger:
    """Test cases for ContextLogger class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Set up a string stream to capture log output
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(self.handler)
        root_logger.setLevel(logging.DEBUG)
    
    def teardown_method(self):
        """Clean up test environment."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
    
    def test_context_logger_initialization_success(self):
        """Test successful ContextLogger initialization."""
        context_logger = ContextLogger("test_module", {"session_id": "123"})
        
        assert context_logger.logger.name == "test_module"
        assert context_logger.context == {"session_id": "123"}
    
    def test_context_logger_initialization_no_context(self):
        """Test ContextLogger initialization without context."""
        context_logger = ContextLogger("test_module")
        
        assert context_logger.logger.name == "test_module"
        assert context_logger.context == {}
    
    def test_context_logger_set_context(self):
        """Test setting context in ContextLogger."""
        context_logger = ContextLogger("test_module")
        
        context_logger.set_context(operation_id="op123", resource_type="storage")
        
        expected_context = {"operation_id": "op123", "resource_type": "storage"}
        assert context_logger.context == expected_context
    
    def test_context_logger_update_context(self):
        """Test updating existing context in ContextLogger."""
        context_logger = ContextLogger("test_module", {"session_id": "123"})
        
        context_logger.set_context(operation_id="op123", session_id="456")
        
        expected_context = {"session_id": "456", "operation_id": "op123"}
        assert context_logger.context == expected_context
    
    def test_context_logger_clear_context(self):
        """Test clearing context in ContextLogger."""
        context_logger = ContextLogger("test_module", {"session_id": "123"})
        
        context_logger.clear_context()
        
        assert context_logger.context == {}
    
    def test_context_logger_format_message_with_context(self):
        """Test message formatting with context."""
        context_logger = ContextLogger("test_module", {"session_id": "123", "op": "deploy"})
        
        formatted = context_logger._format_message("Test message")
        
        assert "[session_id=123 op=deploy] Test message" == formatted
    
    def test_context_logger_format_message_no_context(self):
        """Test message formatting without context."""
        context_logger = ContextLogger("test_module")
        
        formatted = context_logger._format_message("Test message")
        
        assert formatted == "Test message"
    
    def test_context_logger_info_with_context(self):
        """Test info logging with context."""
        context_logger = ContextLogger("test_module", {"session_id": "123"})
        
        context_logger.info("Test info message")
        
        log_output = self.log_stream.getvalue()
        assert "[session_id=123] Test info message" in log_output
    
    def test_context_logger_error_with_context(self):
        """Test error logging with context."""
        context_logger = ContextLogger("test_module", {"op": "deploy"})
        
        context_logger.error("Test error message")
        
        log_output = self.log_stream.getvalue()
        assert "[op=deploy] Test error message" in log_output
    
    def test_context_logger_debug_with_context(self):
        """Test debug logging with context."""
        context_logger = ContextLogger("test_module", {"resource": "storage"})
        
        context_logger.debug("Test debug message")
        
        log_output = self.log_stream.getvalue()
        assert "[resource=storage] Test debug message" in log_output
    
    def test_context_logger_warning_with_context(self):
        """Test warning logging with context."""
        context_logger = ContextLogger("test_module", {"deployment": "test"})
        
        context_logger.warning("Test warning message")
        
        log_output = self.log_stream.getvalue()
        assert "[deployment=test] Test warning message" in log_output
    
    def test_context_logger_critical_with_context(self):
        """Test critical logging with context."""
        context_logger = ContextLogger("test_module", {"error": "critical"})
        
        context_logger.critical("Test critical message")
        
        log_output = self.log_stream.getvalue()
        assert "[error=critical] Test critical message" in log_output
    
    def test_context_logger_without_context_logging(self):
        """Test logging without context still works."""
        context_logger = ContextLogger("test_module")
        
        context_logger.info("Test message without context")
        
        log_output = self.log_stream.getvalue()
        assert "Test message without context" in log_output
        assert "[" not in log_output  # No context brackets


class TestConfigureThirdPartyLoggers:
    """Test cases for _configure_third_party_loggers function."""
    
    def test_configure_third_party_loggers_success(self):
        """Test successful configuration of third-party loggers."""
        # Get initial levels
        azure_core_logger = logging.getLogger("azure.core")
        urllib3_logger = logging.getLogger("urllib3")
        click_logger = logging.getLogger("click")
        
        # Set to DEBUG to test the function changes them
        azure_core_logger.setLevel(logging.DEBUG)
        urllib3_logger.setLevel(logging.DEBUG)
        click_logger.setLevel(logging.DEBUG)
        
        _configure_third_party_loggers()
        
        # Should be set to WARNING
        assert azure_core_logger.level == logging.WARNING
        assert urllib3_logger.level == logging.WARNING
        assert click_logger.level == logging.WARNING
    
    def test_configure_third_party_loggers_all_libraries(self):
        """Test configuration of all third-party library loggers."""
        library_loggers = [
            "azure.core",
            "azure.identity", 
            "azure.mgmt",
            "urllib3",
            "requests",
            "click"
        ]
        
        # Set all to DEBUG first
        for lib in library_loggers:
            logging.getLogger(lib).setLevel(logging.DEBUG)
        
        _configure_third_party_loggers()
        
        # All should be set to WARNING
        for lib in library_loggers:
            logger = logging.getLogger(lib)
            assert logger.level == logging.WARNING


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        
        # Clear handlers after each test
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.NOTSET)
    
    @patch('src.config.logging.get_settings')
    def test_full_logging_workflow(self, mock_get_settings):
        """Test complete logging workflow."""
        log_file = Path(self.temp_dir) / "test.log"
        
        mock_settings = Mock()
        mock_settings.app.log_level = "DEBUG"
        mock_settings.get_log_file_path.return_value = log_file
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = True
        mock_get_settings.return_value = mock_settings
        
        # Set up logging
        logger = setup_logging()
        
        # Create context logger
        context_logger = ContextLogger("test_module", {"session_id": "test123"})
        
        # Log various levels
        context_logger.debug("Debug message")
        context_logger.info("Info message")
        context_logger.warning("Warning message")
        context_logger.error("Error message")
        
        # Check file was created and contains messages
        assert log_file.exists()
        
        log_content = log_file.read_text()
        assert "[session_id=test123] Debug message" in log_content
        assert "[session_id=test123] Info message" in log_content
        assert "[session_id=test123] Warning message" in log_content
        assert "[session_id=test123] Error message" in log_content
    
    @patch('src.config.logging.get_settings')
    def test_logger_hierarchy(self, mock_get_settings):
        """Test logger hierarchy and inheritance."""
        mock_settings = Mock()
        mock_settings.app.log_level = "INFO"
        mock_settings.get_log_file_path.return_value = None
        mock_settings.app.enable_rich_console = False
        mock_settings.app.enable_file_logging = False
        mock_get_settings.return_value = mock_settings
        
        # Set up logging
        setup_logging()
        
        # Get loggers at different levels
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        
        assert parent_logger.name == "parent"
        assert child_logger.name == "parent.child"
        assert child_logger.parent == parent_logger