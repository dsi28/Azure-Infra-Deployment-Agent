"""
OLLAMA-based intent classifier for enhanced natural language understanding.

This module provides OLLAMA integration for intent classification that works
as an enhancement to the existing keyword-based intent parser. It uses the
same Intent enum and IntentMatch structures for seamless integration.
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..agents.intent_parser import Intent, IntentMatch
from ..config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for OLLAMA integration."""
    
    enabled: bool = True
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout: float = 10.0
    confidence_threshold: float = 0.7


class OllamaIntentClassifier:
    """
    OLLAMA-based intent classifier that enhances keyword-based classification.
    
    This classifier uses OLLAMA to understand natural language intent and maps
    it to the existing Intent enum values. It provides confidence scores and
    graceful fallback when OLLAMA is unavailable.
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize the OLLAMA intent classifier.
        
        Args:
            config (OllamaConfig, optional): OLLAMA configuration. Uses defaults if None.
        """
        self.config = config or OllamaConfig()
        self._ollama_client = None
        self._is_available = False
        
        if self.config.enabled:
            self._initialize_ollama()
        
        logger.info(f"OllamaIntentClassifier initialized (enabled={self.config.enabled}, "
                   f"available={self._is_available})")
    
    def _initialize_ollama(self) -> None:
        """Initialize OLLAMA client and check availability."""
        try:
            import ollama
            self._ollama_client = ollama.Client(host=self.config.base_url)
            
            # Test connection with a simple request
            self._test_ollama_connection()
            self._is_available = True
            
        except ImportError:
            logger.warning("ollama package not installed. LLM intent enhancement disabled.")
            self._is_available = False
            
        except Exception as e:
            logger.warning(f"Failed to connect to OLLAMA: {e}. Using keyword-based fallback.")
            self._is_available = False
    
    def _test_ollama_connection(self) -> None:
        """Test OLLAMA connection with a simple request."""
        try:
            # Simple test to verify the model is available
            response = self._ollama_client.generate(
                model=self.config.model,
                prompt="Test",
                stream=False,
                options={'num_predict': 1}
            )
            
            if not response or 'response' not in response:
                raise ValueError("Invalid OLLAMA response format")
                
        except Exception as e:
            raise ConnectionError(f"OLLAMA connection test failed: {e}")
    
    def is_available(self) -> bool:
        """
        Check if OLLAMA is available and enabled.
        
        Returns:
            bool: True if OLLAMA is available and enabled, False otherwise.
        """
        return self.config.enabled and self._is_available
    
    def classify_intent(self, text: str) -> Optional[IntentMatch]:
        """
        Classify intent using OLLAMA with natural language understanding.
        
        Args:
            text (str): The input text to classify.
            
        Returns:
            Optional[IntentMatch]: The intent match if successful, None if failed or unavailable.
        """
        if not self.is_available():
            return None
        
        try:
            # Create prompt for intent classification
            prompt = self._create_classification_prompt(text)
            
            # Get response from OLLAMA
            response = self._ollama_client.generate(
                model=self.config.model,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.1,  # Low temperature for consistent classification
                    'num_predict': 100,  # Limit response length
                    'top_p': 0.9
                }
            )
            
            if not response or 'response' not in response:
                logger.warning("Invalid OLLAMA response format")
                return None
            
            # Parse the response
            intent_match = self._parse_ollama_response(response['response'], text)
            
            if intent_match and intent_match.confidence >= self.config.confidence_threshold:
                logger.debug(f"OLLAMA classified intent: {intent_match.intent.value} "
                           f"(confidence: {intent_match.confidence:.2f})")
                return intent_match
            else:
                logger.debug(f"OLLAMA confidence too low: {intent_match.confidence if intent_match else 0:.2f}")
                return None
                
        except Exception as e:
            logger.warning(f"OLLAMA intent classification failed: {e}")
            return None
    
    def _create_classification_prompt(self, text: str) -> str:
        """
        Create a structured prompt for intent classification.
        
        Args:
            text (str): The user input text.
            
        Returns:
            str: The formatted prompt for OLLAMA.
        """
        # Define the available intents with descriptions
        intent_descriptions = {
            "create_storage_account": "User wants to create an Azure storage account, blob storage, or file storage",
            "create_web_app": "User wants to create a web application, app service, or website",
            "create_function_app": "User wants to create a serverless function or Azure function app",
            "create_app_service_plan": "User wants to create an app service plan or hosting plan",
            "create_resource_group": "User wants to create a resource group",
            "create_virtual_network": "User wants to create a virtual network, VNet, or subnet",
            "list_resources": "User wants to see existing resources or inventory",
            "delete_resource": "User wants to delete, remove, or clean up resources",
            "deploy_template": "User wants to deploy infrastructure templates or ARM templates",
            "validate_template": "User wants to validate or check templates",
            "preview_template": "User wants to preview or see what will be created",
            "get_help": "User is asking for help, usage instructions, or guidance",
            "get_status": "User wants to check deployment status or progress",
            "greeting": "User is greeting or saying hello",
            "goodbye": "User is saying goodbye, thanking, or ending conversation",
            "unknown": "User intent is unclear or doesn't match any specific category"
        }
        
        intent_list = "\n".join([f"- {intent}: {desc}" for intent, desc in intent_descriptions.items()])
        
        return f"""Classify the user's intent for Azure infrastructure management. 

User input: "{text}"

Available intents:
{intent_list}

Respond with ONLY a JSON object in this exact format:
{{"intent": "intent_name", "confidence": 0.95, "reasoning": "brief explanation"}}

The confidence should be between 0.0 and 1.0. Use "unknown" if the intent is unclear."""
    
    def _parse_ollama_response(self, response_text: str, original_text: str) -> Optional[IntentMatch]:
        """
        Parse OLLAMA response into an IntentMatch object.
        
        Args:
            response_text (str): Raw response from OLLAMA.
            original_text (str): Original user input.
            
        Returns:
            Optional[IntentMatch]: Parsed intent match or None if parsing failed.
        """
        try:
            # Try to extract JSON from the response
            response_text = response_text.strip()
            
            # Find JSON content (handle cases where OLLAMA adds extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in OLLAMA response")
                return None
            
            json_content = response_text[start_idx:end_idx]
            response_data = json.loads(json_content)
            
            # Validate required fields
            if 'intent' not in response_data or 'confidence' not in response_data:
                logger.warning("Missing required fields in OLLAMA response")
                return None
            
            # Map intent string to Intent enum
            intent_str = response_data['intent'].lower()
            try:
                intent = Intent(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent from OLLAMA: {intent_str}")
                intent = Intent.UNKNOWN
            
            confidence = float(response_data['confidence'])
            reasoning = response_data.get('reasoning', 'OLLAMA classification')
            
            # Extract keywords mentioned in reasoning or use original text words
            keywords = self._extract_keywords_from_text(original_text)
            
            return IntentMatch(
                intent=intent,
                confidence=confidence,
                keywords=keywords,
                reasoning=f"OLLAMA: {reasoning}"
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse OLLAMA response: {e}")
            return None
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """
        Extract relevant keywords from the input text.
        
        Args:
            text (str): Input text to extract keywords from.
            
        Returns:
            List[str]: List of extracted keywords.
        """
        # Simple keyword extraction - could be enhanced
        import re
        
        # Remove common stop words and extract meaningful terms
        stop_words = {'i', 'need', 'want', 'can', 'you', 'please', 'help', 'me', 'to', 'a', 'an', 'the'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords[:5]  # Limit to 5 keywords
    
    def get_config(self) -> OllamaConfig:
        """
        Get the current OLLAMA configuration.
        
        Returns:
            OllamaConfig: Current configuration.
        """
        return self.config
    
    def update_config(self, **kwargs) -> None:
        """
        Update OLLAMA configuration.
        
        Args:
            **kwargs: Configuration parameters to update.
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Reinitialize if configuration changed
        if self.config.enabled and not self._is_available:
            self._initialize_ollama()
        elif not self.config.enabled:
            self._is_available = False
            
        logger.info(f"OLLAMA configuration updated (enabled={self.config.enabled}, "
                   f"available={self._is_available})")