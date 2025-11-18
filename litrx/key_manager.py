"""Secure API key management using keyring.

This module provides secure storage and retrieval of API keys using the system's
keyring service instead of storing them in plain text.
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None

logger = logging.getLogger(__name__)

# Service name for keyring storage
SERVICE_NAME = "litrx"

# Key identifiers
KEY_OPENAI = "openai_api_key"
KEY_SILICONFLOW = "siliconflow_api_key"


class KeyManager:
    """Manages secure storage and retrieval of API keys."""

    def __init__(self):
        """Initialize the key manager."""
        self.keyring_available = KEYRING_AVAILABLE
        if not self.keyring_available:
            logger.warning(
                "keyring library not available. API keys will not be stored securely. "
                "Install keyring: pip install keyring"
            )

    def set_key(self, key_name: str, api_key: str) -> bool:
        """Store an API key securely.

        Args:
            key_name: The identifier for the key (e.g., "openai_api_key")
            api_key: The API key to store

        Returns:
            True if successful, False otherwise
        """
        if not api_key or not api_key.strip():
            # Don't store empty keys
            return True

        if not self.keyring_available:
            logger.warning(f"Cannot securely store {key_name}: keyring not available")
            return False

        try:
            keyring.set_password(SERVICE_NAME, key_name, api_key.strip())
            logger.info(f"Successfully stored {key_name} in system keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to store {key_name} in keyring: {e}")
            return False

    def get_key(self, key_name: str) -> Optional[str]:
        """Retrieve an API key from secure storage.

        Args:
            key_name: The identifier for the key (e.g., "openai_api_key")

        Returns:
            The API key if found, None otherwise
        """
        if not self.keyring_available:
            return None

        try:
            key = keyring.get_password(SERVICE_NAME, key_name)
            if key:
                logger.debug(f"Retrieved {key_name} from keyring")
            return key
        except Exception as e:
            logger.error(f"Failed to retrieve {key_name} from keyring: {e}")
            return None

    def delete_key(self, key_name: str) -> bool:
        """Delete an API key from secure storage.

        Args:
            key_name: The identifier for the key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.keyring_available:
            return False

        try:
            keyring.delete_password(SERVICE_NAME, key_name)
            logger.info(f"Deleted {key_name} from keyring")
            return True
        except Exception as e:
            logger.debug(f"Could not delete {key_name} from keyring: {e}")
            return False

    def migrate_from_plaintext(self, plaintext_keys: dict) -> dict:
        """Migrate API keys from plaintext config to secure keyring.

        Args:
            plaintext_keys: Dictionary with keys like "OPENAI_API_KEY", "SILICONFLOW_API_KEY"

        Returns:
            Dictionary with keys removed (empty strings) if migration successful
        """
        migrated_keys = plaintext_keys.copy()

        # Migrate OpenAI key
        if plaintext_keys.get("OPENAI_API_KEY"):
            if self.set_key(KEY_OPENAI, plaintext_keys["OPENAI_API_KEY"]):
                migrated_keys["OPENAI_API_KEY"] = ""  # Clear from plaintext

        # Migrate SiliconFlow key
        if plaintext_keys.get("SILICONFLOW_API_KEY"):
            if self.set_key(KEY_SILICONFLOW, plaintext_keys["SILICONFLOW_API_KEY"]):
                migrated_keys["SILICONFLOW_API_KEY"] = ""  # Clear from plaintext

        return migrated_keys


# Global instance
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get the global KeyManager instance.

    Returns:
        The global KeyManager instance
    """
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager
