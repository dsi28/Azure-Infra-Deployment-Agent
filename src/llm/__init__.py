"""
LLM integration module for Azure Infrastructure Agent.

This module provides OLLAMA-based intent classification capabilities
that enhance the existing keyword-based intent parser with natural
language understanding.
"""

from .ollama_intent_classifier import OllamaIntentClassifier

__all__ = ["OllamaIntentClassifier"]