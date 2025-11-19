# AI 辅助配置生成功能 - 需求文档与设计方案

**版本**: 1.0
**日期**: 2025-11-19
**状态**: 设计阶段

---

## 1. 功能概述

### 1.1 背景与动机

当前，用户需要手动配置摘要筛选模式和文献矩阵维度，这需要：
- 理解 JSON/YAML 配置文件格式
- 熟悉问题类型的技术定义（如 yes_no、single_choice、multiple_choice 等）
- 手动设计合理的筛选问题

这对非技术用户来说存在较高的使用门槛。

### 1.2 核心价值

通过引入 AI 辅助配置生成功能，用户可以：
1. **用自然语言描述需求**，无需理解技术细节
2. **快速生成专业的配置**，由 AI 自动选择合适的问题类型
3. **获得智能建议**，AI 根据研究领域和目标自动设计合理的问题
4. **迭代优化配置**，可以在 AI 生成的基础上继续调整

### 1.3 应用场景

#### 场景 1：摘要筛选模式创建
**用户描述**：
> "我想创建一个筛选心理学实证研究的模式。我需要知道研究是否使用了实验方法，样本量是多少，是否有对照组，以及研究的主要发现是什么。"

**AI 生成结果**：
- 模式名称：psychology_empirical_screening
- Yes/No 问题：
  - 是否使用实验方法？
  - 是否有对照组？
- 开放问题：
  - 样本量是多少？
  - 主要研究发现是什么？

#### 场景 2：文献矩阵维度创建
**用户描述**：
> "我在做关于机器学习应用的文献综述。需要提取每篇文献使用的算法类型（可能有多个）、数据集大小、准确率，以及研究的应用领域。另外我想评估每篇文献的方法创新性。"

**AI 生成结果**：
- 多选题维度：使用的算法类型（选项：深度学习、传统机器学习、强化学习等）
- 数值提取维度：数据集大小、准确率
- 单选题维度：应用领域
- 评分维度：方法创新性（1-5分）

---

## 2. 功能需求

### 2.1 功能模块

#### 模块 1：摘要筛选模式 AI 助手
**位置**：摘要筛选标签页（Abstract Tab）

**功能点**：
1. **"AI 辅助创建模式"按钮**
   - 位置：模式选择下拉框旁边
   - 触发：打开 AI 助手对话框

2. **AI 助手对话框**
   - 输入框：多行文本，让用户描述需求
   - 提示文本：引导用户如何描述（见后文）
   - "生成配置"按钮：调用 AI 生成配置
   - 预览区域：显示 AI 生成的问题列表
   - "应用"按钮：将生成的配置添加到 questions_config.json
   - "重新生成"按钮：基于相同描述重新生成
   - "取消"按钮：放弃生成

3. **生成后的配置管理**
   - 自动添加到模式列表
   - 用户可以通过"编辑问题"功能继续手动调整
   - 保存到 questions_config.json

#### 模块 2：文献矩阵维度 AI 助手
**位置**：文献矩阵标签页（Matrix Tab）

**功能点**：
1. **"AI 辅助创建维度"按钮**
   - 位置：维度编辑器对话框中
   - 触发：打开 AI 助手对话框

2. **AI 助手对话框**
   - 输入框：多行文本，让用户描述需求
   - 提示文本：引导用户如何描述
   - "生成配置"按钮：调用 AI 生成维度配置
   - 预览区域：显示 AI 生成的维度列表（表格形式）
   - 批量操作：
     - "全选/全不选"复选框
     - 每个维度有复选框，用户可以选择性应用
   - "应用选中"按钮：将选中的维度添加到配置
   - "重新生成"按钮：重新生成
   - "取消"按钮：放弃生成

3. **生成后的配置管理**
   - 添加到现有维度列表
   - 用户可以继续手动编辑每个维度
   - 保存到配置文件

### 2.2 用户交互流程

#### 流程 1：摘要筛选模式创建

```
用户点击"AI 辅助创建模式"
  → 打开对话框
  → 用户输入需求描述
  → 点击"生成配置"
  → 显示加载状态
  → AI 返回结果
  → 显示预览（模式名、问题列表）
  → 用户确认/修改
  → 点击"应用"
  → 保存到 questions_config.json
  → 关闭对话框
  → 模式出现在下拉列表中
```

#### 流程 2：文献矩阵维度创建

```
用户打开"编辑维度"对话框
  → 点击"AI 辅助创建维度"
  → 打开 AI 助手对话框
  → 用户输入需求描述
  → 点击"生成配置"
  → 显示加载状态
  → AI 返回结果
  → 显示维度列表预览（表格：类型、问题、列名、选项等）
  → 用户选择需要的维度（复选框）
  → 点击"应用选中"
  → 选中的维度添加到维度列表
  → 关闭 AI 助手对话框
  → 用户可继续手动编辑
```

### 2.3 AI 生成规则

#### 2.3.1 摘要筛选模式生成

**输入**：用户的自然语言描述

