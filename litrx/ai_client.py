"""Simple AI client wrapper for OpenAI and SiliconFlow APIs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

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
    """Initialize API credentials and send requests through OpenAI SDK."""

    def __init__(self, config: Dict[str, Any]) -> None:
        service = config.get("AI_SERVICE", "openai")
        model = config.get("MODEL_NAME", "gpt-4o")

        if service == "openai":
            api_key = config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OpenAI API密钥未配置。")
            api_base = config.get("API_BASE") or os.getenv("API_BASE") or None

        elif service == "siliconflow":
            api_key = config.get("SILICONFLOW_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
            if not api_key:
                raise RuntimeError("SiliconFlow API密钥未配置。")
            # SiliconFlow uses OpenAI-compatible API
            api_base = "https://api.siliconflow.cn/v1"

        else:
            raise RuntimeError(
                f"无效的AI服务 '{service}'。必须是 'openai' 或 'siliconflow'。"
            )

        self.model = model
        self.service = service
        self.config = config

        # Initialize OpenAI client (works for both OpenAI and SiliconFlow)
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base if api_base else None
        )

    def request(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """Send a chat completion request and return the response.

        Parameters
        ----------
        messages:
            List of message dictionaries with 'role' and 'content' keys.
        **kwargs:
            Additional parameters to pass to the API (temperature, max_tokens, etc.)

        Returns
        -------
        dict:
            Response dictionary in OpenAI format with 'choices' key.
        """
        try:
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )

            # Convert response to dict format
            return response.model_dump()

        except Exception as e:
            raise RuntimeError(f"AI 请求失败: {e}") from e
