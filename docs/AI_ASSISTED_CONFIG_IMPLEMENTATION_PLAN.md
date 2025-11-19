# AI 辅助配置生成 - 实施计划

**基于**: AI_ASSISTED_CONFIG_DESIGN.md
**目标**: 快速实施参考指南

---

## 快速概览

### 核心功能
1. **摘要筛选**: 用户描述需求 → AI 生成模式配置 (yes/no + open questions)
2. **文献矩阵**: 用户描述需求 → AI 生成维度配置 (7种类型)

### 技术栈
- 后端逻辑: Python 3.8+
- GUI: PyQt6
- AI: OpenAI SDK (现有 AIClient)
- 配置: YAML, JSON

---

## 实施路线图

### Phase 1: 核心生成器 (3-4天)

#### 1.1 创建 AI 配置生成器模块

**文件**: `litrx/ai_config_generator.py`

**类 1: AbstractModeGenerator**
```python
class AbstractModeGenerator:
    def __init__(self, config: dict):
        # 适配现有 AIClient 接口
        self.client = AIClient(config)
        self.prompt_template = self._load_prompt_template()

    def generate_mode(self, description: str, language: str = "zh") -> dict:
        """主入口: 生成模式配置"""
        prompt = self._build_prompt(description, language)
        req = {"messages": [{"role": "user", "content": prompt}]}
        if getattr(self.client, "supports_temperature", True):
            req["temperature"] = 0.3
        response = self.client.request(**req)
        content = response["choices"][0]["message"]["content"]
        config = self._parse_json_response(content)
        self._validate_config(config)
        return config

    def _build_prompt(self, description: str, language: str) -> str:
        """构建提示词"""
        return self.prompt_template.format(
            user_description=description,
            language=language
        )

    def _parse_json_response(self, response: str) -> dict:
        """解析 JSON 响应"""
        try:
            # 提取 JSON 部分（可能包含在 markdown 代码块中）
            if "```json" in response:
                json_part = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_part = response.split("```")[1].split("```")[0]
            else:
                json_part = response
            return json.loads(json_part.strip())
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Failed to parse AI response: {e}")

    def _validate_config(self, config: dict) -> None:
        """验证配置结构"""
        required = ["mode_key", "description", "yes_no_questions", "open_questions"]
        for field in required:
            if field not in config:
                raise ValueError(f"Missing field: {field}")

        # 验证问题格式
        for q_list in [config["yes_no_questions"], config["open_questions"]]:
            for q in q_list:
                if not all(k in q for k in ["key", "question", "column_name"]):
                    raise ValueError(f"Invalid question format: {q}")

    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        # 使用统一资源定位，兼容打包
        from .resources import resource_path
        template_path = resource_path("litrx", "prompts", "abstract_mode_generation.txt")
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return self._get_default_template()

    def _get_default_template(self) -> str:
        """默认提示词模板（内嵌）"""
        return """You are an expert in literature screening. Generate a screening mode configuration.

User's requirements:
{user_description}

Generate JSON with this structure:
{{
  "mode_key": "descriptive_snake_case",
  "description": "Brief description in {language}",
  "yes_no_questions": [
    {{"key": "english_key", "question": "Question in {language}?", "column_name": "Column in {language}"}}
  ],
  "open_questions": [
    {{"key": "english_key", "question": "Question in {language}?", "column_name": "Column in {language}"}}
  ]
}}

Guidelines:
- yes_no for binary judgments
- open for extractive/descriptive info
- 3-6 yes/no questions, 2-4 open questions
- Clear, professional wording
- Output ONLY JSON, no explanations
"""
```

**类 2: MatrixDimensionGenerator**
```python
class MatrixDimensionGenerator:
    DIMENSION_TYPES = ["text", "yes_no", "single_choice", "multiple_choice",
                       "number", "rating", "list"]

    def __init__(self, config: dict):
        self.client = AIClient(config)
        self.prompt_template = self._load_prompt_template()

    def generate_dimensions(self, description: str, language: str = "zh") -> list[dict]:
        """主入口: 生成维度列表"""
        prompt = self._build_prompt(description, language)
        req = {"messages": [{"role": "user", "content": prompt}]}
        if getattr(self.client, "supports_temperature", True):
            req["temperature"] = 0.3
        response = self.client.request(**req)
        content = response["choices"][0]["message"]["content"]
        dimensions = self._parse_yaml_response(content)
        for dim in dimensions:
            self._validate_dimension(dim)
        return dimensions

    def _parse_yaml_response(self, response: str) -> list[dict]:
        """解析 YAML 响应"""
        try:
            import yaml
            # 提取 YAML 部分
            if "```yaml" in response:
                yaml_part = response.split("```yaml")[1].split("```")[0]
            elif "```" in response:
                yaml_part = response.split("```")[1].split("```")[0]
            else:
                yaml_part = response

            data = yaml.safe_load(yaml_part.strip())
            return data.get("dimensions", []) if isinstance(data, dict) else data
        except Exception as e:
            raise ValueError(f"Failed to parse YAML response: {e}")

    def _validate_dimension(self, dim: dict) -> None:
        """验证单个维度"""
        # 必需字段
        required = ["type", "key", "question", "column_name"]
        for field in required:
            if field not in dim:
                raise ValueError(f"Missing field '{field}' in dimension")

        # 类型验证
        if dim["type"] not in self.DIMENSION_TYPES:
            raise ValueError(f"Invalid type: {dim['type']}")

        # 类型特定验证
        if dim["type"] in ["single_choice", "multiple_choice"]:
            if "options" not in dim or len(dim["options"]) < 2:
                raise ValueError("Choice types need at least 2 options")

        if dim["type"] == "rating":
            if "scale" not in dim or not (2 <= dim["scale"] <= 10):
                raise ValueError("Rating needs scale 2-10")

        if dim["type"] == "list":
            if "separator" not in dim:
                raise ValueError("List type needs separator")

    def _get_default_template(self) -> str:
        """默认提示词模板"""
        return """You are an expert in literature matrix design. Generate dimension configurations.

User's requirements:
{user_description}

Generate YAML with this structure:
dimensions:
  - type: <text|yes_no|single_choice|multiple_choice|number|rating|list>
    key: english_snake_case
    question: "Question in {language}"
    column_name: "Column in {language}"
    # Type-specific fields:
    # single_choice/multiple_choice: options (list)
    # number: unit (optional)
    # rating: scale (int), scale_description (optional)
    # list: separator

Guidelines:
- Choose appropriate type for each info piece
- Provide comprehensive options for choice types
- 5-12 dimensions total
- Output ONLY YAML, no explanations
"""
```

#### 1.2 创建提示词模板文件

**文件 1**: `litrx/prompts/abstract_mode_generation.txt`（通过 `resource_path()` 读取）
```
You are an expert in academic literature screening and research methodology.

