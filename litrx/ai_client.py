"""Simple AI client wrapper for OpenAI and Gemini via LiteLLM."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from litellm import completion

from .config import DEFAULT_CONFIG as BASE_CONFIG, load_config as base_load_config


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load AI client configuration.

    Parameters
    ----------
    path:
        Optional path to a YAML/JSON config file. When omitted, the default
        configuration under ``configs/config.yaml`` is used.
    """

    default_path = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    return base_load_config(str(path or default_path), BASE_CONFIG)


class AIClient:
    """Initialise API credentials and send requests through LiteLLM."""

    def __init__(self, config: Dict[str, Any]) -> None:
        service = config.get("AI_SERVICE", "openai")
        model = config.get("MODEL_NAME", "gpt-4o")
        api_base = config.get("API_BASE") or os.getenv("API_BASE")

        if service == "openai":
            api_key = config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OpenAI API密钥未配置。")
            os.environ["OPENAI_API_KEY"] = api_key
            if api_base:
                os.environ["OPENAI_BASE_URL"] = api_base
        elif service == "gemini":
            api_key = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("Gemini API密钥未配置。")
            os.environ["GEMINI_API_KEY"] = api_key
        elif service == "siliconflow":
            api_key = config.get("SILICONFLOW_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
            if not api_key:
                raise RuntimeError("SiliconFlow API密钥未配置。")
            os.environ["OPENAI_API_KEY"] = api_key
            # SiliconFlow uses OpenAI-compatible API, set the base URL
            os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"
        else:
            raise RuntimeError(
                f"无效的AI服务 '{service}'。必须是 'openai'、'gemini' 或 'siliconflow'。"
            )

        self.model = model

    def request(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """Send a chat completion request and return the raw response."""

        try:
            return completion(model=self.model, messages=messages, **kwargs)
        except Exception as e:  # pragma: no cover - passthrough to caller
            raise RuntimeError(f"AI 请求失败: {e}") from e
