"""AI-powered configuration generator for abstract screening modes and matrix dimensions.

This module provides tools to automatically generate configuration files from natural
language descriptions using AI language models.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .ai_client import AIClient


class AbstractModeGenerator:
    """AI-powered abstract screening mode generator.

    Generates screening mode configurations with yes/no questions and open questions
    based on user's natural language description of their screening needs.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize generator with AI client configuration.

        Args:
            config: Configuration dict containing AI_SERVICE, API keys, etc.
        """
        self.config = config
        self.client = AIClient(config["AI_SERVICE"], config)
        self.prompt_template = self._load_prompt_template()

    def generate_mode(
        self,
        description: str,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """Generate screening mode configuration from user description.

        Args:
            description: User's natural language description of screening needs
            language: Output language (zh/en)

        Returns:
            Mode configuration dict with structure:
            {
                "mode_key": str,
                "description": str,
                "yes_no_questions": list[dict],
                "open_questions": list[dict]
            }

        Raises:
            ValueError: If AI response is invalid or cannot be parsed
            Exception: If AI request fails
        """
        # 1. Build prompt
        prompt = self._build_prompt(description, language)

        # 2. Call AI
        response = self.client.request(
            prompt=prompt,
            temperature=0.3  # Lower temperature for stability
        )

        # 3. Parse response
        config = self._parse_json_response(response)

        # 4. Validate configuration
        self._validate_config(config)

        return config

    def _build_prompt(self, description: str, language: str) -> str:
        """Build AI prompt from template and user description.

        Args:
            description: User's description
            language: Target language (zh/en)

        Returns:
            Complete prompt string
        """
        return self.prompt_template.format(
            user_description=description,
            language=language
        )

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response (JSON) into configuration dict.

        Handles responses that may be wrapped in markdown code blocks.

        Args:
            response: Raw AI response

        Returns:
            Parsed configuration dict

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_part = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_part = response.split("```")[1].split("```")[0]
            else:
                json_part = response

            return json.loads(json_part.strip())
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}\n\nResponse: {response[:500]}")

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate generated configuration structure.

        Args:
            config: Configuration dict to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Required fields
        required = ["mode_key", "description", "yes_no_questions", "open_questions"]
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        # Validate mode_key format
        mode_key = config["mode_key"]
        if not mode_key.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid mode_key format (use snake_case): {mode_key}")

        # Validate question lists
        for q_list_name in ["yes_no_questions", "open_questions"]:
            q_list = config[q_list_name]
            if not isinstance(q_list, list):
                raise ValueError(f"{q_list_name} must be a list")

            for idx, q in enumerate(q_list):
                # Each question must have key, question, column_name
                required_fields = ["key", "question", "column_name"]
                for field in required_fields:
                    if field not in q:
                        raise ValueError(
                            f"{q_list_name}[{idx}] missing field: {field}"
                        )

                # Validate key format
                if not q["key"].replace("_", "").isalnum():
                    raise ValueError(
                        f"Invalid question key format (use snake_case): {q['key']}"
                    )

        # Check total question count
        total_questions = len(config["yes_no_questions"]) + len(config["open_questions"])
        if total_questions == 0:
            raise ValueError("Configuration must have at least one question")
        if total_questions > 15:
            warnings.warn(
                f"Too many questions ({total_questions}). Consider reducing for better usability.",
                UserWarning
            )

    def _load_prompt_template(self) -> str:
        """Load prompt template from file or use default.

        Returns:
            Prompt template string
        """
        template_path = Path(__file__).parent / "prompts" / "abstract_mode_generation.txt"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return self._get_default_template()

    def _get_default_template(self) -> str:
        """Get default embedded prompt template.

        Returns:
            Default prompt template string
        """
        return """You are an expert in academic literature screening and research methodology.

The user wants to create a literature screening mode with the following requirements:

\"\"\"
{user_description}
\"\"\"

Please generate a screening mode configuration in JSON format with this exact structure:

{{
  "mode_key": "descriptive_key_in_snake_case",
  "description": "Brief description in {language}",
  "yes_no_questions": [
    {{
      "key": "question_key_in_english",
      "question": "Question text in {language}?",
      "column_name": "Column name in {language}"
    }}
  ],
  "open_questions": [
    {{
      "key": "question_key_in_english",
      "question": "Question text in {language}?",
      "column_name": "Column name in {language}"
    }}
  ]
}}