The user wants to create a literature screening mode with the following requirements:

"""
{user_description}
"""

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
6. 3-6 yes/no questions, 2-4 open questions for usability
7. Output ONLY the JSON, no markdown, no explanations

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
}}
```

**文件 2**: `litrx/prompts/matrix_dimension_generation.txt`（通过 `resource_path()` 读取）
```
You are an expert in systematic literature review and data extraction.

The user wants to extract the following information from literature:

"""
{user_description}
"""

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
- Provide comprehensive option lists for choice types
- 5-12 dimensions total
- Clear, answerable questions
- Keys in English snake_case
- Questions and columns in {language}
- Output ONLY YAML, no markdown, no explanations

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
```

#### 1.3 单元测试（适配 OpenAI SDK 返回结构）

**文件**: `tests/test_ai_config_generator.py`

```python
import pytest
from unittest.mock import MagicMock
from litrx.ai_config_generator import AbstractModeGenerator, MatrixDimensionGenerator


@pytest.fixture
def mock_config():
    return {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-4",
        "OPENAI_API_KEY": "test-key"
    }


@pytest.fixture
def mock_ai_client(mocker):
    mock = mocker.MagicMock()
    mocker.patch("litrx.ai_config_generator.AIClient", return_value=mock)
    return mock


def test_abstract_mode_generator_basic(mock_config, mock_ai_client):
    """测试基本模式生成"""
    mock_ai_client.request.return_value = {
        "choices": [{
            "message": {
                "content": '{\n  "mode_key": "test_mode",\n  "description": "测试模式",\n  "yes_no_questions": [{"key": "q1", "question": "问题1?", "column_name": "列1"}],\n  "open_questions": [{"key": "q2", "question": "问题2?", "column_name": "列2"}]\n}'
            }
        }]
    }

    generator = AbstractModeGenerator(mock_config)
    result = generator.generate_mode("测试描述")

    assert result["mode_key"] == "test_mode"
    assert len(result["yes_no_questions"]) == 1
    assert len(result["open_questions"]) == 1


