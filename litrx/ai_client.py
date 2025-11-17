"""Simple AI client wrapper for OpenAI and Gemini via LiteLLM."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from litellm import completion

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

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
    """Initialise API credentials and send requests through LiteLLM or OpenAI SDK."""

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
        self.service = service
        self.config = config

        # Initialize OpenAI client for GPT-5 and o1 models
        self.openai_client = None
        if service == "openai" and self._is_new_api_model(model):
            if OpenAI is None:
                raise RuntimeError("需要安装 openai 包以使用 GPT-5 或 o1 模型: pip install openai")
            self.openai_client = OpenAI(
                api_key=api_key,
                base_url=api_base if api_base else None
            )

    def _is_new_api_model(self, model: str) -> bool:
        """Check if model requires the new responses API (GPT-5 or o1 series)."""
        model_lower = model.lower()
        return "gpt-5" in model_lower or model_lower.startswith("o1")

    def _is_o1_model(self, model: str) -> bool:
        """Check if model is from o1 series (has special parameter restrictions)."""
        return model.lower().startswith("o1")

    def _convert_messages_to_input(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert old-style messages to GPT-5 input format."""
        input_list = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Convert system role to developer for GPT-5
            if role == "system":
                role = "developer"

            # Convert content format
            if isinstance(content, str):
                converted_msg = {
                    "role": role,
                    "content": [{"type": "input_text", "text": content}]
                }
            elif isinstance(content, list):
                # Already in new format or needs conversion
                converted_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            converted_content.append({"type": "input_text", "text": item.get("text", "")})
                        else:
                            converted_content.append(item)
                    else:
                        converted_content.append({"type": "input_text", "text": str(item)})
                converted_msg = {
                    "role": role,
                    "content": converted_content
                }
            else:
                converted_msg = {
                    "role": role,
                    "content": [{"type": "input_text", "text": str(content)}]
                }

            input_list.append(converted_msg)

        return input_list

    def _extract_response_content(self, response: Any) -> str:
        """Extract text content from GPT-5 response object."""
        try:
            # Try to get output_text first (simplest)
            if hasattr(response, 'output_text'):
                return response.output_text

            # Try output[1].content[0].text pattern
            if hasattr(response, 'output') and len(response.output) > 1:
                output_item = response.output[1]
                if hasattr(output_item, 'content') and len(output_item.content) > 0:
                    content_item = output_item.content[0]
                    if hasattr(content_item, 'text'):
                        return content_item.text

            # Fallback: convert to dict and extract
            response_dict = response.model_dump() if hasattr(response, 'model_dump') else dict(response)
            if 'output' in response_dict and len(response_dict['output']) > 1:
                return response_dict['output'][1]['content'][0]['text']

            return str(response)
        except Exception:
            # Final fallback
            return str(response)

    def request(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """Send a chat completion request and return the raw response.

        Automatically uses GPT-5 responses API for gpt-5 and o1 models,
        and traditional chat completions API for other models.
        """
        try:
            # Use new responses API for GPT-5 and o1 models
            if self.openai_client is not None:
                return self._request_gpt5(messages, **kwargs)

            # Use traditional LiteLLM completion for other models
            return completion(model=self.model, messages=messages, **kwargs)
        except Exception as e:  # pragma: no cover - passthrough to caller
            raise RuntimeError(f"AI 请求失败: {e}") from e

    def _request_gpt5(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """Make request using GPT-5's new responses API."""
        # Convert messages to input format
        input_data = self._convert_messages_to_input(messages)

        # Extract GPT-5 specific parameters
        verbosity = kwargs.pop("verbosity", self.config.get("VERBOSITY", "medium"))
        reasoning_effort = kwargs.pop("reasoning_effort", self.config.get("REASONING_EFFORT", "medium"))
        reasoning_summary = kwargs.pop("reasoning_summary", "auto")
        store = kwargs.pop("store", True)
        tools = kwargs.pop("tools", [])

        # Handle response_format
        response_format = kwargs.pop("response_format", {"type": "text"})

        # Build text parameter
        text_param = {
            "format": response_format,
            "verbosity": verbosity
        }

        # Build reasoning parameter (not supported for o1 models)
        reasoning_param = None
        if not self._is_o1_model(self.model):
            reasoning_param = {
                "effort": reasoning_effort,
                "summary": reasoning_summary
            }

        # Remove old API parameters that are not supported in GPT-5
        kwargs.pop("temperature", None)
        kwargs.pop("top_p", None)
        kwargs.pop("frequency_penalty", None)
        kwargs.pop("presence_penalty", None)
        kwargs.pop("max_tokens", None)

        # Handle o1 specific parameters
        if self._is_o1_model(self.model):
            max_completion_tokens = kwargs.pop("max_completion_tokens", None)

        # Make the API call
        call_params = {
            "model": self.model,
            "input": input_data,
            "text": text_param,
            "tools": tools,
            "store": store,
        }

        # Add reasoning only for non-o1 models
        if reasoning_param:
            call_params["reasoning"] = reasoning_param

        # Add any remaining kwargs
        call_params.update(kwargs)

        response = self.openai_client.responses.create(**call_params)

        # Convert response to dict format compatible with old API
        content = self._extract_response_content(response)

        # Return in format compatible with existing code
        return {
            "choices": [{
                "message": {
                    "content": content,
                    "role": "assistant"
                },
                "index": 0,
                "finish_reason": "stop"
            }],
            "model": self.model,
            "_raw_response": response  # Store raw response for advanced use cases
        }
