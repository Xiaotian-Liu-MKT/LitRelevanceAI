"""AI-powered configuration generators for modes and matrix dimensions.

Skeleton implementation that integrates with AIClient and supports
JSON/YAML parsing from model outputs. Uses resource_path() to load
prompt templates and falls back to embedded defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import yaml

from .ai_client import AIClient
from .resources import resource_path


def _clean_code_fences(text: str, kind: str) -> str:
    fence = f"```{kind}"
    if fence in text:
        try:
            return text.split(fence, 1)[1].split("```", 1)[0].strip()
        except Exception:
            return text
    if "```" in text:
        try:
            return text.split("```", 1)[1].split("```", 1)[0].strip()
        except Exception:
            return text
    return text


@dataclass
class _PromptFiles:
    abstract_mode: str = "litrx/prompts/abstract_mode_generation.txt"
    matrix_dims: str = "litrx/prompts/matrix_dimension_generation.txt"


class AbstractModeGenerator:
    """Generate abstract-screening mode configs via LLM."""

    def __init__(self, config: Dict[str, Any]):
        self.client = AIClient(config)
        self.template = self._load_template(_PromptFiles.abstract_mode, self._default_mode_template())

    def generate_mode(self, description: str, language: str = "zh") -> Dict[str, Any]:
        prompt = self.template.format(user_description=description, language=language)
        req: Dict[str, Any] = {"messages": [{"role": "user", "content": prompt}]}
        if getattr(self.client, "supports_temperature", True):
            req["temperature"] = 0.3
        resp = self.client.request(**req)
        content = resp["choices"][0]["message"]["content"]
        payload = _clean_code_fences(content, "json")
        data = json.loads(payload)
        self._validate_mode(data)
        return data

    def _validate_mode(self, data: Dict[str, Any]) -> None:
        for k in ("mode_key", "description", "yes_no_questions", "open_questions"):
            if k not in data:
                raise ValueError(f"Missing field: {k}")
        for group_name in ("yes_no_questions", "open_questions"):
            group = data.get(group_name, [])
            if not isinstance(group, list):
                raise ValueError(f"{group_name} must be a list")
            for idx, q in enumerate(group):
                for f in ("key", "question", "column_name"):
                    if f not in q:
                        raise ValueError(f"Question {group_name}[{idx}] missing field {f}")

    def _load_template(self, path_str: str, default_value: str) -> str:
        p = resource_path(*path_str.split("/"))
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return default_value

    def _default_mode_template(self) -> str:
        return (
            "You are an expert in academic literature screening.\n\n"
            "User's requirements:\n{user_description}\n\n"
            "Output ONLY JSON with structure:\n"
            "{{\n  \"mode_key\": \"english_snake_case\",\n  \"description\": \"in {language}\",\n"
            "  \"yes_no_questions\": [{{\"key\": \"...\", \"question\": \"...\", \"column_name\": \"...\"}}],\n"
            "  \"open_questions\": [{{\"key\": \"...\", \"question\": \"...\", \"column_name\": \"...\"}}]\n}}"
        )


class MatrixDimensionGenerator:
    """Generate matrix dimension configs via LLM."""

    def __init__(self, config: Dict[str, Any]):
        self.client = AIClient(config)
        self.template = self._load_template(_PromptFiles.matrix_dims, self._default_dims_template())

    def generate_dimensions(self, description: str, language: str = "zh") -> List[Dict[str, Any]]:
        prompt = self.template.format(user_description=description, language=language)
        req: Dict[str, Any] = {"messages": [{"role": "user", "content": prompt}]}
        if getattr(self.client, "supports_temperature", True):
            req["temperature"] = 0.3
        resp = self.client.request(**req)
        content = resp["choices"][0]["message"]["content"]
        payload = _clean_code_fences(content, "yaml")
        data = yaml.safe_load(payload)
        dims = data.get("dimensions", data) if isinstance(data, dict) else data
        if not isinstance(dims, list):
            raise ValueError("Expected a list of dimensions")
        for d in dims:
            self._validate_dimension(d)
        return dims

    def _validate_dimension(self, d: Dict[str, Any]) -> None:
        for k in ("type", "key", "question", "column_name"):
            if k not in d:
                raise ValueError(f"Missing field '{k}' in dimension")
        if d["type"] in ("single_choice", "multiple_choice"):
            opts = d.get("options", [])
            if not isinstance(opts, list) or len(opts) < 2:
                raise ValueError("Choice types require at least 2 options")
        if d["type"] == "rating":
            scale = d.get("scale")
            if not isinstance(scale, int) or not (2 <= scale <= 10):
                raise ValueError("rating.scale must be an integer in [2,10]")
        if d["type"] == "list" and "separator" not in d:
            raise ValueError("list type requires 'separator'")

    def _load_template(self, path_str: str, default_value: str) -> str:
        p = resource_path(*path_str.split("/"))
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return default_value

    def _default_dims_template(self) -> str:
        return (
            "You are an expert in literature matrix design.\n\n"
            "User's requirements:\n{user_description}\n\n"
            "Output ONLY YAML with structure:\n"
            "dimensions:\n  - type: <text|yes_no|single_choice|multiple_choice|number|rating|list>\n"
            "    key: english_snake_case\n    question: 'in {language}'\n    column_name: 'in {language}'\n"
            "    # type-specific fields as needed\n"
        )

