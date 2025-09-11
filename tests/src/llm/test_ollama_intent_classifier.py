"""
Unit tests for OLLAMA intent classifier.

These tests verify the OLLAMA integration functionality including:
- Configuration handling
- Connection testing
- Intent classification
- Error handling and graceful fallback
- Response parsing
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.llm.ollama_intent_classifier import (
    OllamaIntentClassifier, 
    OllamaConfig
)
from src.agents.intent_parser import Intent, IntentMatch


class TestOllamaConfig:
    """Test OLLAMA configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = OllamaConfig()
        
        assert config.enabled is True
        assert config.base_url == "http://localhost:11434"
        assert config.model == "llama3.1"
        assert config.timeout == 10.0
        assert config.confidence_threshold == 0.7
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = OllamaConfig(
            enabled=False,
            base_url="http://custom:8080",
            model="llama3.2",
            timeout=5.0,
            confidence_threshold=0.8
        )
        
        assert config.enabled is False
        assert config.base_url == "http://custom:8080"
        assert config.model == "llama3.2"
        assert config.timeout == 5.0
        assert config.confidence_threshold == 0.8


class TestOllamaIntentClassifier:
    """Test OLLAMA intent classifier functionality."""
    
    def test_init_disabled(self):
        """Test initialization with OLLAMA disabled."""
        config = OllamaConfig(enabled=False)
        classifier = OllamaIntentClassifier(config)
        
        assert classifier.config.enabled is False
        assert classifier.is_available() is False
        assert classifier._ollama_client is None
    
    def test_init_enabled_but_unavailable(self):
        """Test initialization with OLLAMA enabled but unavailable."""
        # Mock import error by patching the import in the classifier
        with patch('src.llm.ollama_intent_classifier.ollama', side_effect=ImportError("ollama not installed")):
            classifier = OllamaIntentClassifier()
            
            assert classifier.config.enabled is True
            assert classifier.is_available() is False
    
    def test_init_connection_failure(self):
        """Test initialization with connection failure."""
        # Mock connection failure
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            mock_client = Mock()
            mock_client.generate.side_effect = Exception("Connection failed")
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            assert classifier.config.enabled is True
            assert classifier.is_available() is False
    
    def test_init_successful(self):
        """Test successful initialization."""
        # Mock successful connection
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            assert classifier.config.enabled is True
            assert classifier.is_available() is True
            mock_client.generate.assert_called_once()
    
    def test_classify_intent_unavailable(self):
        """Test intent classification when OLLAMA is unavailable."""
        config = OllamaConfig(enabled=False)
        classifier = OllamaIntentClassifier(config)
        
        result = classifier.classify_intent("I need a storage account")
        
        assert result is None
    
    def test_classify_intent_success(self):
        """Test successful intent classification."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            
            # Mock successful initialization
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock classification response
            classification_response = {
                'response': '{"intent": "create_storage_account", "confidence": 0.95, "reasoning": "User wants storage"}'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent("I need a storage account")
            
            assert result is not None
            assert isinstance(result, IntentMatch)
            assert result.intent == Intent.CREATE_STORAGE_ACCOUNT
            assert result.confidence == 0.95
            assert "OLLAMA:" in result.reasoning
            assert len(result.keywords) > 0
    
    def test_classify_intent_low_confidence(self):
        """Test intent classification with low confidence."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock low confidence response
            classification_response = {
                'response': '{"intent": "unknown", "confidence": 0.3, "reasoning": "Unclear intent"}'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent("unclear input")
            
            # Should return None due to low confidence
            assert result is None
    
    def test_classify_intent_invalid_json(self):
        """Test handling of invalid JSON response."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock invalid JSON response
            classification_response = {
                'response': 'This is not JSON'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent("test input")
            
            assert result is None
    
    def test_classify_intent_missing_fields(self):
        """Test handling of response with missing required fields."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock response with missing confidence
            classification_response = {
                'response': '{"intent": "create_storage_account", "reasoning": "User wants storage"}'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent("test input")
            
            assert result is None
    
    def test_classify_intent_unknown_intent(self):
        """Test handling of unknown intent from OLLAMA."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock response with unknown intent
            classification_response = {
                'response': '{"intent": "invalid_intent", "confidence": 0.9, "reasoning": "Test"}'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent("test input")
            
            assert result is not None
            assert result.intent == Intent.UNKNOWN
            assert result.confidence == 0.9
    
    def test_classify_intent_ollama_exception(self):
        """Test handling of OLLAMA generation exception."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock generation exception
            mock_client.generate.side_effect = Exception("OLLAMA error")
            
            result = classifier.classify_intent("test input")
            
            assert result is None
    
    def test_extract_keywords_from_text(self):
        """Test keyword extraction from text."""
        config = OllamaConfig(enabled=False)
        classifier = OllamaIntentClassifier(config)
        
        keywords = classifier._extract_keywords_from_text("I need a storage account for my web app")
        
        assert "storage" in keywords
        assert "account" in keywords
        assert "web" in keywords
        assert "app" in keywords
        # Should exclude stop words
        assert "need" not in keywords
        assert "for" not in keywords
        assert "my" not in keywords
    
    def test_create_classification_prompt(self):
        """Test creation of classification prompt."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock for initialization
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            prompt = classifier._create_classification_prompt("I need storage")
            
            assert "I need storage" in prompt
            assert "create_storage_account" in prompt
            assert "JSON object" in prompt
            assert "confidence" in prompt
    
    def test_parse_ollama_response_with_extra_text(self):
        """Test parsing OLLAMA response with extra text around JSON."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock for initialization
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            response_text = 'Here is the classification: {"intent": "create_web_app", "confidence": 0.8, "reasoning": "Web app request"} Hope this helps!'
            
            result = classifier._parse_ollama_response(response_text, "create web app")
            
            assert result is not None
            assert result.intent == Intent.CREATE_WEB_APP
            assert result.confidence == 0.8
    
    def test_get_config(self):
        """Test getting current configuration."""
        config = OllamaConfig(model="custom-model")
        classifier = OllamaIntentClassifier(config)
        
        retrieved_config = classifier.get_config()
        
        assert retrieved_config.model == "custom-model"
        assert retrieved_config is config
    
    def test_update_config(self):
        """Test updating configuration."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock for initialization
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Update configuration
            classifier.update_config(model="new-model", confidence_threshold=0.9)
            
            assert classifier.config.model == "new-model"
            assert classifier.config.confidence_threshold == 0.9
    
    def test_update_config_enable_when_disabled(self):
        """Test updating configuration to enable when disabled."""
        config = OllamaConfig(enabled=False)
        classifier = OllamaIntentClassifier(config)
        
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier.update_config(enabled=True)
            
            assert classifier.config.enabled is True
            # Should attempt to initialize OLLAMA
            mock_ollama.Client.assert_called_once()


class TestOllamaIntentClassifierIntegration:
    """Integration tests for OLLAMA intent classifier."""
    
    @pytest.mark.parametrize("user_input,expected_intent", [
        ("I need a storage account", Intent.CREATE_STORAGE_ACCOUNT),
        ("Create a web app", Intent.CREATE_WEB_APP),
        ("I want to deploy a function", Intent.CREATE_FUNCTION_APP),
        ("Show me my resources", Intent.LIST_RESOURCES),
        ("Help me", Intent.GET_HELP),
        ("Hello", Intent.GREETING),
        ("Thank you, goodbye", Intent.GOODBYE),
    ])
    def test_classify_various_intents(self, user_input, expected_intent):
        """Test classification of various intent types."""
        with patch('src.llm.ollama_intent_classifier.ollama') as mock_ollama:
            # Setup mock
            mock_client = Mock()
            mock_client.generate.return_value = {'response': 'test'}
            mock_ollama.Client.return_value = mock_client
            
            classifier = OllamaIntentClassifier()
            
            # Mock appropriate response
            classification_response = {
                'response': f'{{"intent": "{expected_intent.value}", "confidence": 0.9, "reasoning": "Test classification"}}'
            }
            mock_client.generate.return_value = classification_response
            
            result = classifier.classify_intent(user_input)
            
            assert result is not None
            assert result.intent == expected_intent
            assert result.confidence == 0.9