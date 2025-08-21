"""
Logging configuration for Azure Infrastructure Agent.

This module sets up structured logging with support for both console
and file output, configurable log levels, and Rich formatting.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from .settings import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_rich: Optional[bool] = None
) -> logging.Logger:
    """
    Set up application logging with console and file handlers.
    
    Args:
        log_level (Optional[str]): Log level override.
        log_file (Optional[Path]): Log file path override.
        enable_rich (Optional[bool]): Enable Rich console formatting override.
        
    Returns:
        logging.Logger: Configured root logger.
    """
    settings = get_settings()
    
    # Use overrides or fall back to settings
    log_level = log_level or settings.app.log_level
    log_file = log_file or settings.get_log_file_path()
    enable_rich = enable_rich if enable_rich is not None else settings.app.enable_rich_console
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        fmt="%(levelname)s - %(message)s"
    )
    
    # Console handler
    if enable_rich:
        console = Console(width=settings.app.console_width)
        console_handler = RichHandler(
            console=console,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_suppress=[
                # Suppress common library tracebacks for cleaner output
                "click",
                "rich",
                "pydantic"
            ]
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
    
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if log_file and settings.app.enable_file_logging:
        try:
            # Ensure log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent large log files
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(log_file),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(detailed_formatter)
            file_handler.setLevel(logging.DEBUG)  # Always debug level for file
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            # If file logging fails, log to console
            root_logger.error(f"Failed to set up file logging: {e}")
    
    # Set specific loggers to appropriate levels
    _configure_third_party_loggers()
    
    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    return root_logger


def _configure_third_party_loggers() -> None:
    """Configure logging levels for third-party libraries to reduce noise."""
    # Azure SDK loggers
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("azure.mgmt").setLevel(logging.WARNING)
    
    # HTTP libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # CLI libraries
    logging.getLogger("click").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name (str): The logger name (typically __name__).
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    return logging.getLogger(name)


class ContextLogger:
    """
    Context-aware logger that can track operation context.
    
    This logger adds contextual information like operation IDs,
    resource names, and deployment states to log messages.
    """
    
    def __init__(self, name: str, context: Optional[dict] = None):
        """
        Initialize context logger.
        
        Args:
            name (str): The logger name.
            context (Optional[dict]): Additional context to include in logs.
        """
        self.logger = get_logger(name)
        self.context = context or {}
    
    def _format_message(self, message: str) -> str:
        """
        Format message with context information.
        
        Args:
            message (str): The base log message.
            
        Returns:
            str: Formatted message with context.
        """
        if not self.context:
            return message
        
        context_parts = []
        for key, value in self.context.items():
            context_parts.append(f"{key}={value}")
        
        context_str = " ".join(context_parts)
        return f"[{context_str}] {message}"
    
    def set_context(self, **kwargs) -> None:
        """
        Update the logging context.
        
        Args:
            **kwargs: Context key-value pairs.
        """
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context information."""
        self.context.clear()
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message with context."""
        self.logger.debug(self._format_message(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message with context."""
        self.logger.info(self._format_message(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message with context."""
        self.logger.warning(self._format_message(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message with context."""
        self.logger.error(self._format_message(message), *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message with context."""
        self.logger.critical(self._format_message(message), *args, **kwargs)


# Initialize logging on import if not already configured
if not logging.getLogger().handlers:
    setup_logging()