**输出**：JSON 格式的模式配置
```json
{
  "mode_key": "user_generated_mode_1",
  "description": "用户描述的简化版",
  "yes_no_questions": [
    {
      "key": "question_1",
      "question": "问题文本？",
      "column_name": "列名"
    }
  ],
  "open_questions": [
    {
      "key": "question_2",
      "question": "问题文本？",
      "column_name": "列名"
    }
  ]
}
```

**AI 任务**：
1. 分析用户需求，识别：
   - 需要判断的是非问题（→ yes_no_questions）
   - 需要提取描述性信息的问题（→ open_questions）
2. 生成合理的问题文本（清晰、专业、符合学术规范）
3. 自动生成字段标识符（key，使用英文蛇形命名）
4. 自动生成列名（中文或英文，根据用户语言）
5. 生成模式描述

#### 2.3.2 文献矩阵维度生成

**输入**：用户的自然语言描述

**输出**：YAML 格式的维度配置列表
```yaml
dimensions:
  - type: single_choice
    key: research_type
    question: "研究类型是什么？"
    column_name: "研究类型"
    options:
      - "实证研究"
      - "理论研究"
      - "文献综述"

  - type: number
    key: sample_size
    question: "样本量是多少？"
    column_name: "样本量"
    unit: "个"

  - type: rating
    key: innovation
    question: "评估研究的创新性"
    column_name: "创新性评分"
    scale: 5
    scale_description: "1=无创新, 5=高度创新"
```

**AI 任务**：
1. 分析用户需求，识别：
   - 需要提取的信息类型
   - 合适的问题类型（7种类型中选择）
   - 选项式问题的具体选项
2. 为每个维度选择最合适的类型：
   - `text`：开放式描述（如"主要发现"）
   - `yes_no`：是非判断（如"是否实证研究"）
   - `single_choice`：单选（如"研究范式"）
   - `multiple_choice`：多选（如"使用的方法"）
   - `number`：数值提取（如"样本量"）
   - `rating`：主观评分（如"研究质量"）
   - `list`：列表提取（如"关键变量"）
3. 为选择题自动生成合理的选项列表
4. 生成专业的问题文本
5. 自动生成字段标识符和列名

### 2.4 提示词引导文本

#### 摘要筛选模式

对话框中的引导文本：
```
请用自然语言描述您的筛选需求。您可以包括：

1. 研究领域或主题（如：心理学、机器学习、市场营销）
2. 需要判断的特征（如：是否为实证研究、是否使用定量方法）
3. 需要提取的信息（如：样本量、主要发现、使用的理论）

示例：
"我想筛选关于消费者行为的实证研究。需要判断是否使用了问卷调查法，
是否在中国情境下开展，并提取研究的主要发现和理论框架。"
```

#### 文献矩阵维度

对话框中的引导文本：
```
请用自然语言描述您需要提取的文献信息。您可以包括：

1. 研究特征（如：研究类型、研究方法、样本特征）
2. 数值信息（如：样本量、效应量、年份）
3. 分类信息（如：研究领域、理论框架）
4. 评估需求（如：研究质量、相关性）

示例：
"我需要提取每篇文献的研究方法（定量/定性/混合），样本量，
是否在中国开展，使用的主要理论（可能有多个），以及我对
研究质量的评分（1-5分）。"
```

---

## 3. 技术设计

### 3.1 架构设计

#### 3.1.1 组件架构

```
┌─────────────────────────────────────────────┐
│           GUI Layer (Tkinter)                │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │ Abstract Tab    │  │  Matrix Tab      │  │
│  │ - AI助手按钮    │  │  - AI助手按钮    │  │
│  └────────┬────────┘  └────────┬─────────┘  │
└───────────┼────────────────────┼─────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────┐
│      AI Configuration Generator Module       │
│  ┌──────────────────────────────────────┐   │
│  │  AbstractModeGenerator                │   │
│  │  - generate_mode(description)         │   │
│  │  - parse_ai_response()                │   │
│  │  - validate_config()                  │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  MatrixDimensionGenerator             │   │
│  │  - generate_dimensions(description)   │   │
│  │  - parse_ai_response()                │   │
│  │  - validate_dimensions()              │   │
│  └──────────────────────────────────────┘   │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│           AIClient (existing)                │
│  - request(prompt, temperature)              │
└─────────────────────────────────────────────┘
```

#### 3.1.2 新增文件

```
litrx/
├── ai_config_generator.py          # 新增：AI 配置生成器核心逻辑
│   ├── AbstractModeGenerator       # 摘要模式生成器
│   └── MatrixDimensionGenerator    # 矩阵维度生成器
│
├── gui/
│   └── dialogs/
│       ├── ai_mode_assistant.py    # 新增：摘要模式 AI 助手对话框
│       └── ai_dimension_assistant.py # 新增：矩阵维度 AI 助手对话框
│
└── prompts/
    ├── abstract_mode_generation.yaml  # 新增：摘要模式生成提示词模板
    └── matrix_dimension_generation.yaml # 新增：矩阵维度生成提示词模板
```

### 3.2 数据流设计

#### 3.2.1 摘要模式生成流程

