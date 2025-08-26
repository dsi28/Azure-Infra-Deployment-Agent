#!/usr/bin/env python3
"""
Test script for Day 1: Local LLM Setup

Tests the Ollama client and storage prompts to verify the setup works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.llm.ollama_client import create_ollama_client
from src.agent.llm.storage_prompts import (
    STORAGE_AGENT_SYSTEM_PROMPT,
    format_extract_requirements_prompt,
    format_conversational_response_prompt
)


def test_ollama_availability():
    """Test if Ollama is available and responsive."""
    print("=" * 50)
    print("Testing Ollama Availability")
    print("=" * 50)
    
    client = create_ollama_client()
    
    # Test availability
    is_available = client.is_available()
    print(f"Ollama Available: {is_available}")
    
    if not is_available:
        print("\n! Ollama is not running.")
        print("To install and start Ollama:")
        print("1. Visit: https://ollama.ai")
        print("2. Download and install Ollama")
        print("3. Run: ollama pull llama3.2:3b")
        print("4. Ollama should start automatically")
        return False
        
    # Test model listing
    models = client.list_models()
    print(f"Available Models: {models}")
    
    if not models:
        print("\n! No models found.")
        print("Run: ollama pull llama3.2:3b")
        return False
        
    return True


def test_basic_chat():
    """Test basic chat functionality."""
    print("\n" + "=" * 50)
    print("Testing Basic Chat")
    print("=" * 50)
    
    client = create_ollama_client()
    
    # Test simple chat
    response = client.chat("Hello! Can you help me with Azure storage?")
    
    print(f"Success: {response.success}")
    print(f"Model: {response.model}")
    
    if response.success:
        print(f"Response: {response.content[:200]}...")
    else:
        print(f"Error: {response.error_message}")
        
    return response.success


def test_storage_prompts():
    """Test storage-specific prompts."""
    print("\n" + "=" * 50)
    print("Testing Storage Prompts")
    print("=" * 50)
    
    # Use longer timeout for complex storage prompts
    client = create_ollama_client(timeout=90)
    
    # Test storage agent system prompt
    test_request = "I need storage for my blog images"
    
    response = client.chat(
        message=test_request,
        system_prompt=STORAGE_AGENT_SYSTEM_PROMPT
    )
    
    print(f"Test Request: {test_request}")
    print(f"Success: {response.success}")
    
    if response.success:
        print(f"Storage Agent Response: {response.content}")
    else:
        print(f"Error: {response.error_message}")
        
    return response.success


def test_requirements_extraction():
    """Test requirements extraction prompt."""
    print("\n" + "=" * 50)
    print("Testing Requirements Extraction")
    print("=" * 50)
    
    client = create_ollama_client()
    
    test_inputs = [
        "I need storage for my website images",
        "Create backup storage for my database",
        "I need cheap storage for old log files",
    ]
    
    for test_input in test_inputs:
        print(f"\nTesting: '{test_input}'")
        
        prompt = format_extract_requirements_prompt(test_input)
        response = client.generate(prompt)
        
        if response.success:
            print(f"Extracted: {response.content[:150]}...")
        else:
            print(f"Error: {response.error_message}")


def main():
    """Run all tests for Day 1 setup."""
    print("Testing Day 1: Local LLM Setup")
    print("This will test Ollama integration and storage prompts\n")
    
    # Test 1: Ollama availability
    if not test_ollama_availability():
        print("\nX Ollama setup incomplete. Please install Ollama and try again.")
        return
        
    # Test 2: Basic chat
    if not test_basic_chat():
        print("\nX Basic chat failed.")
        return
        
    # Test 3: Storage prompts
    if not test_storage_prompts():
        print("\nX Storage prompts failed.")
        return
        
    # Test 4: Requirements extraction
    test_requirements_extraction()
    
    print("\n" + "=" * 50)
    print("+ Day 1 Setup Complete!")
    print("=" * 50)
    print("+ Ollama is running and accessible")
    print("+ Basic chat functionality works")
    print("+ Storage-specific prompts work")
    print("+ Requirements extraction tested")
    print("\nReady for Day 2: JSON Memory System")


if __name__ == "__main__":
    main()