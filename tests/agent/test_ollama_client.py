"""
Unit tests for Ollama client functionality.

Tests the OllamaClient class for proper API interaction and error handling.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from src.agent.llm.ollama_client import OllamaClient, OllamaResponse, create_ollama_client


class TestOllamaClient:
    """Test suite for OllamaClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = OllamaClient()
    
    def test_initialization(self):
        """Test client initialization with default values."""
        assert self.client.base_url == "http://localhost:11434"
        assert self.client.timeout == 60
        assert self.client._available_models is None
    
    def test_initialization_custom_values(self):
        """Test client initialization with custom values."""
        client = OllamaClient(base_url="http://custom:8080/", timeout=60)
        assert client.base_url == "http://custom:8080"
        assert client.timeout == 60
    
    @patch('requests.get')
    def test_is_available_success(self, mock_get):
        """Test successful availability check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        assert self.client.is_available() is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)
    
    @patch('requests.get')
    def test_is_available_failure(self, mock_get):
        """Test failed availability check."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        assert self.client.is_available() is False
    
    @patch('requests.get')
    def test_is_available_http_error(self, mock_get):
        """Test availability check with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        assert self.client.is_available() is False
    
    @patch('requests.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "mistral"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Mock is_available to return True
        with patch.object(self.client, 'is_available', return_value=True):
            models = self.client.list_models()
            
        assert models == ["llama3.2:3b", "mistral"]
        assert self.client._available_models == ["llama3.2:3b", "mistral"]
    
    @patch('requests.get')
    def test_list_models_unavailable(self, mock_get):
        """Test model listing when service unavailable."""
        with patch.object(self.client, 'is_available', return_value=False):
            models = self.client.list_models()
            
        assert models == []
        mock_get.assert_not_called()
    
    @patch('requests.post')
    def test_chat_success(self, mock_post):
        """Test successful chat interaction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hello! I can help with Azure storage."}
        }
        mock_post.return_value = mock_response
        
        with patch.object(self.client, 'is_available', return_value=True):
            response = self.client.chat("Hello")
            
        assert response.success is True
        assert response.content == "Hello! I can help with Azure storage."
        assert response.model == "llama3.2:3b"
        assert response.error_message is None
    
    def test_chat_unavailable(self):
        """Test chat when service unavailable."""
        with patch.object(self.client, 'is_available', return_value=False):
            response = self.client.chat("Hello")
            
        assert response.success is False
        assert response.content == ""
        assert "not available" in response.error_message
    
    @patch('requests.post')
    def test_chat_timeout(self, mock_post):
        """Test chat with timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with patch.object(self.client, 'is_available', return_value=True):
            response = self.client.chat("Hello")
            
        assert response.success is False
        assert "timeout" in response.error_message.lower()
    
    @patch('requests.post')
    def test_chat_http_error(self, mock_post):
        """Test chat with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with patch.object(self.client, 'is_available', return_value=True):
            response = self.client.chat("Hello")
            
        assert response.success is False
        assert "500" in response.error_message
    
    @patch('requests.post')
    def test_chat_with_system_prompt(self, mock_post):
        """Test chat with system prompt."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "I'm a storage specialist."}
        }
        mock_post.return_value = mock_response
        
        with patch.object(self.client, 'is_available', return_value=True):
            response = self.client.chat("Hello", system_prompt="You are a storage expert.")
            
        # Verify the payload included system message
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        messages = payload['messages']
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == "You are a storage expert."
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == "Hello"
    
    @patch('requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Generated text response"
        }
        mock_post.return_value = mock_response
        
        with patch.object(self.client, 'is_available', return_value=True):
            response = self.client.generate("Generate text about storage")
            
        assert response.success is True
        assert response.content == "Generated text response"
    
    def test_create_ollama_client(self):
        """Test factory function."""
        client = create_ollama_client()
        assert isinstance(client, OllamaClient)
        assert client.base_url == "http://localhost:11434"


class TestOllamaResponse:
    """Test suite for OllamaResponse dataclass."""
    
    def test_response_creation(self):
        """Test OllamaResponse creation."""
        response = OllamaResponse(
            content="test content",
            model="llama3.2:3b",
            success=True
        )
        
        assert response.content == "test content"
        assert response.model == "llama3.2:3b"
        assert response.success is True
        assert response.error_message is None
    
    def test_response_with_error(self):
        """Test OllamaResponse with error."""
        response = OllamaResponse(
            content="",
            model="llama3.2:3b", 
            success=False,
            error_message="Connection failed"
        )
        
        assert response.content == ""
        assert response.success is False
        assert response.error_message == "Connection failed"