```
用户描述 (str)
    ↓
AbstractModeGenerator.generate_mode()
    ↓
构建提示词（使用模板 + 用户描述）
    ↓
AIClient.request(prompt)
    ↓
AI 响应（JSON 格式字符串）
    ↓
parse_ai_response() → 解析为 Python dict
    ↓
validate_config() → 验证配置有效性
    ↓
返回验证后的配置 dict
    ↓
保存到 questions_config.json
```

#### 3.2.2 矩阵维度生成流程

```
用户描述 (str)
    ↓
MatrixDimensionGenerator.generate_dimensions()
    ↓
构建提示词（使用模板 + 用户描述）
    ↓
AIClient.request(prompt)
    ↓
AI 响应（YAML 格式字符串）
    ↓
parse_ai_response() → 解析为 Python list[dict]
    ↓
validate_dimensions() → 验证每个维度
    ↓
返回验证后的维度列表
    ↓
添加到现有维度配置
```

### 3.3 核心类设计

#### 3.3.1 AbstractModeGenerator

```python
class AbstractModeGenerator:
    """AI-powered abstract screening mode generator."""

    def __init__(self, config: dict):
        """Initialize with AI client configuration."""
        self.config = config
        self.client = AIClient(config["AI_SERVICE"], config)
        self.prompt_template = self._load_prompt_template()

    def generate_mode(
        self,
        description: str,
        language: str = "zh"
    ) -> dict:
        """Generate screening mode from user description.

        Args:
            description: User's natural language description
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
            ValueError: If AI response is invalid
            AIClientError: If AI request fails
        """
        # 1. 构建提示词
        prompt = self._build_prompt(description, language)

        # 2. 调用 AI
        response = self.client.request(
            prompt=prompt,
            temperature=0.3  # 较低温度保证稳定性
        )

        # 3. 解析响应
        config = self._parse_response(response)

        # 4. 验证配置
        self._validate_config(config)

        return config

    def _build_prompt(self, description: str, language: str) -> str:
        """Build AI prompt from template and user description."""
        pass

    def _parse_response(self, response: str) -> dict:
        """Parse AI response (JSON) into configuration dict."""
        pass

    def _validate_config(self, config: dict) -> None:
        """Validate generated configuration structure."""
        pass

    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        pass
```

#### 3.3.2 MatrixDimensionGenerator

```python
class MatrixDimensionGenerator:
    """AI-powered literature matrix dimension generator."""

    # 7种支持的问题类型
    SUPPORTED_TYPES = [
        "text", "yes_no", "single_choice",
        "multiple_choice", "number", "rating", "list"
    ]

    def __init__(self, config: dict):
        """Initialize with AI client configuration."""
        self.config = config
        self.client = AIClient(config["AI_SERVICE"], config)
        self.prompt_template = self._load_prompt_template()

    def generate_dimensions(
        self,
        description: str,
        language: str = "zh"
    ) -> list[dict]:
        """Generate matrix dimensions from user description.

        Args:
            description: User's natural language description
            language: Output language (zh/en)

        Returns:
            List of dimension dicts, each with structure:
            {
                "type": str,  # one of SUPPORTED_TYPES
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
            AIClientError: If AI request fails
        """
        # 1. 构建提示词
        prompt = self._build_prompt(description, language)

        # 2. 调用 AI
        response = self.client.request(
            prompt=prompt,
            temperature=0.3
        )

        # 3. 解析响应
        dimensions = self._parse_response(response)

        # 4. 验证每个维度
        for dim in dimensions:
            self._validate_dimension(dim)

        return dimensions

    def _build_prompt(self, description: str, language: str) -> str:
        """Build AI prompt from template and user description."""
        pass

    def _parse_response(self, response: str) -> list[dict]:
        """Parse AI response (YAML) into dimension list."""
        pass

    def _validate_dimension(self, dimension: dict) -> None:
        """Validate a single dimension configuration."""
        # 验证必需字段
        required_fields = ["type", "key", "question", "column_name"]
        for field in required_fields:
            if field not in dimension:
                raise ValueError(f"Missing required field: {field}")

        # 验证类型
        if dimension["type"] not in self.SUPPORTED_TYPES:
            raise ValueError(f"Invalid type: {dimension['type']}")

        # 类型特定验证
        if dimension["type"] in ["single_choice", "multiple_choice"]:
            if "options" not in dimension or not dimension["options"]:
                raise ValueError("Choice type requires options")

        if dimension["type"] == "rating":
            if "scale" not in dimension:
                raise ValueError("Rating type requires scale")

    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        pass
```

#### 3.3.3 GUI 对话框类

