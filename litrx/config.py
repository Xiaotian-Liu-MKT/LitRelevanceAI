"""Configuration utilities for LitRelevanceAI.

This module centralizes loading environment variables from a `.env` file
and reading configuration from JSON or YAML files. It exposes a
``DEFAULT_CONFIG`` dictionary with common AI settings which individual
scripts can extend.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback if pyyaml missing
    yaml = None

try:
    from .key_manager import get_key_manager, KEY_OPENAI, KEY_SILICONFLOW
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Base configuration shared across scripts.
DEFAULT_CONFIG: Dict[str, Any] = {
    "AI_SERVICE": "openai",  # or "gemini" or "siliconflow"
    "MODEL_NAME": "gpt-4o",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "SILICONFLOW_API_KEY": "",
    "API_BASE": "",
    # GPT-5 specific parameters
    "VERBOSITY": "medium",  # "low", "medium", or "high"
    "REASONING_EFFORT": "medium",  # "low", "medium", or "high"
}

def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from a .env file if present."""

    path = Path(env_path)
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

def load_config(path: Optional[str], default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load configuration from a JSON or YAML file and merge with defaults.

    This function now prioritizes API keys in the following order:
    1. Environment variables (highest priority)
    2. Secure keyring storage
    3. Config file values (lowest priority, for backward compatibility)
    """

    config: Dict[str, Any] = (default or DEFAULT_CONFIG).copy()
    if not path:
        return config

    file_path = Path(path)
    if not file_path.is_file():
        return config

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix.lower() in {".yaml", ".yml"}:
                if yaml is None:
                    raise RuntimeError("pyyaml is required to read YAML files")
                user_cfg = yaml.safe_load(f) or {}
            else:
                user_cfg = json.load(f)
        if isinstance(user_cfg, dict):
            config.update(user_cfg)
    except Exception as e:
        raise RuntimeError(f"Failed to load config file {path}: {e}")

    # Load API keys from secure keyring (if available)
    if KEYRING_AVAILABLE:
        key_manager = get_key_manager()

        # Load OpenAI key from keyring if not in config
        openai_key = key_manager.get_key(KEY_OPENAI)
        if openai_key and not config.get("OPENAI_API_KEY"):
            config["OPENAI_API_KEY"] = openai_key

        # Load SiliconFlow key from keyring if not in config
        siliconflow_key = key_manager.get_key(KEY_SILICONFLOW)
        if siliconflow_key and not config.get("SILICONFLOW_API_KEY"):
            config["SILICONFLOW_API_KEY"] = siliconflow_key

    return config
