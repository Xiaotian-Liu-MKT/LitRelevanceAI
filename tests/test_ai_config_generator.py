"""Unit tests for AI configuration generator."""

import json
import pytest
from unittest.mock import MagicMock, patch

import yaml

from litrx.ai_config_generator import AbstractModeGenerator, MatrixDimensionGenerator


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-4",
        "OPENAI_API_KEY": "test-key",
        "LANGUAGE": "zh"
    }


@pytest.fixture
def mock_ai_client(mocker):
    """Mock AIClient to avoid actual API calls."""
    mock = mocker.MagicMock()
    mocker.patch("litrx.ai_config_generator.AIClient", return_value=mock)
    return mock


class TestAbstractModeGenerator:
    """Tests for AbstractModeGenerator."""

    def test_generate_mode_basic(self, mock_config, mock_ai_client):
        """Test basic mode generation."""
        # Mock AI response
        mock_ai_client.request.return_value = '''
        {
          "mode_key": "test_mode",
          "description": "测试模式",
          "yes_no_questions": [
            {"key": "q1", "question": "问题1?", "column_name": "列1"}
          ],
          "open_questions": [
            {"key": "q2", "question": "问题2?", "column_name": "列2"}
          ]
        }
        '''

        generator = AbstractModeGenerator(mock_config)
        result = generator.generate_mode("测试描述")

        assert result["mode_key"] == "test_mode"
        assert result["description"] == "测试模式"
        assert len(result["yes_no_questions"]) == 1
        assert len(result["open_questions"]) == 1
        assert result["yes_no_questions"][0]["key"] == "q1"
        assert result["open_questions"][0]["key"] == "q2"

    def test_generate_mode_with_markdown_code_block(self, mock_config, mock_ai_client):
        """Test parsing JSON from markdown code block."""
        mock_ai_client.request.return_value = '''
        ```json
        {
          "mode_key": "markdown_test",
          "description": "Markdown test",
          "yes_no_questions": [],
          "open_questions": [{"key": "q1", "question": "Q?", "column_name": "C"}]
        }
        ```
        '''

        generator = AbstractModeGenerator(mock_config)
        result = generator.generate_mode("test")

        assert result["mode_key"] == "markdown_test"
        assert len(result["open_questions"]) == 1

    def test_validate_config_missing_field(self, mock_config):
        """Test validation with missing field."""
        generator = AbstractModeGenerator(mock_config)

        with pytest.raises(ValueError, match="Missing required field"):
            generator._validate_config({"mode_key": "test"})

    def test_validate_config_invalid_mode_key(self, mock_config):
        """Test validation with invalid mode_key format."""
        generator = AbstractModeGenerator(mock_config)

        invalid_config = {
            "mode_key": "invalid-mode!@#",
            "description": "test",
            "yes_no_questions": [],
            "open_questions": []
        }

        with pytest.raises(ValueError, match="Invalid mode_key format"):
            generator._validate_config(invalid_config)

    def test_validate_config_invalid_question(self, mock_config):
        """Test validation with invalid question format."""
        generator = AbstractModeGenerator(mock_config)

        invalid_config = {
            "mode_key": "test_mode",
            "description": "test",
            "yes_no_questions": [{"invalid": "format"}],
            "open_questions": []
        }

        with pytest.raises(ValueError):
            generator._validate_config(invalid_config)

    def test_parse_json_response_error(self, mock_config):
        """Test parsing invalid JSON."""
        generator = AbstractModeGenerator(mock_config)

        with pytest.raises(ValueError, match="Failed to parse"):
            generator._parse_json_response("not a json")