```python
class AIModeAssistantDialog:
    """Dialog for AI-assisted mode creation."""

    def __init__(self, parent: tk.Tk, generator: AbstractModeGenerator):
        """Initialize dialog.

        Args:
            parent: Parent window
            generator: AbstractModeGenerator instance
        """
        self.parent = parent
        self.generator = generator
        self.result = None  # Generated config if successful

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("AI 辅助创建筛选模式")
        self.dialog.geometry("700x600")

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # 1. 引导文本
        # 2. 用户输入框（多行文本）
        # 3. 生成按钮
        # 4. 预览区域（显示生成的配置）
        # 5. 应用/取消按钮
        pass

    def _on_generate(self) -> None:
        """Handle generate button click."""
        # 1. 获取用户描述
        # 2. 显示加载状态
        # 3. 调用 generator.generate_mode()
        # 4. 显示结果预览
        # 5. 启用应用按钮
        pass

    def _on_apply(self) -> None:
        """Handle apply button click."""
        # 1. 将生成的配置保存到 result
        # 2. 关闭对话框
        pass


class AIDimensionAssistantDialog:
    """Dialog for AI-assisted dimension creation."""

    def __init__(self, parent: tk.Toplevel, generator: MatrixDimensionGenerator):
        """Initialize dialog.

        Args:
            parent: Parent window
            generator: MatrixDimensionGenerator instance
        """
        self.parent = parent
        self.generator = generator
        self.result = None  # List of selected dimensions if successful

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("AI 辅助创建分析维度")
        self.dialog.geometry("900x700")

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # 1. 引导文本
        # 2. 用户输入框（多行文本）
        # 3. 生成按钮
        # 4. 预览区域（表格形式，带复选框）
        # 5. 应用选中/取消按钮
        pass

    def _on_generate(self) -> None:
        """Handle generate button click."""
        # 1. 获取用户描述
        # 2. 显示加载状态
        # 3. 调用 generator.generate_dimensions()
        # 4. 在表格中显示结果，每行带复选框
        # 5. 启用应用按钮
        pass

    def _on_apply(self) -> None:
        """Handle apply button click."""
        # 1. 收集选中的维度
        # 2. 保存到 result
        # 3. 关闭对话框
        pass
```

### 3.4 提示词模板设计

#### 3.4.1 摘要模式生成提示词

文件：`litrx/prompts/abstract_mode_generation.yaml`

```yaml
system_prompt: |
  You are an expert in academic literature screening and research methodology.
  Your task is to help researchers create abstract screening configurations.

  Given a user's description of their screening needs, generate a structured
  configuration with appropriate yes/no questions and open-ended questions.

user_prompt_template: |
  The user wants to create a literature screening mode with the following requirements:

  """
  {user_description}
  """

  Please generate a screening mode configuration in JSON format with this structure:

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
  2. Use open questions for extractive or descriptive information (e.g., "What are the main findings?")
  3. Make questions clear, specific, and professionally worded
  4. Generate keys in English snake_case (e.g., "sample_size", "has_control_group")
  5. Generate questions and column names in {language}
  6. Ensure the mode_key is descriptive and unique
  7. Limit to 3-6 yes/no questions and 2-4 open questions for usability

  Output ONLY the JSON, no explanations.

examples:
  - user_description: |
      "我想筛选关于消费者行为的实证研究。需要判断是否使用了问卷调查法，
      是否在中国情境下开展，并提取研究的主要发现和理论框架。"

    output: |
      {
        "mode_key": "consumer_behavior_empirical",
        "description": "消费者行为实证研究筛选",
        "yes_no_questions": [
          {
            "key": "is_empirical",
            "question": "这是否为实证研究？",
            "column_name": "实证研究"
          },
          {
            "key": "uses_survey",
            "question": "是否使用了问卷调查法？",
            "column_name": "问卷调查"
          },
          {
            "key": "chinese_context",
            "question": "是否在中国情境下开展？",
            "column_name": "中国情境"
          }
        ],
        "open_questions": [
          {
            "key": "main_findings",
            "question": "研究的主要发现是什么？",
            "column_name": "主要发现"
          },
          {
            "key": "theoretical_framework",
            "question": "使用了什么理论框架？",
            "column_name": "理论框架"
          }
        ]
      }
```

#### 3.4.2 矩阵维度生成提示词

文件：`litrx/prompts/matrix_dimension_generation.yaml`

```yaml
system_prompt: |
  You are an expert in systematic literature review and data extraction.
  Your task is to help researchers design literature matrix dimensions.

  Given a user's description of information they want to extract from papers,
  generate appropriate dimension configurations with correct question types.

user_prompt_template: |
  The user wants to extract the following information from literature:

  """
  {user_description}
  """

  Please generate dimension configurations in YAML format with this structure:

  dimensions:
    - type: <question_type>
      key: key_in_english
      question: "Question text in {language}"
      column_name: "Column name in {language}"
      # Type-specific fields below

  Available question types:
  1. text: Open-ended text extraction (e.g., "What are the main findings?")
  2. yes_no: Binary judgment (e.g., "Is this empirical research?")
  3. single_choice: Choose one from options (e.g., "Research paradigm: quantitative/qualitative/mixed")
  4. multiple_choice: Choose multiple from options (e.g., "Data collection methods used")
  5. number: Numerical extraction (e.g., "Sample size")
  6. rating: Subjective rating 1-N (e.g., "Research quality: 1-5")
  7. list: Extract list of items (e.g., "Key variables")

  Type-specific fields:
  - single_choice/multiple_choice: must have "options" (list of strings)
  - number: optional "unit" (e.g., "个", "%")
  - rating: must have "scale" (int), optional "scale_description"
  - list: must have "separator" (e.g., "; ")

  Guidelines:
  1. Choose the most appropriate question type for each piece of information
  2. For choice types, provide comprehensive but focused option lists
  3. Make questions clear and answerable from abstracts/full texts
  4. Generate keys in English snake_case
  5. Generate questions and column names in {language}
  6. Limit to 5-12 dimensions for usability
  7. Group related dimensions together

  Output ONLY the YAML, no explanations.

examples:
  - user_description: |
      "我需要提取每篇文献的研究方法（定量/定性/混合），样本量，
      是否在中国开展,使用的主要理论（可能有多个），以及我对
      研究质量的评分（1-5分）。"

    output: |
      dimensions:
        - type: single_choice
          key: research_paradigm
          question: "研究采用的研究范式是什么？"
          column_name: "研究范式"
          options:
            - "定量研究"
            - "定性研究"
            - "混合方法"
            - "其他"

        - type: number
          key: sample_size
          question: "研究的样本量是多少？如无法确定，回答N/A。"
          column_name: "样本量"
          unit: "个"

        - type: yes_no
          key: chinese_context
          question: "是否在中国情境下开展研究？"
          column_name: "中国情境"

        - type: list
          key: theoretical_frameworks
          question: "研究使用了哪些主要理论框架？请列出。"
          column_name: "理论框架"
          separator: "; "

        - type: rating
          key: research_quality
          question: "请评估本研究的整体质量"
          column_name: "研究质量"
          scale: 5
          scale_description: "1=很差, 2=较差, 3=一般, 4=良好, 5=优秀"
```

