#!/usr/bin/env python3
"""
Test runner with clean output for Azure Infrastructure Agent.
"""

import subprocess
import sys
from pathlib import Path

def run_clean_tests():
    """Run tests with clean, minimal output."""
    
    # Test categories that work without Azure credentials
    working_test_dirs = [
        "tests/agent/",  # Agent functionality (187 tests)
        "tests/src/cli/",  # CLI tests  
        "tests/test_main.py",  # Main module tests
    ]
    
    print("Running Azure Infrastructure Agent Tests")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for test_dir in working_test_dirs:
        print(f"\nTesting: {test_dir}")
        print("-" * 40)
        
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_dir, 
            "-v", "--tb=no", "-q"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            summary_line = [l for l in lines if 'passed' in l][-1] if lines else ""
            print(f"PASS: {summary_line}")
            
            # Extract passed count
            if 'passed' in summary_line:
                try:
                    # Look for pattern like "187 passed"
                    words = summary_line.split()
                    for i, word in enumerate(words):
                        if word == 'passed' and i > 0:
                            passed = int(words[i-1])
                            total_passed += passed
                            break
                except (ValueError, IndexError):
                    pass
        else:
            print(f"FAIL: Some failures in {test_dir}")
            print(result.stdout)
            total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {total_passed} tests passed")
    if total_failed > 0:
        print(f"WARNING: {total_failed} test directories had issues")
    else:
        print("SUCCESS: All functional tests passing!")
    
    print("\nTo run full suite (with Azure failures):")
    print("   python -m pytest tests/ -v --tb=line -q")
    
if __name__ == "__main__":
    run_clean_tests()