def test_matrix_dimension_generator_basic(mock_config, mock_ai_client):
    """测试基本维度生成"""
    mock_ai_client.request.return_value = {
        "choices": [{
            "message": {
                "content": 'dimensions:\n  - type: text\n    key: findings\n    question: "主要发现?"\n    column_name: "发现"\n  - type: rating\n    key: quality\n    question: "质量评分"\n    column_name: "质量"\n    scale: 5\n'
            }
        }]
    }

    generator = MatrixDimensionGenerator(mock_config)
    result = generator.generate_dimensions("测试描述")

    assert len(result) == 2
    assert result[0]["type"] == "text"
    assert result[1]["type"] == "rating"


def test_validation_errors(mock_config):
    """测试验证错误"""
    generator = AbstractModeGenerator(mock_config)

    # 缺少必需字段
    with pytest.raises(ValueError, match="Missing field"):
        generator._validate_config({"mode_key": "test"})

    # 问题格式错误
    with pytest.raises(ValueError):
        generator._validate_config({
            "mode_key": "test",
            "description": "test",
            "yes_no_questions": [{"invalid": "format"}],
            "open_questions": []
        })
```

---

### Phase 2: GUI 对话框 (2-3天，PyQt6)

#### 2.1 摘要模式 AI 助手对话框（PyQt6）

**文件**: `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py`（PyQt6）

```python
"""AI assistant dialog for creating abstract screening modes."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional

from ...ai_config_generator import AbstractModeGenerator
from ...i18n import t


class AIModeAssistantDialog:
    """Dialog for AI-assisted mode creation."""

    def __init__(self, parent: tk.Tk, config: dict):
        self.parent = parent
        self.config = config
        self.generator = AbstractModeGenerator(config)
        self.result = None  # Generated config if user clicks Apply

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t("ai_mode_assistant_title"))
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _create_widgets(self):
        # 省略：此处为 PyQt6 界面元素，见设计文档（采用 QLabel/QTextEdit/QPushButton 组合）

        # 2. 用户输入框
        ttk.Label(main_frame, text=t("describe_your_needs")).pack(anchor=tk.W)
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.input_text = tk.Text(input_frame, height=6, wrap=tk.WORD)
        input_scroll = ttk.Scrollbar(input_frame, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. 生成按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        self.generate_btn = ttk.Button(
            btn_frame,
            text=t("generate_config"),
            command=self._on_generate
        )
        self.generate_btn.pack()

        # 4. 加载状态
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack(pady=5)

        # 5. 预览区域
        preview_label = ttk.Label(main_frame, text=t("preview_label"))
        preview_label.pack(anchor=tk.W, pady=(10, 5))

        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(preview_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 6. 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(pady=10)

        self.regenerate_btn = ttk.Button(
            bottom_frame,
            text=t("regenerate"),
            command=self._on_generate,
            state=tk.DISABLED
        )
        self.regenerate_btn.pack(side=tk.LEFT, padx=5)

        self.apply_btn = ttk.Button(
            bottom_frame,
            text=t("apply"),
            command=self._on_apply,
            state=tk.DISABLED
        )
        self.apply_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom_frame, text=t("cancel"), command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_generate(self):
        """Handle generate button click."""
        description = self.input_text.get("1.0", tk.END).strip()
        if not description:
            messagebox.showwarning(t("warning"), t("please_enter_description"))
            return

        # 禁用按钮
        self.generate_btn.config(state=tk.DISABLED)
        self.regenerate_btn.config(state=tk.DISABLED)
        self.status_label.config(text=t("generating"))

        # 后台线程生成
        thread = threading.Thread(
            target=self._generate_thread,
            args=(description,),
            daemon=True
        )
        thread.start()

    def _generate_thread(self, description: str):
        """Background thread for generation."""
        try:
            language = self.config.get("LANGUAGE", "zh")
            result = self.generator.generate_mode(description, language)
            self.dialog.after(0, self._on_generation_success, result)
        except Exception as e:
            self.dialog.after(0, self._on_generation_error, str(e))

    def _on_generation_success(self, result: dict):
        """Handle successful generation."""
        self.generated_config = result
        self.status_label.config(text=t("generation_success"), foreground="green")

        # 显示预览
        preview = self._format_preview(result)
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
        self.preview_text.config(state=tk.DISABLED)

        # 启用按钮
        self.generate_btn.config(state=tk.NORMAL)
        self.regenerate_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)

    def _on_generation_error(self, error: str):
        """Handle generation error."""
        self.status_label.config(text=t("generation_failed"), foreground="red")
        messagebox.showerror(t("error"), f"{t('generation_error')}:\n{error}")

        self.generate_btn.config(state=tk.NORMAL)

    def _format_preview(self, config: dict) -> str:
        """Format config for preview display."""
        lines = []
        lines.append(f"模式名称: {config['mode_key']}")
        lines.append(f"描述: {config['description']}")
        lines.append("")

        lines.append(f"是非判断问题 ({len(config['yes_no_questions'])}):")
        for q in config['yes_no_questions']:
            lines.append(f"  ✓ {q['question']}")

        lines.append("")
        lines.append(f"开放问题 ({len(config['open_questions'])}):")
        for q in config['open_questions']:
            lines.append(f"  • {q['question']}")

        return "\n".join(lines)

    def _on_apply(self):
        """Handle apply button."""
        self.result = self.generated_config
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle cancel button."""
        self.result = None
        self.dialog.destroy()

    def _center_dialog(self):
        """Center dialog on parent."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
```

#### 2.2 文献矩阵 AI 助手对话框

**文件**: `litrx/gui/dialogs/ai_dimension_assistant.py`

```python
"""AI assistant dialog for creating matrix dimensions."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from ...ai_config_generator import MatrixDimensionGenerator
from ...i18n import t