### 3.5 配置验证规则

#### 3.5.1 摘要模式配置验证

```python
def validate_abstract_mode_config(config: dict) -> None:
    """Validate abstract screening mode configuration.

    Raises:
        ValueError: If configuration is invalid
    """
    # 必需字段
    required_fields = ["mode_key", "description", "yes_no_questions", "open_questions"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    # mode_key 格式验证
    mode_key = config["mode_key"]
    if not mode_key.replace("_", "").isalnum():
        raise ValueError(f"Invalid mode_key format: {mode_key}")

    # 验证问题列表
    for question_list, list_name in [
        (config["yes_no_questions"], "yes_no_questions"),
        (config["open_questions"], "open_questions")
    ]:
        if not isinstance(question_list, list):
            raise ValueError(f"{list_name} must be a list")

        for idx, q in enumerate(question_list):
            # 每个问题的必需字段
            q_required = ["key", "question", "column_name"]
            for field in q_required:
                if field not in q:
                    raise ValueError(
                        f"{list_name}[{idx}] missing field: {field}"
                    )

            # key 格式验证
            if not q["key"].replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid question key format: {q['key']}"
                )

    # 检查问题数量合理性
    total_questions = len(config["yes_no_questions"]) + len(config["open_questions"])
    if total_questions == 0:
        raise ValueError("Configuration must have at least one question")
    if total_questions > 15:
        warnings.warn(f"Too many questions ({total_questions}), consider reducing")
```

#### 3.5.2 矩阵维度配置验证

```python
def validate_matrix_dimension(dimension: dict) -> None:
    """Validate a single matrix dimension configuration.

    Raises:
        ValueError: If dimension is invalid
    """
    # 必需字段
    required_fields = ["type", "key", "question", "column_name"]
    for field in required_fields:
        if field not in dimension:
            raise ValueError(f"Missing required field: {field}")

    # 类型验证
    valid_types = ["text", "yes_no", "single_choice", "multiple_choice",
                   "number", "rating", "list"]
    if dimension["type"] not in valid_types:
        raise ValueError(f"Invalid type: {dimension['type']}")

    # key 格式验证
    key = dimension["key"]
    if not key.replace("_", "").isalnum() or key[0].isdigit():
        raise ValueError(f"Invalid key format: {key}")

    # 类型特定验证
    dim_type = dimension["type"]

    if dim_type in ["single_choice", "multiple_choice"]:
        if "options" not in dimension:
            raise ValueError(f"{dim_type} requires 'options' field")
        if not isinstance(dimension["options"], list):
            raise ValueError("'options' must be a list")
        if len(dimension["options"]) < 2:
            raise ValueError("Choice type must have at least 2 options")

    if dim_type == "rating":
        if "scale" not in dimension:
            raise ValueError("Rating type requires 'scale' field")
        scale = dimension["scale"]
        if not isinstance(scale, int) or scale < 2 or scale > 10:
            raise ValueError(f"Invalid scale value: {scale} (must be 2-10)")

    if dim_type == "list":
        if "separator" not in dimension:
            raise ValueError("List type requires 'separator' field")
```

---

## 4. 实现计划

### 4.1 开发阶段

#### 阶段 1：核心逻辑实现（3-4天）
**任务**：
1. 创建 `litrx/ai_config_generator.py`
   - 实现 `AbstractModeGenerator` 类
   - 实现 `MatrixDimensionGenerator` 类
   - 添加配置验证函数

2. 创建提示词模板文件
   - `litrx/prompts/abstract_mode_generation.yaml`
   - `litrx/prompts/matrix_dimension_generation.yaml`

3. 单元测试
   - 测试 AI 响应解析
   - 测试配置验证
   - Mock AI 客户端进行测试

