#!/usr/bin/env python
"""Lightweight test runner for AI assistant generators without pytest.

Runs two checks with a dummy AI client:
- AbstractModeGenerator: parses JSON and skips temperature for GPT‑5
- MatrixDimensionGenerator: parses YAML and skips temperature for GPT‑5
"""

import json
import os
import sys
from typing import Any, Dict

# Ensure repository root is on sys.path for package import
THIS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
# Redirect HOME so logging writes under repo (sandbox-safe)
os.environ["HOME"] = REPO_ROOT
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import litrx.ai_config_generator as gen_mod


class DummyAIClient:
    def __init__(self, config: Dict[str, Any]):
        self.model = config.get("MODEL_NAME", "gpt-4o")
        name = str(self.model).lower()
        self.supports_temperature = not (
            name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3") or name.startswith("o-")
        )
        self.last_kwargs: Dict[str, Any] = {}
        self._response_factory = None

    def request(self, **kwargs: Any) -> Dict[str, Any]:
        self.last_kwargs = kwargs
        assert self._response_factory, "No response factory attached"
        content = self._response_factory()
        return {"choices": [{"message": {"content": content}}]}


def run():
    # Patch AIClient in module
    gen_mod.AIClient = DummyAIClient  # type: ignore

    # 1) Abstract mode with GPT-5 (no temperature expected)
    gen_a = gen_mod.AbstractModeGenerator({"MODEL_NAME": "gpt-5"})

    def resp_json():
        payload = {
            "mode_key": "weekly_screening",
            "description": "中文描述",
            "yes_no_questions": [
                {"key": "rel", "question": "是否相关?", "column_name": "是否相关"}
            ],
            "open_questions": [
                {"key": "sum", "question": "请总结", "column_name": "摘要总结"}
            ],
        }
        return "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"

    gen_a.client._response_factory = resp_json  # type: ignore[attr-defined]
    data = gen_a.generate_mode("测试需求")
    assert data["mode_key"] == "weekly_screening"
    assert "temperature" not in gen_a.client.last_kwargs
    assert gen_a.client.last_kwargs.get("response_format") == {"type": "json_object"}
    print("OK: AbstractModeGenerator (GPT-5, no temperature)")

    # 2) Matrix dimensions with GPT-5 (no temperature expected)
    gen_m = gen_mod.MatrixDimensionGenerator({"MODEL_NAME": "gpt-5-mini"})

    def resp_yaml():
        return (
            "dimensions:\n"
            "  - type: yes_no\n"
            "    key: relevant\n"
            "    question: 是否相关?\n"
            "    column_name: 是否相关\n"
            "  - type: text\n"
            "    key: summary\n"
            "    question: 请总结\n"
            "    column_name: 摘要总结\n"
        )

    gen_m.client._response_factory = resp_yaml  # type: ignore[attr-defined]
    dims = gen_m.generate_dimensions("测试维度")
    assert isinstance(dims, list) and len(dims) == 2
    assert "temperature" not in gen_m.client.last_kwargs
    assert "response_format" not in gen_m.client.last_kwargs
    print("OK: MatrixDimensionGenerator (GPT-5, no temperature)")


if __name__ == "__main__":
    run()
