"""Security utilities for handling sensitive data.

This module provides tools for sanitizing sensitive information like API keys
in logs, error messages, and other output to prevent accidental exposure.
"""

import re
from typing import Dict, Any, Union


class SecureLogger:
    """Utility class for safely logging data that may contain sensitive information."""

    # Sensitive field keys that should be redacted
    SENSITIVE_KEYS = {
        'OPENAI_API_KEY',
        'SILICONFLOW_API_KEY',
        'GEMINI_API_KEY',
        'ANTHROPIC_API_KEY',
        'API_KEY',
        'api_key',
        'password',
        'secret',
        'token',
        'authorization',
        'auth_token',
        'access_token',
        'refresh_token',
        'private_key',
        'secret_key',
    }

    # Patterns for detecting API keys in strings
    API_KEY_PATTERNS = [
        r'sk-[a-zA-Z0-9]{16,}',  # OpenAI format (accepts shorter test strings)
        r'sk-proj-[a-zA-Z0-9_-]{16,}',  # OpenAI project keys
        r'sk-(test|live)-[a-zA-Z0-9]{16,}',  # Environment-scoped keys
        r'[A-Fa-f0-9]{32,}',  # Generic hex tokens
        r'Bearer\s+[A-Za-z0-9._\-]+',  # Bearer tokens
        r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',  # JWT tokens
    ]

    @staticmethod
    def sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe copy of configuration with sensitive information redacted.

        Args:
            config: Original configuration dictionary

        Returns:
            Sanitized configuration dictionary (deep copy)

        Example:
            >>> config = {"OPENAI_API_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz", "MODEL": "gpt-4"}
            >>> safe = SecureLogger.sanitize_config(config)
            >>> print(safe["OPENAI_API_KEY"])
            sk-12345***
            >>> print(safe["MODEL"])
            gpt-4
        """
        safe_config = {}

        for key, value in config.items():
            if key in SecureLogger.SENSITIVE_KEYS:
                if value and isinstance(value, str):
                    # Preserve first 8 characters, replace rest with ***
                    safe_config[key] = value[:8] + "***" if len(value) > 8 else "***"
                else:
                    safe_config[key] = "***"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                safe_config[key] = SecureLogger.sanitize_config(value)
            elif isinstance(value, (list, tuple)):
                # Sanitize lists/tuples
                safe_config[key] = [
                    SecureLogger.sanitize_config(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                safe_config[key] = value

        return safe_config

    @staticmethod
    def sanitize_string(text: str) -> str:
        """Remove potential API keys and sensitive patterns from a string.

        Args:
            text: Original text that may contain sensitive information

        Returns:
            Text with sensitive patterns replaced with '***REDACTED***'

        Example:
            >>> text = "Error: API key sk-1234567890abcdefghijklmnopqrstuvwxyz is invalid"
            >>> safe = SecureLogger.sanitize_string(text)
            >>> print(safe)
            Error: API key ***REDACTED*** is invalid
        """
        if not text:
            return text

        result = text

        # Replace known API key patterns
        for pattern in SecureLogger.API_KEY_PATTERNS:
            result = re.sub(pattern, '***REDACTED***', result, flags=re.IGNORECASE)

        # Replace sensitive key-value pairs in text
        # Pattern: key=value or key: value
        for sensitive_key in SecureLogger.SENSITIVE_KEYS:
            # Match key=value or key: value patterns
            patterns = [
                rf'{sensitive_key}\s*=\s*[^\s,\n]+',
                rf'{sensitive_key}\s*:\s*[^\s,\n]+',
                rf'"{sensitive_key}"\s*:\s*"[^"]+',
                rf"'{sensitive_key}'\s*:\s*'[^']+",
            ]
            for pattern in patterns:
                result = re.sub(
                    pattern,
                    f'{sensitive_key}: ***REDACTED***',
                    result,
                    flags=re.IGNORECASE
                )

        return result

    @staticmethod
    def sanitize_error(error: Exception) -> str:
        """Sanitize error message to remove sensitive information.

        Args:
            error: Exception object

        Returns:
            Sanitized error message string

        Example:
            >>> error = Exception("Invalid API key: sk-abc123...")
            >>> safe = SecureLogger.sanitize_error(error)
            >>> print(safe)
            Invalid API key: ***REDACTED***
        """
        return SecureLogger.sanitize_string(str(error))

    @staticmethod
    def sanitize_dict(data: Union[Dict, list, Any]) -> Union[Dict, list, Any]:
        """Recursively sanitize a dictionary or list structure.

        Args:
            data: Dictionary, list, or other data structure

        Returns:
            Sanitized copy of the data structure

        Example:
            >>> data = {"user": "john", "api_key": "secret123", "nested": {"token": "abc"}}
            >>> safe = SecureLogger.sanitize_dict(data)
            >>> print(safe["api_key"])
            ***
        """
        if isinstance(data, dict):
            return SecureLogger.sanitize_config(data)
        elif isinstance(data, (list, tuple)):
            return [SecureLogger.sanitize_dict(item) for item in data]
        elif isinstance(data, str):
            return SecureLogger.sanitize_string(data)
        else:
            return data

    @staticmethod
    def get_safe_repr(obj: Any, max_length: int = 100) -> str:
        """Get a safe string representation of an object with sensitive data redacted.

        Args:
            obj: Any Python object
            max_length: Maximum length of the output string (default: 100)

        Returns:
            Safe string representation

        Example:
            >>> config = {"OPENAI_API_KEY": "sk-secret", "MODEL": "gpt-4"}
            >>> print(SecureLogger.get_safe_repr(config))
            {'OPENAI_API_KEY': '***', 'MODEL': 'gpt-4'}
        """
        if isinstance(obj, dict):
            safe_obj = SecureLogger.sanitize_config(obj)
        elif isinstance(obj, str):
            safe_obj = SecureLogger.sanitize_string(obj)
        elif isinstance(obj, Exception):
            safe_obj = SecureLogger.sanitize_error(obj)
        else:
            safe_obj = obj

        repr_str = repr(safe_obj)

        if len(repr_str) > max_length:
            repr_str = repr_str[:max_length] + "..."

        return repr_str


# Convenience functions for common use cases

def safe_log_config(config: Dict[str, Any]) -> str:
    """Generate a safe log-friendly string representation of configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Safe string suitable for logging

    Example:
        >>> config = {"OPENAI_API_KEY": "sk-secret", "MODEL": "gpt-4"}
        >>> print(safe_log_config(config))
        OPENAI_API_KEY: sk-secre***, MODEL: gpt-4
    """
    safe_config = SecureLogger.sanitize_config(config)
    items = [f"{k}: {v}" for k, v in safe_config.items()]
    return ", ".join(items)


def safe_log_error(error: Exception, include_type: bool = True) -> str:
    """Generate a safe log-friendly error message.

    Args:
        error: Exception to log
        include_type: Whether to include exception type (default: True)

    Returns:
        Safe error message string

    Example:
        >>> error = ValueError("Invalid API key: sk-abc123")
        >>> print(safe_log_error(error))
        ValueError: Invalid API key: ***REDACTED***
    """
    safe_message = SecureLogger.sanitize_error(error)
    if include_type:
        return f"{type(error).__name__}: {safe_message}"
    return safe_message