class TestMatrixDimensionGenerator:
    """Tests for MatrixDimensionGenerator."""

    def test_generate_dimensions_basic(self, mock_config, mock_ai_client):
        """Test basic dimension generation."""
        mock_ai_client.request.return_value = '''
        dimensions:
          - type: text
            key: findings
            question: "主要发现?"
            column_name: "发现"
          - type: rating
            key: quality
            question: "质量评分"
            column_name: "质量"
            scale: 5
        '''

        generator = MatrixDimensionGenerator(mock_config)
        result = generator.generate_dimensions("测试描述")

        assert len(result) == 2
        assert result[0]["type"] == "text"
        assert result[0]["key"] == "findings"
        assert result[1]["type"] == "rating"
        assert result[1]["scale"] == 5

    def test_generate_dimensions_with_code_block(self, mock_config, mock_ai_client):
        """Test parsing YAML from markdown code block."""
        mock_ai_client.request.return_value = '''
        ```yaml
        dimensions:
          - type: yes_no
            key: is_empirical
            question: "是否实证研究?"
            column_name: "实证研究"
        ```
        '''

        generator = MatrixDimensionGenerator(mock_config)
        result = generator.generate_dimensions("test")

        assert len(result) == 1
        assert result[0]["type"] == "yes_no"

    def test_validate_dimension_missing_field(self, mock_config):
        """Test validation with missing field."""
        generator = MatrixDimensionGenerator(mock_config)

        with pytest.raises(ValueError, match="Missing required field"):
            generator._validate_dimension({"type": "text"})

    def test_validate_dimension_invalid_type(self, mock_config):
        """Test validation with invalid type."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "invalid_type",
            "key": "test",
            "question": "Test?",
            "column_name": "Test"
        }

        with pytest.raises(ValueError, match="Invalid type"):
            generator._validate_dimension(dim)

    def test_validate_dimension_choice_without_options(self, mock_config):
        """Test validation of choice type without options."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "single_choice",
            "key": "test",
            "question": "Test?",
            "column_name": "Test"
        }

        with pytest.raises(ValueError, match="requires 'options'"):
            generator._validate_dimension(dim)

    def test_validate_dimension_choice_with_valid_options(self, mock_config):
        """Test validation of choice type with valid options."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "single_choice",
            "key": "test",
            "question": "Test?",
            "column_name": "Test",
            "options": ["Option 1", "Option 2"]
        }

        # Should not raise
        generator._validate_dimension(dim)

    def test_validate_dimension_rating_without_scale(self, mock_config):
        """Test validation of rating type without scale."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "rating",
            "key": "test",
            "question": "Test?",
            "column_name": "Test"
        }

        with pytest.raises(ValueError, match="requires 'scale'"):
            generator._validate_dimension(dim)

    def test_validate_dimension_rating_invalid_scale(self, mock_config):
        """Test validation of rating with invalid scale."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "rating",
            "key": "test",
            "question": "Test?",
            "column_name": "Test",
            "scale": 15  # Invalid: > 10
        }

        with pytest.raises(ValueError, match="Invalid scale value"):
            generator._validate_dimension(dim)

    def test_validate_dimension_list_without_separator(self, mock_config):
        """Test validation of list type without separator."""
        generator = MatrixDimensionGenerator(mock_config)

        dim = {
            "type": "list",
            "key": "test",
            "question": "Test?",
            "column_name": "Test"
        }

        with pytest.raises(ValueError, match="requires 'separator'"):
            generator._validate_dimension(dim)

    def test_parse_yaml_response_error(self, mock_config):
        """Test parsing invalid YAML."""
        generator = MatrixDimensionGenerator(mock_config)

        with pytest.raises(ValueError, match="Failed to parse"):
            generator._parse_yaml_response("invalid: yaml: {")


def test_generator_uses_template_file(tmp_path, mock_config, mocker):
    """Test that generator uses template file if it exists."""
    # Create a temporary template file
    template_dir = tmp_path / "prompts"
    template_dir.mkdir()
    template_file = template_dir / "abstract_mode_generation.txt"
    template_file.write_text("Custom template {user_description} {language}")

    # Patch Path to return our temp directory
    mock_path = mocker.patch("litrx.ai_config_generator.Path")
    mock_path.return_value.parent = tmp_path

    # Mock AIClient
    mocker.patch("litrx.ai_config_generator.AIClient")

    generator = AbstractModeGenerator(mock_config)

    # Generator should have loaded the custom template
    assert "Custom template" in generator.prompt_template


def test_generator_uses_default_template(mock_config, mocker):
    """Test that generator uses default template if file doesn't exist."""
    # Mock Path to return non-existent directory
    mock_path = mocker.patch("litrx.ai_config_generator.Path")
    mock_path.return_value.parent = mocker.MagicMock()
    mock_path.return_value.parent.__truediv__ = lambda self, x: mocker.MagicMock()
    mock_path.return_value.parent.__truediv__().exists.return_value = False

    # Mock AIClient
    mocker.patch("litrx.ai_config_generator.AIClient")

    generator = AbstractModeGenerator(mock_config)

    # Generator should have loaded the default template
    assert "You are an expert" in generator.prompt_template
