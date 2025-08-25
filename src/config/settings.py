"""
Configuration management for Azure Infrastructure Agent.

This module handles application settings, environment variables,
and configuration loading from various sources.
"""

import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path


class AzureSettings(BaseSettings):
    """Azure-specific configuration settings."""
    
    subscription_id: Optional[str] = Field(None, env="AZURE_SUBSCRIPTION_ID")
    tenant_id: Optional[str] = Field(None, env="AZURE_TENANT_ID")
    client_id: Optional[str] = Field(None, env="AZURE_CLIENT_ID")
    client_secret: Optional[str] = Field(None, env="AZURE_CLIENT_SECRET")
    default_location: str = Field("East US", env="AZURE_DEFAULT_LOCATION")
    default_resource_group: Optional[str] = Field(None, env="AZURE_DEFAULT_RESOURCE_GROUP")
    
    # Azure CLI settings
    use_azure_cli: bool = Field(True, env="USE_AZURE_CLI")
    azure_cli_path: str = Field("az", env="AZURE_CLI_PATH")


class AppSettings(BaseSettings):
    """Application-wide configuration settings."""
    
    # Application info
    app_name: str = "Azure Infrastructure Agent"
    version: str = "1.0.0"
    debug: bool = Field(False, env="DEBUG")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    enable_file_logging: bool = Field(True, env="ENABLE_FILE_LOGGING")
    
    # CLI settings
    console_width: int = Field(120, env="CONSOLE_WIDTH")
    enable_rich_console: bool = Field(True, env="ENABLE_RICH_CONSOLE")
    
    # Template settings
    templates_dir: str = Field("templates", env="TEMPLATES_DIR")
    output_dir: str = Field("output", env="OUTPUT_DIR")
    
    # Deployment settings
    max_deployment_timeout: int = Field(1800, env="MAX_DEPLOYMENT_TIMEOUT")  # 30 minutes
    deployment_status_check_interval: int = Field(30, env="DEPLOYMENT_STATUS_CHECK_INTERVAL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class Settings:
    """
    Main settings class that combines all configuration sources.
    
    This class provides a centralized way to access all application settings
    and handles loading from environment variables, config files, and defaults.
    """
    
    def __init__(self):
        """Initialize settings by loading from various sources."""
        self.app = AppSettings()
        self.azure = AzureSettings()
        self._config_file_path = None
        self._load_config_file()
    
    def _load_config_file(self) -> None:
        """Load additional settings from a JSON config file if it exists."""
        config_paths = [
            Path(".") / "config.json",
            Path.home() / ".azure-infrastructure-agent" / "config.json",
            Path("/etc/azure-infrastructure-agent/config.json")
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                self._config_file_path = str(config_path)
                # TODO: Implement JSON config loading
                break
    
    def get_templates_dir(self) -> Path:
        """
        Get the templates directory path.
        
        Returns:
            Path: The path to the templates directory.
        """
        return Path(self.app.templates_dir).resolve()
    
    def get_output_dir(self) -> Path:
        """
        Get the output directory path.
        
        Returns:
            Path: The path to the output directory.
        """
        output_path = Path(self.app.output_dir)
        output_path.mkdir(exist_ok=True)
        return output_path.resolve()
    
    def get_log_file_path(self) -> Optional[Path]:
        """
        Get the log file path if file logging is enabled.
        
        Returns:
            Optional[Path]: The log file path or None if file logging is disabled.
        """
        if not self.app.enable_file_logging:
            return None
        
        if self.app.log_file:
            return Path(self.app.log_file).resolve()
        
        # Default log file location
        log_dir = Path.home() / ".azure-infrastructure-agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "agent.log"
    
    def is_azure_cli_available(self) -> bool:
        """
        Check if Azure CLI is available and configured.
        
        Returns:
            bool: True if Azure CLI is available, False otherwise.
        """
        if not self.azure.use_azure_cli:
            return False
        
        import shutil
        return shutil.which(self.azure.azure_cli_path) is not None
    
    def has_service_principal_auth(self) -> bool:
        """
        Check if service principal authentication is configured.
        
        Returns:
            bool: True if service principal auth is configured, False otherwise.
        """
        return all([
            self.azure.tenant_id,
            self.azure.client_id,
            self.azure.client_secret
        ])
    
    def get_auth_method(self) -> str:
        """
        Determine the preferred authentication method.
        
        Returns:
            str: The authentication method ('service_principal', 'azure_cli', or 'none').
        """
        if self.has_service_principal_auth():
            return "service_principal"
        elif self.is_azure_cli_available():
            return "azure_cli"
        else:
            return "none"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all settings to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary containing all configuration values.
        """
        return {
            "app": self.app.dict(),
            "azure": {
                **self.azure.dict(),
                # Hide sensitive values
                "client_secret": "***" if self.azure.client_secret else None
            },
            "config_file": self._config_file_path,
            "auth_method": self.get_auth_method()
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: The global settings instance.
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from all sources.
    
    Returns:
        Settings: The reloaded settings instance.
    """
    global settings
    settings = Settings()
    return settings


def mask_subscription_id(subscription_id: Optional[str]) -> str:
    """
    Mask subscription ID to show only the last 4 characters.
    
    Args:
        subscription_id: The subscription ID to mask
        
    Returns:
        str: Masked subscription ID in format "****-xxxx" or "Unknown" if None
    """
    if not subscription_id:
        return "Unknown"
    
    if len(subscription_id) <= 4:
        return subscription_id
    
    return "****-" + subscription_id[-4:]