**交付物**：
- 可工作的生成器类
- 提示词模板
- 单元测试（覆盖率 > 80%）

#### 阶段 2：GUI 对话框实现（2-3天）
**任务**：
1. 创建 `litrx/gui/dialogs/ai_mode_assistant.py`
   - 实现 `AIModeAssistantDialog` 类
   - 设计用户界面
   - 集成 `AbstractModeGenerator`

2. 创建 `litrx/gui/dialogs/ai_dimension_assistant.py`
   - 实现 `AIDimensionAssistantDialog` 类
   - 设计用户界面（带表格预览和复选框）
   - 集成 `MatrixDimensionGenerator`

3. 添加国际化支持
   - 在 `litrx/i18n.py` 中添加新的翻译条目
   - 支持中英文

**交付物**：
- 功能完整的对话框组件
- 国际化翻译

#### 阶段 3：集成到现有标签页（1-2天）
**任务**：
1. 修改 `litrx/gui/tabs/abstract/abstract_tab.py`
   - 添加"AI 辅助创建"按钮
   - 集成 `AIModeAssistantDialog`
   - 处理生成结果（保存到 questions_config.json）

2. 修改 `litrx/gui/dialogs/dimension_editor.py`
   - 添加"AI 辅助创建"按钮
   - 集成 `AIDimensionAssistantDialog`
   - 处理生成结果（添加到维度列表）

**交付物**：
- 集成完成的 GUI
- 配置文件读写逻辑

#### 阶段 4：测试与优化（2-3天）
**任务**：
1. 端到端测试
   - 测试完整的用户流程
   - 测试各种边界情况

2. 提示词优化
   - 根据实际生成效果调整提示词
   - 确保生成质量稳定

3. 错误处理
   - 优化错误提示
   - 添加重试机制

4. 性能优化
   - 优化 AI 调用（避免超时）
   - 添加加载状态指示

**交付物**：
- 稳定可用的功能
- 优化的提示词模板
- 错误处理机制

#### 阶段 5：文档与发布（1天）
**任务**：
1. 更新文档
   - 更新 `README.md` 和 `Chinese_README.md`
   - 更新 `CLAUDE.md`
   - 创建用户指南（如何使用 AI 助手）

2. 创建示例
   - 提供典型用例示例
   - 录制演示视频（可选）

**交付物**：
- 完整文档
- 用户指南

### 4.2 开发优先级

**必需功能（MVP）**：
1. ✅ 核心生成器类
2. ✅ 提示词模板
3. ✅ 基础 GUI 对话框
4. ✅ 集成到现有标签页

**增强功能（v1.1）**：
1. 历史记录功能（保存用户之前的描述和生成结果）
2. 配置模板库（预设常见领域的配置）
3. 批量生成（一次描述生成多个相关配置）
4. 智能建议（基于已有配置推荐相关问题）

**未来功能（v2.0）**：
1. 对话式配置（多轮对话精细化配置）
2. 配置分析（分析现有配置并提供优化建议）
3. 跨模式学习（基于历史使用学习用户偏好）

### 4.3 技术风险与应对

#### 风险 1：AI 生成质量不稳定
**影响**：生成的配置可能不符合用户需求

**应对**：
- 使用较低的 temperature (0.3) 提高稳定性
- 提供详细的提示词示例
- 允许用户重新生成
- 提供手动编辑功能作为补充

#### 风险 2：AI API 调用失败
**影响**：功能不可用

**应对**：
- 添加重试机制（最多3次）
- 提供清晰的错误提示
- 降级方案：回退到手动编辑模式
- 添加网络超时处理

#### 风险 3：生成的配置格式不正确
**影响**：无法保存或使用配置

**应对**：
- 严格的配置验证
- 提供格式修复建议
- 允许用户手动修正
- 记录失败案例用于改进提示词

#### 风险 4：用户描述不清晰
**影响**：AI 无法理解需求

**应对**：
- 提供详细的引导文本和示例
- 允许用户迭代（重新描述）
- 提供对话式澄清（未来功能）

### 4.4 性能指标

#### 响应时间
- AI 调用响应时间：< 10秒（取决于 AI 服务）
- 配置解析和验证：< 1秒
- 总体用户等待时间：< 15秒

#### 质量指标
- 配置验证通过率：> 95%
- 用户满意度（需要的问题覆盖率）：> 80%
- 一次生成成功率（无需重新生成）：> 70%

---

## 5. 用户体验设计

### 5.1 界面设计草图

#### 5.1.1 摘要模式 AI 助手对话框

