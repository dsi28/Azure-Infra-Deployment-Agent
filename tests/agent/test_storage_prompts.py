"""
Unit tests for storage prompt functionality.

Tests the storage prompt templates and formatting functions.
"""

import pytest
from src.agent.llm.storage_prompts import (
    STORAGE_AGENT_SYSTEM_PROMPT,
    EXTRACT_REQUIREMENTS_PROMPT,
    SUGGEST_CONFIG_PROMPT,
    CONVERSATIONAL_RESPONSE_PROMPT,
    format_extract_requirements_prompt,
    format_suggest_config_prompt,
    format_conversational_response_prompt
)


class TestStoragePrompts:
    """Test suite for storage prompt templates."""
    
    def test_system_prompt_content(self):
        """Test storage agent system prompt contains key information."""
        prompt = STORAGE_AGENT_SYSTEM_PROMPT
        
        # Check for key storage concepts
        assert "Azure Storage Account" in prompt
        assert "Performance Tiers" in prompt
        assert "Access Tiers" in prompt
        assert "Replication" in prompt
        
        # Check for specific tiers mentioned
        assert "Hot" in prompt
        assert "Cool" in prompt
        assert "Archive" in prompt
        assert "Standard" in prompt
        assert "Premium" in prompt
        
        # Check for replication types
        assert "LRS" in prompt
        assert "GRS" in prompt
        assert "ZRS" in prompt
    
    def test_extract_requirements_prompt_content(self):
        """Test requirements extraction prompt structure."""
        prompt = EXTRACT_REQUIREMENTS_PROMPT
        
        assert "{user_input}" in prompt
        assert "JSON format" in prompt
        assert "use_case" in prompt
        assert "performance_needs" in prompt
        assert "access_frequency" in prompt
        assert "durability_needs" in prompt
    
    def test_suggest_config_prompt_content(self):
        """Test configuration suggestion prompt structure."""
        prompt = SUGGEST_CONFIG_PROMPT
        
        assert "{requirements}" in prompt
        assert "{user_preferences}" in prompt
        assert "performance_tier" in prompt
        assert "access_tier" in prompt
        assert "replication_type" in prompt
        assert "reasoning" in prompt
    
    def test_conversational_response_prompt_content(self):
        """Test conversational response prompt structure."""
        prompt = CONVERSATIONAL_RESPONSE_PROMPT
        
        assert "{configuration}" in prompt
        assert "{context}" in prompt
        assert "natural" in prompt
        assert "confirmation" in prompt


class TestPromptFormatters:
    """Test suite for prompt formatting functions."""
    
    def test_format_extract_requirements_prompt(self):
        """Test requirements extraction prompt formatting."""
        user_input = "I need storage for my blog images"
        
        formatted = format_extract_requirements_prompt(user_input)
        
        assert user_input in formatted
        assert "User request:" in formatted
        assert "JSON format" in formatted
        
        # Ensure the placeholder was replaced
        assert "{user_input}" not in formatted
    
    def test_format_suggest_config_prompt(self):
        """Test configuration suggestion prompt formatting."""
        requirements = {
            "use_case": "blog images",
            "performance_needs": "cost-effective",
            "access_frequency": "frequent"
        }
        user_preferences = {
            "preferred_regions": ["eastus"],
            "cost_preference": "optimized"
        }
        
        formatted = format_suggest_config_prompt(requirements, user_preferences)
        
        assert str(requirements) in formatted
        assert str(user_preferences) in formatted
        
        # Ensure placeholders were replaced
        assert "{requirements}" not in formatted
        assert "{user_preferences}" not in formatted
    
    def test_format_conversational_response_prompt(self):
        """Test conversational response prompt formatting."""
        configuration = {
            "performance_tier": "Standard",
            "access_tier": "Hot",
            "replication_type": "LRS"
        }
        context = {
            "use_case": "blog images",
            "user_name": "John"
        }
        
        formatted = format_conversational_response_prompt(configuration, context)
        
        assert str(configuration) in formatted
        assert str(context) in formatted
        
        # Ensure placeholders were replaced
        assert "{configuration}" not in formatted
        assert "{context}" not in formatted
    
    def test_format_extract_requirements_empty_input(self):
        """Test requirements extraction with empty input."""
        user_input = ""
        
        formatted = format_extract_requirements_prompt(user_input)
        
        assert 'User request: ""' in formatted
        assert "{user_input}" not in formatted
    
    def test_format_suggest_config_empty_dicts(self):
        """Test config suggestion with empty dictionaries."""
        requirements = {}
        user_preferences = {}
        
        formatted = format_suggest_config_prompt(requirements, user_preferences)
        
        assert str(requirements) in formatted
        assert str(user_preferences) in formatted
    
    def test_format_conversational_response_complex_data(self):
        """Test conversational response with complex nested data."""
        configuration = {
            "performance_tier": "Premium",
            "access_tier": "Hot",
            "replication_type": "ZRS",
            "reasoning": "High-performance requirements with zone redundancy"
        }
        context = {
            "use_case": "database storage",
            "previous_deployments": ["storage1", "storage2"],
            "user_preferences": {
                "region": "eastus",
                "naming_pattern": "descriptive"
            }
        }
        
        formatted = format_conversational_response_prompt(configuration, context)
        
        # Should contain the complex data structures
        assert "Premium" in formatted
        assert "database storage" in formatted
        assert "storage1" in formatted
        assert "eastus" in formatted