Guidelines:
1. Use yes/no questions for binary judgments (e.g., "Is this empirical research?")
2. Use open questions for extractive information (e.g., "What are the main findings?")
3. Make questions clear, specific, professionally worded
4. Generate keys in English snake_case (e.g., "sample_size", "has_control_group")
5. Generate questions and column names in {language}
6. Aim for 3-6 yes/no questions and 2-4 open questions for usability
7. Output ONLY the JSON, no markdown formatting, no explanations

Example:
User: "我需要筛选实证研究，判断是否使用问卷法和是否在中国开展，并提取样本量和主要发现"
Output:
{{
  "mode_key": "empirical_survey_screening",
  "description": "实证研究问卷调查筛选",
  "yes_no_questions": [
    {{"key": "is_empirical", "question": "这是否为实证研究？", "column_name": "实证研究"}},
    {{"key": "uses_survey", "question": "是否使用问卷调查法？", "column_name": "问卷调查"}},
    {{"key": "chinese_context", "question": "是否在中国情境下开展？", "column_name": "中国情境"}}
  ],
  "open_questions": [
    {{"key": "sample_size", "question": "样本量是多少？", "column_name": "样本量"}},
    {{"key": "main_findings", "question": "主要研究发现是什么？", "column_name": "主要发现"}}
  ]
}}"""


class MatrixDimensionGenerator:
    """AI-powered literature matrix dimension generator.

    Generates matrix dimension configurations from user's natural language
    description of information they want to extract from literature.
    """

    # Supported dimension types
    DIMENSION_TYPES = [
        "text",
        "yes_no",
        "single_choice",
        "multiple_choice",
        "number",
        "rating",
        "list"
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize generator with AI client configuration.

        Args:
            config: Configuration dict containing AI_SERVICE, API keys, etc.
        """
        self.config = config
        self.client = AIClient(config["AI_SERVICE"], config)
        self.prompt_template = self._load_prompt_template()

    def generate_dimensions(
        self,
        description: str,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """Generate matrix dimensions from user description.

        Args:
            description: User's natural language description of extraction needs
            language: Output language (zh/en)

        Returns:
            List of dimension dicts, each with structure:
            {
                "type": str,  # one of DIMENSION_TYPES
                "key": str,
                "question": str,
                "column_name": str,
                "options": list[str],  # for choice types
                "unit": str,  # for number type
                "scale": int,  # for rating type
                "scale_description": str,  # for rating type
                "separator": str  # for list type
            }

        Raises:
            ValueError: If AI response is invalid
            Exception: If AI request fails
        """
        # 1. Build prompt
        prompt = self._build_prompt(description, language)

        # 2. Call AI
        response = self.client.request(
            prompt=prompt,
            temperature=0.3
        )

        # 3. Parse response
        dimensions = self._parse_yaml_response(response)

        # 4. Validate each dimension
        for dim in dimensions:
            self._validate_dimension(dim)

        return dimensions

    def _build_prompt(self, description: str, language: str) -> str:
        """Build AI prompt from template and user description.

        Args:
            description: User's description
            language: Target language (zh/en)

        Returns:
            Complete prompt string
        """
        return self.prompt_template.format(
            user_description=description,
            language=language
        )

    def _parse_yaml_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response (YAML) into dimension list.

        Handles responses that may be wrapped in markdown code blocks.

        Args:
            response: Raw AI response

        Returns:
            List of dimension dicts

        Raises:
            ValueError: If response cannot be parsed as YAML
        """
        try:
            # Try to extract YAML from markdown code blocks
            if "```yaml" in response:
                yaml_part = response.split("```yaml")[1].split("```")[0]
            elif "```" in response:
                yaml_part = response.split("```")[1].split("```")[0]
            else:
                yaml_part = response

            data = yaml.safe_load(yaml_part.strip())

            # Handle both formats: {"dimensions": [...]} or [...]
            if isinstance(data, dict) and "dimensions" in data:
                return data["dimensions"]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError(f"Unexpected YAML structure: {type(data)}")

        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse AI response as YAML: {e}\n\nResponse: {response[:500]}")

    def _validate_dimension(self, dimension: Dict[str, Any]) -> None:
        """Validate a single dimension configuration.

        Args:
            dimension: Dimension dict to validate

        Raises:
            ValueError: If dimension is invalid
        """
        # Required fields
        required_fields = ["type", "key", "question", "column_name"]
        for field in required_fields:
            if field not in dimension:
                raise ValueError(f"Missing required field '{field}' in dimension")

        # Type validation
        if dimension["type"] not in self.DIMENSION_TYPES:
            raise ValueError(
                f"Invalid type '{dimension['type']}'. Must be one of: {', '.join(self.DIMENSION_TYPES)}"
            )

        # Key format validation
        key = dimension["key"]
        if not key.replace("_", "").isalnum() or (key and key[0].isdigit()):
            raise ValueError(f"Invalid key format (use snake_case, no leading digits): {key}")

        # Type-specific validation
        dim_type = dimension["type"]

        if dim_type in ["single_choice", "multiple_choice"]:
            if "options" not in dimension:
                raise ValueError(f"{dim_type} requires 'options' field")
            if not isinstance(dimension["options"], list):
                raise ValueError("'options' must be a list")
            if len(dimension["options"]) < 2:
                raise ValueError("Choice types must have at least 2 options")

        if dim_type == "rating":
            if "scale" not in dimension:
                raise ValueError("Rating type requires 'scale' field")
            scale = dimension["scale"]
            if not isinstance(scale, int) or scale < 2 or scale > 10:
                raise ValueError(f"Invalid scale value: {scale} (must be integer 2-10)")

        if dim_type == "list":
            if "separator" not in dimension:
                raise ValueError("List type requires 'separator' field")

    def _load_prompt_template(self) -> str:
        """Load prompt template from file or use default.

        Returns:
            Prompt template string
        """
        template_path = Path(__file__).parent / "prompts" / "matrix_dimension_generation.txt"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return self._get_default_template()

    def _get_default_template(self) -> str:
        """Get default embedded prompt template.

        Returns:
            Default prompt template string
        """
        return """You are an expert in systematic literature review and data extraction.

The user wants to extract the following information from literature:

\"\"\"
{user_description}
\"\"\"

Please generate dimension configurations in YAML format:

dimensions:
  - type: <question_type>
    key: key_in_english
    question: "Question text in {language}"
    column_name: "Column name in {language}"
    # Type-specific fields as needed

Available types:
1. text: Open-ended text (e.g., "What are the main findings?")
2. yes_no: Binary judgment (e.g., "Is this empirical?")
3. single_choice: Choose one (e.g., "Research type: empirical/theoretical/review")
4. multiple_choice: Choose multiple (e.g., "Data collection methods")
5. number: Numerical extraction (e.g., "Sample size")
6. rating: Subjective rating 1-N (e.g., "Quality: 1-5")
7. list: Extract list (e.g., "Key variables")

Type-specific fields:
- single_choice/multiple_choice: options (list of strings, 2+ items)
- number: unit (optional, e.g., "个", "%")
- rating: scale (int 2-10), scale_description (optional)
- list: separator (e.g., "; ")

Guidelines:
- Choose most appropriate type for each info piece
- Provide comprehensive option lists for choice types (3-8 options)
- 5-12 dimensions total for usability
- Clear, answerable questions
- Keys in English snake_case
- Questions and columns in {language}
- Output ONLY YAML, no markdown formatting, no explanations

Example:
User: "提取研究方法(定量/定性/混合)、样本量、是否中国、使用的理论(多个)、研究质量评分1-5"
Output:
dimensions:
  - type: single_choice
    key: research_paradigm
    question: "研究采用的研究范式是什么？"
    column_name: "研究范式"
    options:
      - "定量研究"
      - "定性研究"
      - "混合方法"
  - type: number
    key: sample_size
    question: "样本量是多少？"
    column_name: "样本量"
    unit: "个"
  - type: yes_no
    key: chinese_context
    question: "是否在中国情境下开展？"
    column_name: "中国情境"
  - type: list
    key: theories
    question: "使用了哪些主要理论？"
    column_name: "理论框架"
    separator: "; "
  - type: rating
    key: quality
    question: "评估研究质量"
    column_name: "质量评分"
    scale: 5
    scale_description: "1=很差, 5=优秀"
"""