class AIDimensionAssistantDialog:
    """Dialog for AI-assisted dimension creation."""

    def __init__(self, parent: tk.Toplevel, config: dict):
        self.parent = parent
        self.config = config
        self.generator = MatrixDimensionGenerator(config)
        self.result = None  # List of selected dimensions

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t("ai_dimension_assistant_title"))
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 引导文本
        guide_text = t("ai_dimension_guide")
        ttk.Label(main_frame, text=guide_text, wraplength=850).pack(anchor=tk.W, pady=(0, 10))

        # 输入框
        ttk.Label(main_frame, text=t("describe_your_needs")).pack(anchor=tk.W)
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        self.input_text = tk.Text(input_frame, height=4, wrap=tk.WORD)
        self.input_text.pack(fill=tk.X)

        # 生成按钮
        self.generate_btn = ttk.Button(
            main_frame,
            text=t("generate_dimensions"),
            command=self._on_generate
        )
        self.generate_btn.pack(pady=10)

        # 状态
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack()

        # 预览表格
        ttk.Label(main_frame, text=t("generated_dimensions")).pack(anchor=tk.W, pady=(10, 5))

        # 全选复选框
        self.select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text=t("select_all"),
            variable=self.select_all_var,
            command=self._on_select_all
        ).pack(anchor=tk.W)

        # 表格
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("select", "type", "question", "column", "details")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.tree.heading("select", text="✓")
        self.tree.heading("type", text=t("type"))
        self.tree.heading("question", text=t("question"))
        self.tree.heading("column", text=t("column_name"))
        self.tree.heading("details", text=t("details"))

        self.tree.column("select", width=30)
        self.tree.column("type", width=100)
        self.tree.column("question", width=350)
        self.tree.column("column", width=120)
        self.tree.column("details", width=150)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击切换选择
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # 统计
        self.stats_label = ttk.Label(main_frame, text="")
        self.stats_label.pack(pady=5)

        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(pady=10)

        self.regenerate_btn = ttk.Button(
            bottom_frame,
            text=t("regenerate"),
            command=self._on_generate,
            state=tk.DISABLED
        )
        self.regenerate_btn.pack(side=tk.LEFT, padx=5)

        self.apply_btn = ttk.Button(
            bottom_frame,
            text=t("apply_selected"),
            command=self._on_apply,
            state=tk.DISABLED
        )
        self.apply_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom_frame, text=t("cancel"), command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _on_generate(self):
        """Handle generate button."""
        description = self.input_text.get("1.0", tk.END).strip()
        if not description:
            messagebox.showwarning(t("warning"), t("please_enter_description"))
            return

        self.generate_btn.config(state=tk.DISABLED)
        self.status_label.config(text=t("generating"))

        thread = threading.Thread(
            target=self._generate_thread,
            args=(description,),
            daemon=True
        )
        thread.start()

    def _generate_thread(self, description: str):
        """Background generation."""
        try:
            language = self.config.get("LANGUAGE", "zh")
            dimensions = self.generator.generate_dimensions(description, language)
            self.dialog.after(0, self._on_generation_success, dimensions)
        except Exception as e:
            self.dialog.after(0, self._on_generation_error, str(e))

    def _on_generation_success(self, dimensions: list):
        """Handle successful generation."""
        self.generated_dimensions = dimensions
        self.status_label.config(text=t("generation_success"), foreground="green")

        # 填充表格
        self.tree.delete(*self.tree.get_children())

        type_names = {
            "text": "开放文本",
            "yes_no": "是/否",
            "single_choice": "单选",
            "multiple_choice": "多选",
            "number": "数值",
            "rating": "评分",
            "list": "列表"
        }

        for dim in dimensions:
            dim_type = type_names.get(dim["type"], dim["type"])
            question = dim["question"][:50] + "..." if len(dim["question"]) > 50 else dim["question"]
            column = dim["column_name"]

            # 详情
            details = []
            if "options" in dim:
                details.append(f"{len(dim['options'])}选项")
            if "unit" in dim:
                details.append(f"单位:{dim['unit']}")
            if "scale" in dim:
                details.append(f"1-{dim['scale']}分")
            detail_str = ", ".join(details) if details else "-"

            self.tree.insert("", tk.END, values=("☑", dim_type, question, column, detail_str))

        self._update_stats()

        # 启用按钮
        self.generate_btn.config(state=tk.NORMAL)
        self.regenerate_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)

    def _on_generation_error(self, error: str):
        """Handle error."""
        self.status_label.config(text=t("generation_failed"), foreground="red")
        messagebox.showerror(t("error"), f"{t('generation_error')}:\n{error}")
        self.generate_btn.config(state=tk.NORMAL)

    def _on_tree_double_click(self, event):
        """Toggle selection on double-click."""
        item = self.tree.identify_row(event.y)
        if item:
            values = list(self.tree.item(item, "values"))
            values[0] = "☐" if values[0] == "☑" else "☑"
            self.tree.item(item, values=values)
            self._update_stats()

    def _on_select_all(self):
        """Toggle all selections."""
        symbol = "☑" if self.select_all_var.get() else "☐"
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[0] = symbol
            self.tree.item(item, values=values)
        self._update_stats()

    def _update_stats(self):
        """Update selection statistics."""
        total = len(self.tree.get_children())
        selected = sum(1 for item in self.tree.get_children()
                      if self.tree.item(item, "values")[0] == "☑")
        self.stats_label.config(text=f"已选择 {selected}/{total} 个维度")

    def _on_apply(self):
        """Apply selected dimensions."""
        selected_dims = []
        for idx, item in enumerate(self.tree.get_children()):
            if self.tree.item(item, "values")[0] == "☑":
                selected_dims.append(self.generated_dimensions[idx])

        if not selected_dims:
            messagebox.showwarning(t("warning"), t("please_select_dimensions"))
            return

        self.result = selected_dims
        self.dialog.destroy()

    def _on_cancel(self):
        """Cancel."""
        self.result = None
        self.dialog.destroy()

    def _center_dialog(self):
        """Center on parent."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
```

#### 2.3 国际化翻译

**文件**: `litrx/i18n.py` (添加以下翻译)

```python
# 在 TRANSLATIONS 字典中添加：

"zh": {
    # ... 现有翻译 ...

    # AI 助手相关
    "ai_mode_assistant_title": "AI 辅助创建筛选模式",
    "ai_dimension_assistant_title": "AI 辅助创建分析维度",
    "ai_mode_guide": "请用自然语言描述您的文献筛选需求。您可以包括：研究领域、需要判断的特征、需要提取的信息等。",
    "ai_dimension_guide": "请用自然语言描述您需要从文献中提取的信息。您可以包括：研究特征、数值信息、分类信息、评估需求等。",
    "describe_your_needs": "请描述您的需求：",
    "generate_config": "生成配置",
    "generate_dimensions": "生成维度",
    "generating": "AI 正在生成配置，请稍候...",
    "generation_success": "生成成功！",
    "generation_failed": "生成失败",
    "generation_error": "生成配置时出错",
    "preview_label": "生成的配置预览：",
    "generated_dimensions": "生成的维度配置（请选择需要的维度）：",
    "regenerate": "重新生成",
    "apply_selected": "应用选中",
    "select_all": "全选",
    "please_enter_description": "请输入需求描述",
    "please_select_dimensions": "请至少选择一个维度",
    "ai_assist_create_mode": "🤖 AI 辅助创建",
    "ai_assist_create_dimension": "🤖 AI 辅助创建",
},

"en": {
    # ... 现有翻译 ...

    "ai_mode_assistant_title": "AI-Assisted Mode Creation",
    "ai_dimension_assistant_title": "AI-Assisted Dimension Creation",
    "ai_mode_guide": "Describe your literature screening needs in natural language. Include: research field, features to judge, information to extract.",
    "ai_dimension_guide": "Describe the information you want to extract from literature. Include: research characteristics, numerical data, classifications, evaluations.",
    "describe_your_needs": "Describe your needs:",
    "generate_config": "Generate Config",
    "generate_dimensions": "Generate Dimensions",
    "generating": "AI is generating configuration...",
    "generation_success": "Generation successful!",
    "generation_failed": "Generation failed",
    "generation_error": "Error generating configuration",
    "preview_label": "Generated Configuration Preview:",
    "generated_dimensions": "Generated Dimensions (select the ones you need):",
    "regenerate": "Regenerate",
    "apply_selected": "Apply Selected",
    "select_all": "Select All",
    "please_enter_description": "Please enter a description",
    "please_select_dimensions": "Please select at least one dimension",
    "ai_assist_create_mode": "🤖 AI Assist",
    "ai_assist_create_dimension": "🤖 AI Assist",
}
```

---

### Phase 3: 集成到现有标签页 (1-2天)

#### 3.1 集成到摘要筛选标签页

**文件**: `litrx/gui/tabs/abstract/abstract_tab.py`

在模式选择区域添加 AI 助手按钮：

```python
# 在 __init__ 方法中，模式选择部分后添加：

# AI 助手按钮
self.ai_assist_btn = ttk.Button(
    mode_frame,
    text=t("ai_assist_create_mode"),
    command=self.open_ai_assistant
)
self.ai_assist_btn.pack(side=tk.LEFT, padx=5)

# 添加方法：
def open_ai_assistant(self):
    """Open AI assistant dialog for mode creation."""
    from ...dialogs.ai_mode_assistant import AIModeAssistantDialog

    # 构建配置
    config = self.app.build_config()

    # 打开对话框
    dialog = AIModeAssistantDialog(self.app.root, config)
    self.app.root.wait_window(dialog.dialog)

    # 处理结果
    if dialog.result:
        self._save_generated_mode(dialog.result)

def _save_generated_mode(self, mode_config: dict):
    """Save AI-generated mode to questions_config.json."""
    import json
    from pathlib import Path

    config_path = Path("questions_config.json")

    # 加载现有配置
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            all_modes = json.load(f)
    else:
        all_modes = {}

    # 检查是否已存在
    mode_key = mode_config["mode_key"]
    if mode_key in all_modes:
        if not messagebox.askyesno(
            t("confirm"),
            f"模式 '{mode_key}' 已存在，是否覆盖？"
        ):
            return

    # 保存
    all_modes[mode_key] = {
        "description": mode_config["description"],
        "yes_no_questions": mode_config["yes_no_questions"],
        "open_questions": mode_config["open_questions"]
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(all_modes, f, ensure_ascii=False, indent=2)

    # 刷新模式列表
    self._load_modes()
    self.mode_var.set(mode_key)

    messagebox.showinfo(t("success"), f"模式 '{mode_key}' 已成功创建！")
```

#### 3.2 集成到矩阵维度编辑器

**文件**: `litrx/gui/dialogs/dimension_editor.py`

在按钮区域添加 AI 助手按钮：

```python
# 在 _create_widgets 方法的按钮区域添加：

# AI 助手按钮
ttk.Button(
    left_btns,
    text=t("ai_assist_create_dimension"),
    command=self._ai_assist_create,
    width=15
).pack(side=tk.LEFT, padx=2)

# 添加方法：
def _ai_assist_create(self):
    """Open AI assistant for dimension creation."""
    from .ai_dimension_assistant import AIDimensionAssistantDialog

    # 从父窗口获取配置
    config = getattr(self.parent, 'build_config', lambda: {})()

    # 打开对话框
    dialog = AIDimensionAssistantDialog(self.dialog, config)
    self.dialog.wait_window(dialog.dialog)

    # 处理结果
    if dialog.result:
        # 添加选中的维度
        self.dimensions.extend(dialog.result)
        self._populate_list()
        messagebox.showinfo(
            t("success"),
            f"成功添加 {len(dialog.result)} 个维度！"
        )
```

---

### Phase 4: 测试与优化 (2-3天)

#### 4.1 端到端测试清单

- [ ] 摘要模式生成
  - [ ] 简单需求（1-2个问题）
  - [ ] 复杂需求（5-10个问题）
  - [ ] 中文描述
  - [ ] 英文描述
  - [ ] 边界情况（空描述、超长描述）

- [ ] 矩阵维度生成
  - [ ] 所有7种类型的维度
  - [ ] 混合类型需求
  - [ ] 选项式问题的选项质量
  - [ ] 部分选择功能

- [ ] 错误处理
  - [ ] AI API 调用失败
  - [ ] 网络超时
  - [ ] 无效响应格式
  - [ ] 验证失败

- [ ] 集成测试
  - [ ] 保存到配置文件
  - [ ] 配置加载与使用
  - [ ] 与现有功能兼容性

#### 4.2 提示词优化策略

1. **收集失败案例**
   - 记录生成质量不佳的示例
   - 分析 AI 误解的原因

2. **迭代改进**
   - 添加更多示例到提示词
   - 优化指令措辞
   - 调整温度参数

3. **A/B 测试**
   - 测试不同提示词版本
   - 收集用户反馈

---

### Phase 5: 文档更新 (1天)

#### 5.1 更新 README.md

在功能介绍部分添加：

```markdown
### 🤖 AI 辅助配置生成（新功能）

无需手动编写配置，只需用自然语言描述需求，AI 自动生成：

- **摘要筛选模式**：描述筛选需求 → AI 生成问题配置
- **文献矩阵维度**：描述提取需求 → AI 生成维度配置

**示例**：
> 用户："我需要筛选实证研究，判断是否使用问卷法，并提取样本量"
>
> AI 自动生成：
> - Yes/No 问题："是否为实证研究？"、"是否使用问卷调查法？"
> - 开放问题："样本量是多少？"
```

#### 5.2 更新 CLAUDE.md

添加新功能的开发指南部分。

---

## 关键技术决策

### 1. 为什么使用提示词文件而非硬编码？
- ✅ 易于迭代优化
- ✅ 支持多语言版本
- ✅ 用户可自定义（高级功能）

### 2. 为什么分离 AbstractModeGenerator 和 MatrixDimensionGenerator？
- ✅ 单一职责原则
- ✅ 不同的验证规则
- ✅ 独立演进

### 3. 为什么使用后台线程？
- ✅ 避免 GUI 冻结
- ✅ 更好的用户体验
- ✅ 支持取消操作（未来）

### 4. 为什么矩阵维度支持部分选择？
- ✅ AI 可能生成冗余维度
- ✅ 用户可能只需要部分
- ✅ 灵活性更高

---

## 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| AI 生成质量不稳定 | 低温度(0.3) + 详细提示词 + 重新生成功能 |
| API 调用失败 | 重试机制 + 清晰错误提示 + 降级到手动 |
| 格式解析失败 | 严格验证 + 容错解析（提取代码块）|
| 用户描述不清晰 | 详细引导文本 + 示例 + 迭代功能 |

---

## 开发检查清单

### Phase 1 ✅
- [ ] `ai_config_generator.py` - AbstractModeGenerator
- [ ] `ai_config_generator.py` - MatrixDimensionGenerator
- [ ] `prompts/abstract_mode_generation.txt`
- [ ] `prompts/matrix_dimension_generation.txt`
- [ ] `tests/test_ai_config_generator.py`

### Phase 2 ✅
- [ ] `gui/dialogs/ai_mode_assistant.py`
- [ ] `gui/dialogs/ai_dimension_assistant.py`
- [ ] `i18n.py` 翻译更新

### Phase 3 ✅
- [ ] `gui/tabs/abstract/abstract_tab.py` 集成
- [ ] `gui/dialogs/dimension_editor.py` 集成

### Phase 4 ✅
- [ ] 端到端测试
- [ ] 提示词优化
- [ ] 错误处理完善

### Phase 5 ✅
- [ ] README.md 更新
- [ ] Chinese_README.md 更新
- [ ] CLAUDE.md 更新

---

**预计总工时**: 9-13天
**优先级**: 高（核心功能增强）
**依赖**: 无（基于现有 AIClient）
