"""
Unit tests for config.settings module.

Tests for configuration management including AzureSettings, AppSettings,
and the main Settings class with various scenarios.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.config.settings import (
    AzureSettings,
    AppSettings,
    Settings,
    get_settings,
    reload_settings
)


class TestAzureSettings:
    """Test cases for AzureSettings class."""
    
    def test_azure_settings_defaults(self):
        """Test AzureSettings initialization with defaults."""
        settings = AzureSettings()
        
        assert settings.subscription_id is None
        assert settings.tenant_id is None
        assert settings.client_id is None
        assert settings.client_secret is None
        assert settings.default_location == "East US"
        assert settings.default_resource_group is None
        assert settings.use_azure_cli is True
        assert settings.azure_cli_path == "az"
    
    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_ID': 'test-sub-id',
        'AZURE_TENANT_ID': 'test-tenant-id',
        'AZURE_CLIENT_ID': 'test-client-id',
        'AZURE_CLIENT_SECRET': 'test-secret',
        'AZURE_DEFAULT_LOCATION': 'West US',
        'AZURE_DEFAULT_RESOURCE_GROUP': 'test-rg',
        'USE_AZURE_CLI': 'false',
        'AZURE_CLI_PATH': '/usr/bin/az'
    })
    def test_azure_settings_from_env(self):
        """Test AzureSettings loading from environment variables."""
        settings = AzureSettings()
        
        assert settings.subscription_id == 'test-sub-id'
        assert settings.tenant_id == 'test-tenant-id'
        assert settings.client_id == 'test-client-id'
        assert settings.client_secret == 'test-secret'
        assert settings.default_location == 'West US'
        assert settings.default_resource_group == 'test-rg'
        assert settings.use_azure_cli is False
        assert settings.azure_cli_path == '/usr/bin/az'


class TestAppSettings:
    """Test cases for AppSettings class."""
    
    def test_app_settings_defaults(self):
        """Test AppSettings initialization with defaults."""
        settings = AppSettings()
        
        assert settings.app_name == "Azure Infrastructure Agent"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.log_file is None
        assert settings.enable_file_logging is True
        assert settings.console_width == 120
        assert settings.enable_rich_console is True
        assert settings.templates_dir == "templates"
        assert settings.output_dir == "output"
        assert settings.max_deployment_timeout == 1800
        assert settings.deployment_status_check_interval == 30
    
    @patch.dict(os.environ, {
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': '/var/log/agent.log',
        'ENABLE_FILE_LOGGING': 'false',
        'CONSOLE_WIDTH': '80',
        'ENABLE_RICH_CONSOLE': 'false',
        'TEMPLATES_DIR': 'custom_templates',
        'OUTPUT_DIR': 'custom_output',
        'MAX_DEPLOYMENT_TIMEOUT': '3600',
        'DEPLOYMENT_STATUS_CHECK_INTERVAL': '60'
    })
    def test_app_settings_from_env(self):
        """Test AppSettings loading from environment variables."""
        settings = AppSettings()
        
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.log_file == "/var/log/agent.log"
        assert settings.enable_file_logging is False
        assert settings.console_width == 80
        assert settings.enable_rich_console is False
        assert settings.templates_dir == "custom_templates"
        assert settings.output_dir == "custom_output"
        assert settings.max_deployment_timeout == 3600
        assert settings.deployment_status_check_interval == 60


class TestSettings:
    """Test cases for Settings class."""
    
    @patch('src.config.settings.Path.exists')
    def test_settings_initialization_no_config_file(self, mock_exists):
        """Test Settings initialization without config file."""
        mock_exists.return_value = False
        
        settings = Settings()
        
        assert isinstance(settings.app, AppSettings)
        assert isinstance(settings.azure, AzureSettings)
        assert settings._config_file_path is None
    
    @patch('src.config.settings.Path.exists')
    def test_settings_initialization_with_config_file(self, mock_exists):
        """Test Settings initialization with config file."""
        def exists_side_effect(path_arg=None):
            # Mock that the first config path exists
            if path_arg is None and hasattr(mock_exists, 'call_count'):
                return mock_exists.call_count == 1
            return str(path_arg).endswith('config.json') and mock_exists.call_count == 1
        
        mock_exists.side_effect = exists_side_effect
        
        settings = Settings()
        
        # Should find a config file path
        assert settings._config_file_path is not None
    
    def test_get_templates_dir_success(self):
        """Test getting templates directory path."""
        settings = Settings()
        
        templates_dir = settings.get_templates_dir()
        
        assert isinstance(templates_dir, Path)
        assert templates_dir.name == settings.app.templates_dir
    
    @patch('src.config.settings.Path.mkdir')
    def test_get_output_dir_creates_directory(self, mock_mkdir):
        """Test getting output directory creates it if needed."""
        settings = Settings()
        
        output_dir = settings.get_output_dir()
        
        assert isinstance(output_dir, Path)
        mock_mkdir.assert_called_once_with(exist_ok=True)
    
    def test_get_log_file_path_disabled(self):
        """Test getting log file path when file logging is disabled."""
        with patch.object(AppSettings, 'enable_file_logging', False):
            settings = Settings()
            
            log_path = settings.get_log_file_path()
            
            assert log_path is None
    
    def test_get_log_file_path_custom_file(self):
        """Test getting log file path with custom file."""
        with patch.object(AppSettings, 'log_file', '/custom/log/path.log'):
            settings = Settings()
            
            log_path = settings.get_log_file_path()
            
            assert isinstance(log_path, Path)
            assert str(log_path).endswith('/custom/log/path.log')
    
    @patch('src.config.settings.Path.mkdir')
    def test_get_log_file_path_default_location(self, mock_mkdir):
        """Test getting default log file path."""
        settings = Settings()
        
        log_path = settings.get_log_file_path()
        
        assert isinstance(log_path, Path)
        assert str(log_path).endswith('agent.log')
        mock_mkdir.assert_called_once()
    
    @patch('shutil.which')
    def test_is_azure_cli_available_true(self, mock_which):
        """Test Azure CLI availability check - available."""
        mock_which.return_value = '/usr/bin/az'
        
        settings = Settings()
        
        result = settings.is_azure_cli_available()
        
        assert result is True
        mock_which.assert_called_once_with(settings.azure.azure_cli_path)
    
    @patch('shutil.which')
    def test_is_azure_cli_available_false(self, mock_which):
        """Test Azure CLI availability check - not available."""
        mock_which.return_value = None
        
        settings = Settings()
        
        result = settings.is_azure_cli_available()
        
        assert result is False
    
    def test_is_azure_cli_available_disabled(self):
        """Test Azure CLI availability when disabled in settings."""
        with patch.object(AzureSettings, 'use_azure_cli', False):
            settings = Settings()
            
            result = settings.is_azure_cli_available()
            
            assert result is False
    
    def test_has_service_principal_auth_true(self):
        """Test service principal auth check - configured."""
        with patch.multiple(
            AzureSettings,
            tenant_id='test-tenant',
            client_id='test-client',
            client_secret='test-secret'
        ):
            settings = Settings()
            
            result = settings.has_service_principal_auth()
            
            assert result is True
    
    def test_has_service_principal_auth_false_missing_fields(self):
        """Test service principal auth check - missing fields."""
        with patch.multiple(
            AzureSettings,
            tenant_id='test-tenant',
            client_id=None,  # Missing
            client_secret='test-secret'
        ):
            settings = Settings()
            
            result = settings.has_service_principal_auth()
            
            assert result is False
    
    @patch.object(Settings, 'has_service_principal_auth')
    @patch.object(Settings, 'is_azure_cli_available')
    def test_get_auth_method_service_principal(self, mock_cli, mock_sp):
        """Test auth method detection - service principal."""
        mock_sp.return_value = True
        mock_cli.return_value = False
        
        settings = Settings()
        
        auth_method = settings.get_auth_method()
        
        assert auth_method == "service_principal"
    
    @patch.object(Settings, 'has_service_principal_auth')
    @patch.object(Settings, 'is_azure_cli_available')
    def test_get_auth_method_azure_cli(self, mock_cli, mock_sp):
        """Test auth method detection - Azure CLI."""
        mock_sp.return_value = False
        mock_cli.return_value = True
        
        settings = Settings()
        
        auth_method = settings.get_auth_method()
        
        assert auth_method == "azure_cli"
    
    @patch.object(Settings, 'has_service_principal_auth')
    @patch.object(Settings, 'is_azure_cli_available')
    def test_get_auth_method_none(self, mock_cli, mock_sp):
        """Test auth method detection - none available."""
        mock_sp.return_value = False
        mock_cli.return_value = False
        
        settings = Settings()
        
        auth_method = settings.get_auth_method()
        
        assert auth_method == "none"
    
    def test_to_dict_success(self):
        """Test converting settings to dictionary."""
        settings = Settings()
        
        config_dict = settings.to_dict()
        
        assert "app" in config_dict
        assert "azure" in config_dict
        assert "config_file" in config_dict
        assert "auth_method" in config_dict
        
        # Check that sensitive values are masked
        if settings.azure.client_secret:
            assert config_dict["azure"]["client_secret"] == "***"
    
    def test_to_dict_no_secret(self):
        """Test converting settings to dictionary without client secret."""
        with patch.object(AzureSettings, 'client_secret', None):
            settings = Settings()
            
            config_dict = settings.to_dict()
            
            assert config_dict["azure"]["client_secret"] is None


class TestGlobalFunctions:
    """Test cases for global functions."""
    
    @patch('src.config.settings.settings')
    def test_get_settings_returns_global_instance(self, mock_settings):
        """Test get_settings returns the global settings instance."""
        mock_instance = Mock()
        mock_settings.return_value = mock_instance
        
        result = get_settings()
        
        # Should return the global settings instance
        assert result is not None
    
    @patch('src.config.settings.Settings')
    def test_reload_settings_creates_new_instance(self, mock_settings_class):
        """Test reload_settings creates a new Settings instance."""
        mock_instance = Mock()
        mock_settings_class.return_value = mock_instance
        
        result = reload_settings()
        
        mock_settings_class.assert_called_once()
        assert result == mock_instance


class TestSettingsIntegration:
    """Integration tests for Settings class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.temp_dir
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        if self.original_home:
            os.environ['HOME'] = self.original_home
        else:
            os.environ.pop('HOME', None)
    
    def test_settings_integration_full_cycle(self):
        """Test complete settings workflow."""
        # Create settings instance
        settings = Settings()
        
        # Test directory creation
        output_dir = settings.get_output_dir()
        assert output_dir.exists()
        
        templates_dir = settings.get_templates_dir()
        assert isinstance(templates_dir, Path)
        
        # Test authentication methods
        auth_method = settings.get_auth_method()
        assert auth_method in ["service_principal", "azure_cli", "none"]
        
        # Test dictionary conversion
        config_dict = settings.to_dict()
        assert isinstance(config_dict, dict)
        assert all(key in config_dict for key in ["app", "azure", "config_file", "auth_method"])