```
┌─────────────────────────────────────────────────────┐
│  AI 辅助创建筛选模式                          ✕      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📝 请描述您的文献筛选需求：                        │
│                                                     │
│  您可以包括：                                       │
│  • 研究领域或主题                                   │
│  • 需要判断的特征（是非问题）                       │
│  • 需要提取的信息（开放问题）                       │
│                                                     │
│  示例："我想筛选关于消费者行为的实证研究..."       │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │  [用户输入区域 - 多行文本框]                 │   │
│  │                                             │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│                      [生成配置]                     │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  📋 生成的配置预览：                                │
│                                                     │
│  模式名称：consumer_behavior_screening              │
│  描述：消费者行为研究筛选                           │
│                                                     │
│  是非判断问题 (3)：                                 │
│    ✓ 是否为实证研究？                               │
│    ✓ 是否使用问卷调查法？                           │
│    ✓ 是否在中国情境下开展？                         │
│                                                     │
│  开放问题 (2)：                                     │
│    • 主要研究发现是什么？                           │
│    • 使用了什么理论框架？                           │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│             [重新生成]  [应用]  [取消]              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

#### 5.1.2 矩阵维度 AI 助手对话框

```
┌─────────────────────────────────────────────────────────────────┐
│  AI 辅助创建分析维度                                      ✕      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📝 请描述您需要从文献中提取的信息：                            │
│                                                                 │
│  您可以包括：                                                   │
│  • 研究特征（研究类型、方法等）                                 │
│  • 数值信息（样本量、效应量等）                                 │
│  • 分类信息（领域、理论等）                                     │
│  • 评估需求（质量评分、相关性等）                               │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  [用户输入区域 - 多行文本框]                           │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│                          [生成维度]                             │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  📋 生成的维度配置（请选择需要的维度）：                        │
│                                                                 │
│  [✓] 全选                                                       │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ ☑ │ 类型       │ 问题                 │ 列名     │ 详情   │ │
│  ├───┼───────────┼─────────────────────┼─────────┼────────┤ │
│  │ ☑ │ 单选题     │ 研究范式是什么？     │ 研究范式 │ 3选项  │ │
│  │ ☑ │ 数值提取   │ 样本量是多少？       │ 样本量   │ 单位:个│ │
│  │ ☑ │ 是/否     │ 是否在中国开展？     │ 中国情境 │ -      │ │
│  │ ☑ │ 列表提取   │ 使用的主要理论？     │ 理论框架 │ 分隔;  │ │
│  │ ☑ │ 评分       │ 评估研究质量         │ 研究质量 │ 1-5分  │ │
│  │ ☐ │ 多选题     │ 数据收集方法？       │ 收集方法 │ 5选项  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  已选择 5/6 个维度                                              │
│                                                                 │
│             [重新生成]  [应用选中]  [取消]                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 交互流程优化

#### 优化 1：渐进式披露
- 初始界面只显示输入框和引导文本
- 生成后才显示预览区域
- 减少初始认知负荷

#### 优化 2：即时反馈
- 生成过程中显示加载动画
- 显示"AI 正在分析您的需求..."等提示
- 生成完成后高亮预览区域

#### 优化 3：错误处理友好
- AI 调用失败时提供清晰的错误提示
- 提供重试按钮
- 建议降级到手动编辑模式

#### 优化 4：灵活性
- 允许用户修改生成的配置
- 提供"基于此重新生成"功能
- 支持部分应用（矩阵维度）

---

## 6. 测试计划

### 6.1 单元测试

#### 测试用例 1：AbstractModeGenerator
```python
def test_generate_mode_basic():
    """测试基本的模式生成功能"""
    generator = AbstractModeGenerator(config)

    description = "我需要筛选实证研究，判断是否使用问卷法"
    result = generator.generate_mode(description, language="zh")

    assert "mode_key" in result
    assert "yes_no_questions" in result
    assert len(result["yes_no_questions"]) > 0


def test_generate_mode_validation():
    """测试生成配置的验证"""
    generator = AbstractModeGenerator(config)

    # Mock invalid AI response
    with pytest.raises(ValueError):
        generator._validate_config({"invalid": "config"})


def test_parse_response_json():
    """测试 JSON 响应解析"""
    generator = AbstractModeGenerator(config)

    json_str = '{"mode_key": "test", ...}'
    result = generator._parse_response(json_str)

    assert isinstance(result, dict)
    assert result["mode_key"] == "test"
```

#### 测试用例 2：MatrixDimensionGenerator
```python
def test_generate_dimensions_basic():
    """测试基本的维度生成功能"""
    generator = MatrixDimensionGenerator(config)

    description = "提取研究方法和样本量"
    result = generator.generate_dimensions(description, language="zh")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all("type" in dim for dim in result)


def test_validate_dimension_types():
    """测试各种维度类型的验证"""
    generator = MatrixDimensionGenerator(config)

    # Valid single_choice
    dim = {
        "type": "single_choice",
        "key": "test",
        "question": "Test?",
        "column_name": "Test",
        "options": ["A", "B"]
    }
    generator._validate_dimension(dim)  # Should not raise

    # Invalid: missing options
    dim_invalid = {
        "type": "single_choice",
        "key": "test",
        "question": "Test?",
        "column_name": "Test"
    }
    with pytest.raises(ValueError):
        generator._validate_dimension(dim_invalid)
```

### 6.2 集成测试

#### 测试场景 1：端到端模式创建
```python
def test_end_to_end_mode_creation(mock_ai_client):
    """测试完整的模式创建流程"""
    # 1. 用户输入描述
    description = "筛选心理学实证研究"

    # 2. 调用生成器
    generator = AbstractModeGenerator(config_with_mock_client)
    result = generator.generate_mode(description)

    # 3. 验证结果
    assert result is not None
    validate_abstract_mode_config(result)

    # 4. 保存到配置文件
    save_to_questions_config(result)

    # 5. 验证可以加载
    loaded = load_mode_questions(result["mode_key"])
    assert loaded == result
```

