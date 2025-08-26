"""
Ollama API client for local LLM inference.

This module provides a simple wrapper around Ollama's REST API for local
language model inference without external API costs.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """Response from Ollama API."""
    content: str
    model: str
    success: bool
    error_message: Optional[str] = None


class OllamaClient:
    """
    Client for interacting with local Ollama LLM API.
    
    Provides a simple interface for chat completions using locally running
    Ollama models with graceful fallback when service is unavailable.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        """
        Initialize Ollama client.
        
        Args:
            base_url (str): Ollama server URL.
            timeout (int): Request timeout in seconds.
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._available_models: Optional[List[str]] = None
        
    def is_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            bool: True if Ollama is running and accessible.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False
            
    def list_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List[str]: Available model names.
        """
        if not self.is_available():
            return []
            
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                self._available_models = models
                return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            
        return []
        
    def chat(self, message: str, model: str = "llama3.1", system_prompt: Optional[str] = None) -> OllamaResponse:
        """
        Send chat message to Ollama model.
        
        Args:
            message (str): User message to send.
            model (str): Model name to use.
            system_prompt (str, optional): System prompt for context.
            
        Returns:
            OllamaResponse: Model response with success status.
        """
        if not self.is_available():
            return OllamaResponse(
                content="",
                model=model,
                success=False,
                error_message="Ollama service is not available. Please install and start Ollama."
            )
            
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False  # Get complete response
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                return OllamaResponse(
                    content=content,
                    model=model,
                    success=True
                )
            else:
                error_msg = f"Ollama API error: {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                
                return OllamaResponse(
                    content="",
                    model=model,
                    success=False,
                    error_message=error_msg
                )
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(error_msg)
            
            return OllamaResponse(
                content="",
                model=model,
                success=False,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Error calling Ollama API: {str(e)}"
            logger.error(error_msg)
            
            return OllamaResponse(
                content="",
                model=model,
                success=False,
                error_message=error_msg
            )
            
    def generate(self, prompt: str, model: str = "llama3.1") -> OllamaResponse:
        """
        Generate text completion using Ollama model.
        
        Args:
            prompt (str): Text prompt for generation.
            model (str): Model name to use.
            
        Returns:
            OllamaResponse: Generated text with success status.
        """
        if not self.is_available():
            return OllamaResponse(
                content="",
                model=model,
                success=False,
                error_message="Ollama service is not available. Please install and start Ollama."
            )
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "")
                
                return OllamaResponse(
                    content=content,
                    model=model,
                    success=True
                )
            else:
                error_msg = f"Ollama API error: {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                
                return OllamaResponse(
                    content="",
                    model=model,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error calling Ollama API: {str(e)}"
            logger.error(error_msg)
            
            return OllamaResponse(
                content="",
                model=model,
                success=False,
                error_message=error_msg
            )


def create_ollama_client() -> OllamaClient:
    """
    Factory function to create Ollama client.
    
    Returns:
        OllamaClient: Configured Ollama client instance.
    """
    return OllamaClient()