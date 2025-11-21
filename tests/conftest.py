"""Pytest configuration for LitRelevanceAI tests."""

import os
import sys
import pytest
from unittest.mock import patch


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


@pytest.fixture
def mocker():
    """Lightweight substitute for pytest-mock's MockerFixture.

    Provides a ``patch`` helper that auto-starts the patch and ensures it is
    cleaned up after the test completes. This keeps tests using
    ``mocker.patch`` working without requiring the external ``pytest-mock``
    plugin.
    """

    active_patches = []

    class _Mocker:
        def patch(self, target, *args, **kwargs):
            p = patch(target, *args, **kwargs)
            active_patches.append(p)
            return p.start()

    yield _Mocker()

    for p in reversed(active_patches):
        p.stop()


@pytest.fixture
def preserve_excepthook():
    """Preserve and restore ``sys.excepthook`` around a test."""

    original_hook = sys.excepthook
    yield
    sys.excepthook = original_hook