#### 测试场景 2：端到端维度创建
```python
def test_end_to_end_dimension_creation(mock_ai_client):
    """测试完整的维度创建流程"""
    # 1. 用户输入描述
    description = "提取研究方法、样本量、研究质量评分"

    # 2. 调用生成器
    generator = MatrixDimensionGenerator(config_with_mock_client)
    dimensions = generator.generate_dimensions(description)

    # 3. 验证结果
    assert len(dimensions) >= 3
    for dim in dimensions:
        validate_matrix_dimension(dim)

    # 4. 添加到配置
    config = load_matrix_config()
    config["dimensions"].extend(dimensions)
    save_matrix_config(config)
```

### 6.3 用户验收测试

#### 测试场景 1：新手用户创建模式
**目标**：验证非技术用户能否成功使用

**步骤**：
1. 打开摘要筛选标签页
2. 点击"AI 辅助创建模式"
3. 根据引导输入需求描述
4. 点击"生成配置"
5. 查看预览
6. 点击"应用"
7. 验证模式出现在下拉列表

**成功标准**：
- 用户能在 5 分钟内完成操作
- 生成的配置符合用户需求
- 无需技术知识

#### 测试场景 2：高级用户创建复杂维度
**目标**：验证功能能否处理复杂需求

**步骤**：
1. 打开文献矩阵标签页
2. 点击"编辑维度" → "AI 辅助创建"
3. 输入包含多种信息类型的复杂描述
4. 生成并预览
5. 选择部分维度应用
6. 手动编辑某些维度
7. 保存配置

**成功标准**：
- AI 能正确识别多种信息类型
- 生成的维度类型准确
- 用户能灵活选择和编辑

---

## 7. 后续优化方向

### 7.1 短期优化（1-2个月）

1. **配置模板库**
   - 预设常见领域的配置（心理学、教育学、医学等）
   - 用户可以基于模板修改

2. **历史记录**
   - 保存用户之前的描述和生成结果
   - 支持重新使用或修改

3. **智能推荐**
   - 基于当前配置推荐相关问题
   - 检测遗漏的常见维度

### 7.2 中期优化（3-6个月）

1. **对话式配置**
   - 多轮对话精细化需求
   - AI 主动询问澄清问题

2. **配置分析**
   - 分析现有配置的合理性
   - 提供优化建议

3. **批量生成**
   - 一次描述生成多个相关配置
   - 支持配置变体

### 7.3 长期优化（6-12个月）

1. **跨模式学习**
   - 基于历史使用学习用户偏好
   - 个性化推荐

2. **协作共享**
   - 用户可以分享配置模板
   - 社区配置库

3. **自动优化**
   - 基于使用反馈自动优化提示词
   - A/B 测试不同生成策略

---

## 8. 成功指标

### 8.1 功能指标

- ✅ 配置生成成功率 > 95%
- ✅ 配置验证通过率 > 95%
- ✅ AI 响应时间 < 15秒
- ✅ 用户操作步骤 < 5 步

### 8.2 用户指标

- 🎯 新用户使用率 > 60%
- 🎯 生成配置直接使用率 > 50%
- 🎯 用户满意度 > 4/5
- 🎯 功能推荐率 > 80%

### 8.3 质量指标

- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖率 > 70%
- ✅ 关键路径测试覆盖率 100%
- ✅ Bug 修复时间 < 48 小时

---

## 9. 附录

### 9.1 术语表

- **摘要筛选模式（Abstract Screening Mode）**：一组用于筛选文献的问题配置
- **文献矩阵维度（Literature Matrix Dimension）**：文献矩阵分析中的单个提取维度
- **Yes/No 问题**：需要AI判断是或否的问题
- **开放问题（Open Question）**：需要AI提取描述性信息的问题
- **问题类型（Question Type）**：7种矩阵维度类型之一

### 9.2 相关文件清单

**现有文件**：
- `litrx/abstract_screener.py` - 摘要筛选核心逻辑
- `litrx/matrix_analyzer.py` - 矩阵分析核心逻辑
- `litrx/ai_client.py` - AI 客户端
- `questions_config.json` - 摘要模式配置
- `configs/matrix/default.yaml` - 矩阵维度配置

**新增文件**：
- `litrx/ai_config_generator.py` - AI 配置生成器
- `litrx/gui/dialogs/ai_mode_assistant.py` - 模式AI助手对话框
- `litrx/gui/dialogs/ai_dimension_assistant.py` - 维度AI助手对话框
- `litrx/prompts/abstract_mode_generation.yaml` - 模式生成提示词
- `litrx/prompts/matrix_dimension_generation.yaml` - 维度生成提示词

### 9.3 参考资料

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [YAML Specification](https://yaml.org/spec/)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [LitRelevanceAI ARCHITECTURE.md](../ARCHITECTURE.md)

---

**文档维护**：
本文档将在开发过程中持续更新。如有疑问或建议，请在 GitHub Issues 中讨论。
