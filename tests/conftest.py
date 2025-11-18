"""Pytest configuration for LitRelevanceAI tests."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Automatically set LITRX_ENV=test for all pytest runs.

    This allows tests to run without requiring real API keys.
    """
    original_env = os.getenv('LITRX_ENV')

    # Set test environment
    os.environ['LITRX_ENV'] = 'test'

    yield

    # Restore original environment (cleanup)
    if original_env is not None:
        os.environ['LITRX_ENV'] = original_env
    else:
        os.environ.pop('LITRX_ENV', None)


@pytest.fixture
def mock_config():
    """
    Provide a mock configuration for testing.

    Returns a config dict with dummy API keys that passes validation
    in test environment.
    """
    return {
        'AI_SERVICE': 'openai',
        'MODEL_NAME': 'gpt-4o-mini',
        'OPENAI_API_KEY': None,  # OK in test environment
        'SILICONFLOW_API_KEY': None,
        'GEMINI_API_KEY': None,
        'TEMPERATURE': 0.3,
        'ENABLE_VERIFICATION': False,
    }
