#!/usr/bin/env python3
"""
Quick Ollama test to diagnose timeout issues
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.llm.ollama_client import create_ollama_client

def simple_test():
    """Test with a simple message"""
    print("Testing simple message...")
    client = create_ollama_client(timeout=30)
    
    start_time = time.time()
    response = client.chat("Hello")
    end_time = time.time()
    
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print(f"Success: {response.success}")
    if response.success:
        print(f"Response: {response.content[:100]}...")
    else:
        print(f"Error: {response.error_message}")

def storage_test():
    """Test with storage-specific prompt"""
    print("\nTesting storage prompt...")
    client = create_ollama_client(timeout=60)  # Should be much faster with llama3.2:3b
    
    start_time = time.time()
    response = client.chat("I need storage for my blog images")
    end_time = time.time()
    
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print(f"Success: {response.success}")
    if response.success:
        print(f"Response: {response.content[:200]}...")
    else:
        print(f"Error: {response.error_message}")

if __name__ == "__main__":
    simple_test()
    storage_test()