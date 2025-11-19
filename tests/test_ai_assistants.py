"""Tests for AI assistant generators (abstract mode and matrix dimensions).

These tests mock the underlying AI client to avoid network calls and
validate that:
- Parsing works for JSON (abstract mode) and YAML (matrix dimensions)
- Temperature is not sent when using GPT-5 style models
"""

from typing import Any, Dict, List

import json
import types

import pytest

import litrx.ai_config_generator as gen_mod


class DummyAIClient:
    """Minimal stand-in for AIClient recording kwargs and returning a stub."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.model = config.get("MODEL_NAME", "gpt-4o")
        self.supports_temperature = not (
            str(self.model).lower().startswith("gpt-5")
            or str(self.model).lower().startswith("o1")
            or str(self.model).lower().startswith("o3")
            or str(self.model).lower().startswith("o-")
        )
        self.last_kwargs: Dict[str, Any] = {}

    def request(self, **kwargs: Any) -> Dict[str, Any]:
        self.last_kwargs = kwargs
        # Response content is filled by the test via monkeypatched factory
        factory = getattr(self, "_response_factory", None)
        assert factory is not None, "_response_factory not set for DummyAIClient"
        content = factory()
        return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def patch_dummy_client(monkeypatch):
    """Patch AIClient in the generator module to our dummy implementation."""
    monkeypatch.setattr(gen_mod, "AIClient", DummyAIClient)
    return DummyAIClient


def test_abstract_mode_generator_parses_json_and_handles_gpt5_temperature(patch_dummy_client):
    # Arrange: config for GPT-5 model (no temperature expected)
    cfg = {"MODEL_NAME": "gpt-5.1"}
    gen = gen_mod.AbstractModeGenerator(cfg)
    assert isinstance(gen.client, DummyAIClient)

    # Provide a JSON response (wrapped in code fences like real models)
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

    # Attach factory to dummy instance
    gen.client._response_factory = resp_json  # type: ignore[attr-defined]

    # Act
    data = gen.generate_mode("测试需求", language="zh")

    # Assert: parsed content and no temperature sent for gpt-5
    assert data["mode_key"] == "weekly_screening"
    assert isinstance(data["yes_no_questions"], list)
    assert isinstance(data["open_questions"], list)

    # Temperature should not be included in kwargs for GPT-5
    assert "temperature" not in gen.client.last_kwargs
    # And response_format should request JSON object
    assert gen.client.last_kwargs.get("response_format") == {"type": "json_object"}


def test_matrix_dimension_generator_parses_yaml_and_handles_gpt5_temperature(patch_dummy_client):
    # Arrange: config for GPT-5 model (no temperature expected)
    cfg = {"MODEL_NAME": "gpt-5-mini"}
    gen = gen_mod.MatrixDimensionGenerator(cfg)
    assert isinstance(gen.client, DummyAIClient)

    # Provide a YAML response (wrapped in code fences)
    def resp_yaml():
        return (
            "```yaml\n"
            "dimensions:\n"
            "  - type: yes_no\n"
            "    key: relevant\n"
            "    question: 是否相关?\n"
            "    column_name: 是否相关\n"
            "  - type: text\n"
            "    key: summary\n"
            "    question: 请总结\n"
            "    column_name: 摘要总结\n"
            "```\n"
        )

    gen.client._response_factory = resp_yaml  # type: ignore[attr-defined]

    # Act
    dims = gen.generate_dimensions("测试维度", language="zh")

    # Assert: parsed content and no temperature sent
    assert isinstance(dims, list) and len(dims) == 2
    assert dims[0]["type"] == "yes_no"
    assert "temperature" not in gen.client.last_kwargs
    # Matrix generator should not force JSON response_format (expects YAML/text)
    assert "response_format" not in gen.client.last_kwargs


def test_generators_send_temperature_for_non_gpt5_models(monkeypatch):
    # Patch in dummy client but use a non-GPT5 model name
    monkeypatch.setattr(gen_mod, "AIClient", DummyAIClient)
    cfg = {"MODEL_NAME": "gpt-4o"}

    # Abstract mode
    gen_a = gen_mod.AbstractModeGenerator(cfg)
    gen_a.client._response_factory = lambda: "{\n\"mode_key\": \"k\", \n\"description\": \"d\", \n\"yes_no_questions\": [], \n\"open_questions\": []\n}"
    _ = gen_a.generate_mode("x")
    assert gen_a.client.last_kwargs.get("temperature") is not None

    # Matrix dims
    gen_m = gen_mod.MatrixDimensionGenerator(cfg)
    gen_m.client._response_factory = lambda: "dimensions:\n  - type: text\n    key: k\n    question: q\n    column_name: c\n"
    _ = gen_m.generate_dimensions("x")
    assert gen_m.client.last_kwargs.get("temperature") is not None
