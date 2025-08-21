"""
Validation result classes for Azure Infrastructure Agent.

This module provides validation result containers and severity levels
for resource parameter validation.
"""

from typing import List, Tuple
from enum import Enum

from ..config.logging import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """
    Container for validation results.
    
    Tracks validation errors, warnings, and info messages
    to provide comprehensive feedback on resource parameters.
    """
    
    def __init__(self):
        """Initialize empty validation result."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str) -> None:
        """
        Add an error message to the validation result.
        
        Args:
            message (str): The error message to add.
        """
        self.errors.append(message)
        logger.debug(f"Validation error: {message}")
    
    def add_warning(self, message: str) -> None:
        """
        Add a warning message to the validation result.
        
        Args:
            message (str): The warning message to add.
        """
        self.warnings.append(message)
        logger.debug(f"Validation warning: {message}")
    
    def add_info(self, message: str) -> None:
        """
        Add an info message to the validation result.
        
        Args:
            message (str): The info message to add.
        """
        self.info.append(message)
        logger.debug(f"Validation info: {message}")
    
    @property
    def is_valid(self) -> bool:
        """
        Check if validation passed (no errors).
        
        Returns:
            bool: True if no errors, False otherwise.
        """
        return len(self.errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """
        Check if validation has warnings.
        
        Returns:
            bool: True if warnings exist, False otherwise.
        """
        return len(self.warnings) > 0
    
    @property
    def message_count(self) -> int:
        """
        Get total count of all messages.
        
        Returns:
            int: Total number of messages (errors + warnings + info).
        """
        return len(self.errors) + len(self.warnings) + len(self.info)
    
    def get_summary(self) -> str:
        """
        Get a summary of validation results.
        
        Returns:
            str: Summary string of validation results.
        """
        if self.is_valid:
            if self.has_warnings:
                return f"Valid with {len(self.warnings)} warning(s)"
            else:
                return "Valid"
        else:
            return f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
    
    def get_all_messages(self) -> List[Tuple[ValidationSeverity, str]]:
        """
        Get all messages with their severity levels.
        
        Returns:
            List[Tuple[ValidationSeverity, str]]: List of (severity, message) tuples.
        """
        messages = []
        
        for error in self.errors:
            messages.append((ValidationSeverity.ERROR, error))
        
        for warning in self.warnings:
            messages.append((ValidationSeverity.WARNING, warning))
        
        for info in self.info:
            messages.append((ValidationSeverity.INFO, info))
        
        return messages