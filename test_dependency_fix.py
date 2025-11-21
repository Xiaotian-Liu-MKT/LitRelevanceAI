#!/usr/bin/env python
"""Test script to verify the httpx/OpenAI SDK compatibility fix."""

import sys
import os

# Add the project to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that we can import the required modules."""
    print("Testing imports...")
    try:
        import openai
        import httpx
        print(f"✓ OpenAI version: {openai.__version__}")
        print(f"✓ httpx version: {httpx.__version__}")

        # Verify versions meet requirements
        openai_version = tuple(map(int, openai.__version__.split('.')[:2]))
        httpx_version = tuple(map(int, httpx.__version__.split('.')[:2]))

        if openai_version >= (1, 14):
            print(f"✓ OpenAI version {openai.__version__} meets requirement (>= 1.14.0)")
        else:
            print(f"✗ OpenAI version {openai.__version__} does not meet requirement (>= 1.14.0)")
            return False

        if httpx_version >= (0, 27):
            print(f"✓ httpx version {httpx.__version__} meets requirement (>= 0.27.0)")
        else:
            print(f"✗ httpx version {httpx.__version__} does not meet requirement (>= 0.27.0)")
            return False

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_ai_client_init():
    """Test that AIClient can be initialized without 'proxies' error."""
    print("\nTesting AIClient initialization...")
    try:
        from litrx.ai_client import AIClient
        from litrx.config import DEFAULT_CONFIG

        # Create a test config (will fail at API key check, but should not fail at 'proxies')
        test_config = DEFAULT_CONFIG.copy()
        test_config["OPENAI_API_KEY"] = "test-key"  # Dummy key to bypass key check

        print("Attempting to create AIClient...")
        try:
            client = AIClient(test_config)
            print("✓ AIClient initialized successfully (no 'proxies' error)")
            print(f"✓ Client service: {client.service}")
            print(f"✓ Client model: {client.model}")
            return True
        except RuntimeError as e:
            error_msg = str(e)
            if "proxies" in error_msg:
                print(f"✗ FAILED: Still getting 'proxies' error: {e}")
                return False
            else:
                # Other errors are OK (like API key validation)
                print(f"✓ No 'proxies' error (got expected error: {e})")
                return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_config_generator():
    """Test that AbstractModeGenerator can be initialized."""
    print("\nTesting AbstractModeGenerator initialization...")
    try:
        from litrx.ai_config_generator import AbstractModeGenerator
        from litrx.config import DEFAULT_CONFIG

        test_config = DEFAULT_CONFIG.copy()
        test_config["OPENAI_API_KEY"] = "test-key"

        print("Attempting to create AbstractModeGenerator...")
        try:
            generator = AbstractModeGenerator(test_config)
            print("✓ AbstractModeGenerator initialized successfully")
            return True
        except RuntimeError as e:
            error_msg = str(e)
            if "proxies" in error_msg:
                print(f"✗ FAILED: Still getting 'proxies' error: {e}")
                return False
            else:
                print(f"✓ No 'proxies' error (got expected error: {e})")
                return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing httpx/OpenAI SDK Compatibility Fix")
    print("=" * 60)

    results = []
    results.append(("Import Test", test_import()))
    results.append(("AIClient Init Test", test_ai_client_init()))
    results.append(("AbstractModeGenerator Test", test_ai_config_generator()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✓ All tests passed! The dependency issue is fixed.")
        print("\nNext steps:")
        print("1. Configure your API key in the GUI or .env file")
        print("2. Run the GUI: python run_gui.py")
        print("3. Try the AI assistant feature in Abstract Screening tab")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Try reinstalling: pip uninstall -y openai httpx && pip install -e .")
        print("2. Clear pip cache: pip cache purge")
        print("3. Create a fresh virtual environment")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
