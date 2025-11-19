# CLAUDE.md - AI Assistant Guide for LitRelevanceAI

This document provides comprehensive guidance for AI assistants (like Claude Code) working with the LitRelevanceAI codebase. It covers architecture, conventions, workflows, and important context to help you work effectively on this project.

## Project Overview

**LitRelevanceAI** (`litrx` package) is an AI-assisted literature review toolkit for academic researchers. It helps screen and analyze academic papers using large language models (OpenAI GPT and SiliconFlow).

### Core Functionality
- **CSV Relevance Analysis**: Score Scopus exports (0-100) with AI-generated relevance explanations
- **Abstract Screening**: Configurable yes/no criteria and open questions with optional verification workflow
- **Literature Matrix Analysis**: Structured data extraction with 7 question types (text, yes_no, single_choice, multiple_choice, number, rating, list)
- **AI-Assisted Configuration Generation** (NEW): Natural language-based automatic generation of screening modes and matrix dimensions using AI
- **PDF Screening**: Legacy full-text analysis (superseded by matrix analyzer)
- **Bilingual GUI**: Tkinter interface with Chinese/English support

### Technology Stack
- **Language**: Python 3.8+
- **AI Provider**: OpenAI SDK (supports OpenAI and SiliconFlow APIs)
- **GUI**: Tkinter (standard library)
- **Data**: pandas, openpyxl
- **PDF**: pypdf
- **Config**: YAML, JSON, .env files
- **Testing**: pytest (minimal coverage currently)

## Repository Structure

```
LitRelevanceAI/
├── litrx/                          # Main package (~5000 LOC)
│   ├── __init__.py                 # Package initialization
│   ├── __main__.py                 # Entry point: python -m litrx
│   ├── cli.py                      # CLI dispatcher (csv/abstract/matrix commands)
│   ├── config.py                   # Cascading configuration management
│   ├── ai_client.py                # OpenAI SDK wrapper for AI providers
│   ├── ai_config_generator.py      # AI-assisted config generation (NEW)
│   ├── i18n.py                     # Internationalization (Observer pattern)
│   ├── csv_analyzer.py             # CSV relevance scoring (LiteratureAnalyzer)
│   ├── abstract_screener.py        # Title/abstract screening with verification
│   ├── pdf_screener.py             # PDF analysis (LEGACY - use matrix_analyzer)
│   ├── matrix_analyzer.py          # Literature matrix analysis
│   ├── prompts/                    # AI prompt templates (NEW)
│   │   ├── abstract_mode_generation.txt
│   │   └── matrix_dimension_generation.txt
│   └── gui/                        # Tkinter GUI components
│       ├── base_window.py          # BaseWindow class with shared controls
│       ├── main_window.py          # LitRxApp - main application window
│       ├── tabs/                   # Feature tabs
│       │   ├── csv_tab.py          # CSV analysis tab
│       │   ├── abstract/           # Abstract screening components
│       │   │   ├── abstract_tab.py # Abstract screening tab
│       │   │   ├── question_editor.py
│       │   │   └── statistics_viewer.py
│       │   ├── matrix_tab.py       # Literature matrix tab
│       │   └── pdf_tab.py          # PDF screening tab (LEGACY)
│       └── dialogs/
│           ├── dimension_editor.py # Matrix dimension configuration
│           ├── ai_mode_assistant.py # AI mode generation dialog (NEW)
│           └── ai_dimension_assistant.py # AI dimension generation dialog (NEW)
├── configs/                        # Configuration files
│   ├── config.yaml                 # Default AI service settings
│   ├── questions/                  # Question templates per module
│   │   ├── csv.yaml
│   │   ├── abstract.yaml
│   │   └── pdf.yaml
│   └── matrix/
│       └── default.yaml            # Matrix dimensions config
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # Detailed architecture
│   ├── AI_ASSISTED_CONFIG_DESIGN.md # AI config feature design (NEW)
│   ├── AI_ASSISTED_CONFIG_IMPLEMENTATION_PLAN.md # Implementation plan (NEW)
│   └── 项目功能与架构概览.md        # Chinese overview
├── tests/                          # Unit tests
│   ├── test_abstract_verification.py
│   └── test_ai_config_generator.py # AI config generator tests (NEW)
├── run_gui.py                      # GUI launcher with auto-install
├── questions_config.json           # Abstract screening modes
├── prompts_config.json             # AI prompt templates (GUI-editable)
├── pyproject.toml                  # PEP 621 packaging
├── setup.cfg                       # Legacy packaging
├── .env.example                    # API key template
├── README.md                       # English documentation
├── Chinese_README.md               # Chinese documentation
├── AGENTS.md                       # Developer guide
└── CLAUDE.md                       # This file

```

## Quick Start for Development

### Setup
```bash
# 1. Install in editable mode
python -m pip install -e .

# 2. Configure API keys
cp .env.example .env
# Edit .env and add OPENAI_API_KEY or SILICONFLOW_API_KEY

# 3. Verify installation
python -m litrx --help
litrx --help  # Should work if installed correctly

# 4. Launch GUI
python run_gui.py  # Auto-installs dependencies
```

### Running Tests
```bash
pytest tests/  # Currently minimal test coverage
```

## Architecture Patterns

### 1. Observer Pattern (i18n System)

**Location**: `litrx/i18n.py`

The internationalization system uses the observer pattern for dynamic UI updates:

```python
from litrx.i18n import get_i18n, t

# Get translation
title = t("app_title")  # Returns text in current language

# Change language and notify all observers
i18n = get_i18n()
i18n.current_language = "en"  # Triggers all registered callbacks

# Register observer (in GUI components)
def on_language_change():
    self.title_label.config(text=t("title"))

i18n.add_observer(on_language_change)
```

**Key Points**:
- Global singleton via `get_i18n()`
- Translations in nested dict: `TRANSLATIONS["zh"]["key"]` and `TRANSLATIONS["en"]["key"]`
- Language preference persisted to config
- All GUI components should register observers in `__init__`

### 2. Template Method Pattern (BaseWindow)

**Location**: `litrx/gui/base_window.py`

Base class for GUI windows with overridable hooks:

```python
class MyWindow(BaseWindow):
    def _on_language_changed(self):
        # Called when language changes
        super()._on_language_changed()
        self.update_my_widgets()

    def build_config(self):
        # Build runtime configuration
        config = super().build_config()
        config["my_setting"] = self.my_value
        return config
```

**Shared Functionality**:
- Configuration controls (AI service, API key, model)
- Language selector dropdown
- Prompt settings editor
- Config persistence to `~/.litrx_gui.yaml`
- Tab container (Notebook)

### 3. Dependency Injection (GUI Tabs)

**Location**: `litrx/gui/tabs/*.py`

Tabs receive parent BaseWindow and access shared resources:

```python
class MyTab(ttk.Frame):
    def __init__(self, parent: BaseWindow):
        super().__init__(parent.notebook)
        self.parent = parent

        # Access shared configuration
        config = parent.build_config()

        # Use shared AI client
        client = AIClient(config["AI_SERVICE"], config)
```

### 4. Cascading Configuration

**Location**: `litrx/config.py`

Configuration priority (low to high):
1. `DEFAULT_CONFIG` (hardcoded defaults)
2. `configs/config.yaml` (project defaults)
3. `~/.litrx_gui.yaml` (user preferences)
4. `.env` file (environment variables)
5. CLI arguments (runtime overrides)

**Key Functions**:
- `load_env_file(path)`: Parse .env files
- `load_config(path, defaults)`: Merge YAML/JSON with defaults
- Configuration keys: `AI_SERVICE`, `MODEL_NAME`, `{OPENAI|SILICONFLOW}_API_KEY`, `API_BASE`, `LANGUAGE`, `ENABLE_VERIFICATION`

## AI-Assisted Configuration Generation (NEW Feature)

### Overview

The AI-assisted configuration generation feature allows users to create screening modes and matrix dimensions using natural language descriptions instead of manually writing JSON/YAML configurations. This significantly lowers the barrier to entry for non-technical users.

### Key Components

#### 1. `ai_config_generator.py` - Core Module

**Classes**:
- `AbstractModeGenerator`: Generates abstract screening modes from natural language
- `MatrixDimensionGenerator`: Generates matrix dimensions from natural language

**Usage Example**:
```python
from litrx.ai_config_generator import AbstractModeGenerator

config = {"AI_SERVICE": "openai", "OPENAI_API_KEY": "sk-..."}
generator = AbstractModeGenerator(config)

# User describes their needs in natural language
description = "我需要筛选实证研究，判断是否使用问卷法，并提取样本量"

# AI generates the configuration
mode_config = generator.generate_mode(description, language="zh")

# Result:
# {
#   "mode_key": "empirical_survey_screening",
#   "description": "实证研究问卷调查筛选",
#   "yes_no_questions": [...],
#   "open_questions": [...]
# }
```

#### 2. Prompt Templates

**Location**: `litrx/prompts/`

- `abstract_mode_generation.txt`: Template for generating abstract screening modes
- `matrix_dimension_generation.txt`: Template for generating matrix dimensions

**Customization**: Users can customize these templates by editing the `.txt` files. If the files don't exist, the system falls back to embedded default templates.

#### 3. GUI Dialogs

**AI Mode Assistant** (`litrx/gui/dialogs/ai_mode_assistant.py`):
- Natural language input for describing screening needs
- Real-time AI generation with progress indicator
- Preview of generated configuration
- Ability to regenerate if unsatisfied
- Direct integration with `questions_config.json`

**AI Dimension Assistant** (`litrx/gui/dialogs/ai_dimension_assistant.py`):
- Natural language input for describing extraction needs
- Multi-dimension generation in one request
- Table view with checkboxes for selective application
- Supports all 7 dimension types (text, yes_no, single_choice, multiple_choice, number, rating, list)

### User Workflow

#### Creating a Screening Mode with AI

1. User clicks "🤖 AI 辅助创建" button in Abstract Screening tab
2. Dialog opens with guidance text and examples
3. User enters natural language description (e.g., "筛选心理学实证研究，需要判断是否使用实验方法...")
4. User clicks "生成配置"
5. AI processes the description (typically 5-10 seconds)
6. Preview shows generated questions categorized as yes/no and open questions
7. User can regenerate or apply the configuration
8. Configuration is saved to `questions_config.json` and immediately available

#### Creating Matrix Dimensions with AI

1. User opens "编辑维度" dialog in Matrix tab
2. Clicks "🤖 AI 辅助创建"
3. Enters description of information to extract
4. AI generates multiple dimensions with appropriate types
5. User reviews in table format and selects desired dimensions
6. Selected dimensions are added to the configuration
7. User can continue manual editing if needed

### Implementation Details

#### AI Response Parsing

**Challenge**: AI responses may include markdown code blocks, explanations, or formatting.

**Solution**: Robust parsing that handles multiple formats:
```python
def _parse_json_response(self, response: str) -> Dict:
    # Try to extract from ```json code block
    if "```json" in response:
        json_part = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        json_part = response.split("```")[1].split("```")[0]
    else:
        json_part = response

    return json.loads(json_part.strip())
```

#### Configuration Validation

**Abstract Modes**:
- Required fields: `mode_key`, `description`, `yes_no_questions`, `open_questions`
- `mode_key` must be valid snake_case identifier
- Each question must have `key`, `question`, `column_name`
- Warns if total questions > 15 (usability concern)

**Matrix Dimensions**:
- Required fields: `type`, `key`, `question`, `column_name`
- Type must be one of 7 supported types
- Type-specific validation:
  - `single_choice`/`multiple_choice`: Must have `options` (list, ≥2 items)
  - `rating`: Must have `scale` (integer, 2-10)
  - `list`: Must have `separator`
  - `number`: Optional `unit`

#### Error Handling

- **Invalid AI Response**: User-friendly error message with suggestion to try again
- **Network Failure**: Clear indication of network issues
- **Validation Errors**: Specific messages about what's wrong with the configuration
- **Fallback**: Users can always use manual editing if AI generation fails

### Testing

**Unit Tests**: `tests/test_ai_config_generator.py`

**Key Test Cases**:
- Basic generation with mocked AI responses
- Markdown code block parsing
- Validation of various error conditions
- All dimension types and their specific requirements
- Template file loading vs. default template fallback

**Running Tests**:
```bash
pytest tests/test_ai_config_generator.py -v
```

### Best Practices for AI Assistants

When working on or extending this feature:

1. **Always Mock AIClient in Tests**: Never make real API calls in tests
   ```python
   @pytest.fixture
   def mock_ai_client(mocker):
       mock = mocker.MagicMock()
       mocker.patch("litrx.ai_config_generator.AIClient", return_value=mock)
       return mock
   ```

2. **Preserve Prompt Template Format**: When modifying templates:
   - Keep `{user_description}` and `{language}` placeholders
   - Maintain clear examples in both Chinese and English
   - Test with actual AI to verify output quality

3. **Handle Edge Cases**: Consider:
   - Empty user input
   - Very long descriptions
   - Non-English/non-Chinese input
   - Ambiguous requirements

4. **Maintain Backward Compatibility**: Generated configurations must work with existing `abstract_screener.py` and `matrix_analyzer.py`

5. **Internationalization**: All UI text must use `t()` function:
   ```python
   self.label.config(text=t("ai_mode_assistant_title"))
   ```

### Future Enhancements

Potential improvements (not yet implemented):

- **Multi-turn Dialogue**: AI asks clarifying questions if description is ambiguous
- **Configuration Templates**: Pre-built templates for common research fields
- **History Tracking**: Save and reuse previous successful generations
- **Batch Generation**: Generate multiple related configurations at once
- **Smart Suggestions**: Recommend additional questions based on existing ones

## Common Development Workflows

### Adding a New GUI Tab

1. **Create tab class** in `litrx/gui/tabs/my_tab.py`:
```python
import tkinter as tk
from tkinter import ttk
from litrx.gui.base_window import BaseWindow
from litrx.i18n import t, get_i18n

class MyTab(ttk.Frame):
    def __init__(self, parent: BaseWindow):
        super().__init__(parent.notebook)
        self.parent = parent

        # Build UI
        self.build_ui()

        # Register language observer
        get_i18n().add_observer(self.update_language)

    def build_ui(self):
        # Create widgets using t() for translations
        self.title_label = ttk.Label(self, text=t("my_tab_title"))
        self.title_label.pack()

    def update_language(self):
        # Update all translatable widgets
        self.title_label.config(text=t("my_tab_title"))
```

2. **Add translations** to `litrx/i18n.py`:
```python
TRANSLATIONS = {
    "zh": {
        "my_tab_title": "我的标签",
        "my_tab": "我的功能",
    },
    "en": {
        "my_tab_title": "My Tab",
        "my_tab": "My Feature",
    }
}
```

3. **Register tab** in `litrx/gui/main_window.py`:
```python
from litrx.gui.tabs.my_tab import MyTab

class LitRxApp(BaseWindow):
    def __init__(self, root):
        super().__init__(root)

        # Add tab
        my_tab = MyTab(self)
        self.notebook.add(my_tab, text=t("my_tab"))
        self.tabs.append(("my_tab", my_tab))
```

### Adding a New Analysis Module

1. **Create module** in `litrx/my_analyzer.py`:
```python
import pandas as pd
from litrx.ai_client import AIClient

class MyAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.client = AIClient(config["AI_SERVICE"], config)

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        # Your analysis logic
        results = []
        for idx, row in data.iterrows():
            response = self.client.request(
                prompt=f"Analyze: {row['text']}",
                temperature=0.3
            )
            results.append(response)

        data["analysis"] = results
        return data
```

2. **Add CLI command** in `litrx/cli.py`:
```python
def my_command():
    # Load data
    df = pd.read_csv("input.csv")

    # Analyze
    analyzer = MyAnalyzer(DEFAULT_CONFIG)
    results = analyzer.analyze(df)

    # Save
    results.to_csv("output.csv")

def main():
    if sys.argv[1] == "my-command":
        my_command()
```

3. **Add prompt templates** to `prompts_config.json`:
```json
{
  "my_analysis": {
    "main_prompt": "Your prompt template here with {placeholders}"
  }
}
```

### Adding Configuration Options

1. **Update defaults** in `litrx/config.py`:
```python
DEFAULT_CONFIG = {
    "MY_NEW_SETTING": "default_value",
}
```

2. **Save in GUI** (`litrx/gui/base_window.py`):
```python
def save_config(self):
    config = {
        "MY_NEW_SETTING": self.my_setting_var.get(),
    }
    # Save to ~/.litrx_gui.yaml
```

3. **Load from .env** (add to `.env.example`):
```
MY_NEW_SETTING=value
```

## Important Code Conventions

### Style Guidelines (PEP 8)
- **Indentation**: 4 spaces (never tabs)
- **Naming**:
  - `snake_case` for functions, variables, modules
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Import ordering**:
  1. Standard library
  2. Third-party packages
  3. Local modules
- **Line length**: Prefer < 100 characters
- **Type hints**: Use throughout (Python 3.8+ style)

### Error Messages
- User-facing errors often in Chinese
- Include helpful context: "Failed to load {file_path}: {error}"
- Use try/except with informative messages

### Docstrings
- Module-level docstrings for all modules
- Function-level for non-trivial functions
- Google/NumPy style preferred

### Common Utilities
- `t(key)`: Get translation
- `get_i18n()`: Access i18n singleton
- `load_config(path, defaults)`: Load configuration
- `AIClient(service, config)`: Create AI client
- `client.request(prompt, temperature)`: Make AI request

## Critical Implementation Details

### Verification Workflow (Abstract Screening)

The abstract screener has a **two-stage AI verification** system:

1. **Initial Analysis**: AI answers questions based on title/abstract
2. **Verification Pass**: AI checks if its answers are supported by source text

**Controlled by**:
- `ENABLE_VERIFICATION` config flag (True/False)
- GUI checkbox "Enable verification"

**Output columns**:
- `<question>`: Initial answer
- `<question>_verified`: Verification result
  - "是" (supported)
  - "否" (unsupported)
  - "不确定" (uncertain)
  - "验证失败" (verification failed)
  - "未验证" (verification disabled)

**Implementation**: `litrx/abstract_screener.py:252-293`

**GUI markers**: `✔` (supported) / `✖` (unsupported) in log output

### Configuration Cascade Quirks

**API Key Switching**: When switching AI service in GUI:
1. Current API key is saved to config
2. New service's previously saved key is loaded
3. Each provider's key persisted independently

**Implementation**: `litrx/gui/base_window.py:148-165`

**Language Persistence**: Language preference saved to `~/.litrx_gui.yaml` and restored on startup

### Metadata Matching (Matrix Analyzer)

**Zotero filename parsing**: Extracts `Author_Year_Title.pdf` pattern
```python
# Example: "Smith_2023_Machine Learning Review.pdf"
# Extracts: author="Smith", year="2023", title="Machine Learning Review"
```

**Fuzzy matching**: Uses rapidfuzz with 80% similarity threshold

**Priority**: DOI > Title > Zotero Key

**Implementation**: `litrx/matrix_analyzer.py`

### Threading Model (GUI)

Long-running tasks use daemon threads:
```python
def process_files(self):
    # Disable UI controls
    self.start_button.config(state="disabled")

    # Run in background thread
    thread = threading.Thread(target=self._process_thread, daemon=True)
    thread.start()

def _process_thread(self):
    # Do work
    results = self.analyzer.analyze(data)

    # Update UI thread-safely
    self.root.after(0, self._update_ui, results)
```

**Critical**: Use `root.after()` for thread-safe UI updates, never update widgets directly from worker threads.

### Prompt Template System

**Location**: `prompts_config.json`

Templates use Python `.format()` placeholders:
```json
{
  "csv_analysis": {
    "main_prompt": "Research topic: {research_topic}\nTitle: {title}\nAbstract: {abstract}"
  }
}
```

**Usage**:
```python
prompt = prompts_config["csv_analysis"]["main_prompt"].format(
    research_topic="machine learning",
    title="A Survey of ML",
    abstract="This paper..."
)
```

**GUI Editing**: Via "Prompt Settings" dialog in base window

## File I/O Patterns

### Column Detection (Flexible)

When reading CSV/Excel, try multiple column name variants:
```python
# Example from csv_analyzer.py
title_col = next(
    (col for col in df.columns if col in ["Title", "文献标题", "Article Title"]),
    None
)
```

**Always check**: Column existence before accessing

### Encoding Handling

```python
# UTF-8 with BOM support (common in Chinese exports)
df = pd.read_csv(file_path, encoding="utf-8-sig")
```

### Progress Preservation

Save interim results to prevent data loss:
```python
# Interim CSV
interim_path = file_path.replace(".csv", "_interim.csv")
df.to_csv(interim_path, index=False)

# Progress checkpoint (JSON)
progress = {"completed_indices": [0, 1, 2], "timestamp": "..."}
with open(progress_path, "w") as f:
    json.dump(progress, f)
```

**Load on restart** to resume from checkpoint.

### Timestamp Naming

Prevent overwriting previous results:
```python
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = f"{base_name}_analyzed_{timestamp}.csv"
```

## Testing Guidelines

### Current State
- **Framework**: pytest
- **Coverage**: Minimal (~5% of codebase)
- **Existing test**: `tests/test_abstract_verification.py`

### Adding Tests

1. **Create test file**: `tests/test_my_feature.py`
```python
import pytest
from litrx.my_module import MyClass

def test_my_function():
    # Arrange
    instance = MyClass()

    # Act
    result = instance.my_method("input")

    # Assert
    assert result == "expected"

@pytest.fixture
def mock_ai_client(mocker):
    """Mock AI client to avoid actual API calls"""
    mock = mocker.MagicMock()
    mock.request.return_value = "mocked response"
    return mock

def test_with_mock(mock_ai_client):
    instance = MyClass(client=mock_ai_client)
    result = instance.process()
    assert mock_ai_client.request.called
```

2. **Run tests**:
```bash
pytest tests/                    # All tests
pytest tests/test_my_feature.py  # Specific file
pytest -v                        # Verbose output
pytest --cov=litrx               # Coverage report
```

### Testing Best Practices

- **Mock AI clients**: Use `mocker` fixture to avoid API calls
- **Use fixtures**: For reusable test data
- **Test edge cases**: Empty inputs, missing columns, API errors
- **Verify side effects**: File creation, DataFrame modifications
- **Keep tests fast**: Mock external dependencies

## Git Workflow & Commits

### Branch Strategy
- **Main branch**: `main` (or default)
- **Feature branches**: `claude/<descriptive-name>-<session-id>`
  - Example: `claude/fix-verification-bug-mi385rmp3io6q2vl-01Xnih4WXoHLMKTyRcHcwkYY`
- **ALWAYS develop on the designated branch** (provided in task context)

### Commit Conventions

**Prefix format**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code restructuring without behavior change
- `test:` Adding or updating tests
- `chore:` Build process or auxiliary tool changes

**Examples**:
```bash
git commit -m "feat: add literature matrix analysis module"
git commit -m "fix: correct argument order in LiteratureAnalyzer instantiation"
git commit -m "docs: update CLAUDE.md with testing guidelines"
```

**Commit message format** (use HEREDOC):
```bash
git commit -m "$(cat <<'EOF'
feat: add verification workflow to abstract screener

- Implement two-stage AI verification process
- Add ENABLE_VERIFICATION config flag
- Create verified columns in output DataFrame
- Add GUI checkbox for enabling/disabling verification
EOF
)"
```

### Pre-commit Checklist

Before committing:
1. **Run tests**: `pytest tests/`
2. **Verify CLI**: `python -m litrx --help`
3. **Check imports**: No unused imports
4. **Update docs**: README if user-facing changes
5. **No secrets**: Never commit API keys or `.env` files

### Push Workflow

**CRITICAL**: Always use the branch specified in task context

```bash
# 1. Commit changes
git add .
git commit -m "..."

# 2. Push to designated branch
git push -u origin claude/<branch-name>

# 3. If network error, retry with exponential backoff
# (2s, 4s, 8s, 16s delays between retries, max 4 retries)
```

**Never**:
- Push to `main` directly
- Force push without explicit permission
- Skip pre-commit hooks
- Amend commits from other developers

## Common Pitfalls & Solutions

### Issue: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'litrx'`

**Solution**: Install in editable mode
```bash
python -m pip install -e .
```

### Issue: Missing Dependencies

**Problem**: `ImportError: No module named 'pandas'`

**Solution 1** (GUI): Run `python run_gui.py` (auto-installs)
**Solution 2** (Manual):
```bash
python -m pip install pandas openai tqdm openpyxl pyyaml pypdf
```

### Issue: Configuration Not Loading

**Problem**: API key from `.env` not recognized

**Check**:
1. File is named `.env` (not `.env.txt`)
2. Located in project root
3. Key format: `OPENAI_API_KEY=sk-...` (no quotes, no spaces)
4. Restart application after editing

**Debug**:
```python
from litrx.config import DEFAULT_CONFIG
print(DEFAULT_CONFIG)  # Check loaded config
```

### Issue: Language Not Switching

**Problem**: GUI elements don't update when changing language

**Solution**: Ensure components register observers:
```python
class MyTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent.notebook)

        # MUST register observer
        get_i18n().add_observer(self.update_language)

    def update_language(self):
        # Update all translatable widgets
        self.title_label.config(text=t("my_title"))
```

### Issue: Thread-Related GUI Crashes

**Problem**: GUI freezes or crashes during long operations

**Solution**: Always use threads for long operations + `root.after()` for UI updates:
```python
# WRONG - blocks UI thread
def process(self):
    results = self.slow_operation()  # Freezes GUI
    self.update_ui(results)

# CORRECT - background thread
def process(self):
    thread = threading.Thread(target=self._process_thread, daemon=True)
    thread.start()

def _process_thread(self):
    results = self.slow_operation()
    self.root.after(0, self._update_ui, results)  # Thread-safe
```

### Issue: CSV Encoding Errors

**Problem**: `UnicodeDecodeError` when reading Chinese CSV exports

**Solution**: Use UTF-8-sig encoding:
```python
df = pd.read_csv(file_path, encoding="utf-8-sig")
```

### Issue: Column Not Found

**Problem**: `KeyError: 'Title'` when processing different CSV formats

**Solution**: Flexible column detection:
```python
title_col = next(
    (col for col in df.columns if col in ["Title", "文献标题", "Article Title", "标题"]),
    None
)
if title_col is None:
    raise ValueError("Title column not found. Available columns: " + ", ".join(df.columns))

title = row[title_col]
```

## Tips for AI Assistants

### When Exploring the Codebase

1. **Start with architecture docs**: Read `ARCHITECTURE.md` and `AGENTS.md` first
2. **Check existing patterns**: Look at similar features before implementing new ones
3. **Understand the config cascade**: Configuration can come from 5 sources
4. **Follow the i18n system**: All user-facing text must be translatable
5. **Respect the GUI threading model**: Never block the main thread

### When Making Changes

1. **Read before editing**: Always use Read tool before Edit/Write
2. **Preserve patterns**: Match existing code style and architecture
3. **Update both READMEs**: English and Chinese versions must stay in sync
4. **Add translations**: For any new user-facing text
5. **Test manually**: Run GUI and test affected features
6. **Update docs**: If changing architecture or user-facing behavior

### When Debugging Issues

1. **Check configuration first**: Most issues stem from config problems
2. **Verify imports**: Ensure package is installed (`pip install -e .`)
3. **Look for existing solutions**: Similar issues may be solved elsewhere
4. **Check file encodings**: Chinese text requires UTF-8-sig
5. **Inspect DataFrame columns**: CSV formats vary widely

### When Adding Features

1. **Follow existing patterns**: Observer for i18n, Template Method for windows, Dependency Injection for tabs
2. **Use existing utilities**: `AIClient`, `load_config`, `t()`, etc.
3. **Add comprehensive translations**: Both zh and en
4. **Consider error cases**: Missing files, API errors, invalid input
5. **Save progress**: Implement interim saves for long operations
6. **Document in code**: Add docstrings and comments for complex logic

### When Writing Tests

1. **Mock AI clients**: Never make real API calls in tests
2. **Test with real-ish data**: Use realistic DataFrame structures
3. **Cover edge cases**: Empty inputs, missing columns, special characters
4. **Use fixtures**: For reusable test data
5. **Keep tests fast**: Mock external dependencies

## Quick Reference

### Key Files to Know

| File | Purpose |
|------|---------|
| `litrx/config.py` | Configuration cascade logic |
| `litrx/i18n.py` | Internationalization system |
| `litrx/ai_client.py` | AI provider wrapper |
| `litrx/gui/base_window.py` | GUI base class with shared controls |
| `litrx/csv_analyzer.py` | CSV relevance scoring |
| `litrx/abstract_screener.py` | Abstract screening with verification |
| `litrx/matrix_analyzer.py` | Literature matrix analysis (NEW) |
| `prompts_config.json` | AI prompt templates |
| `questions_config.json` | Abstract screening modes |
| `configs/config.yaml` | Default configuration |

### Key Functions to Use

```python
# Translations
from litrx.i18n import t, get_i18n
text = t("key")
get_i18n().add_observer(callback)

# Configuration
from litrx.config import load_config, DEFAULT_CONFIG
config = load_config("path/to/config.yaml", DEFAULT_CONFIG)

# AI Client
from litrx.ai_client import AIClient
client = AIClient("openai", config)
response = client.request(prompt="...", temperature=0.3)

# File I/O
import pandas as pd
df = pd.read_csv(path, encoding="utf-8-sig")
df.to_excel(output_path, index=False)
```

### Configuration Keys

| Key | Values | Purpose |
|-----|--------|---------|
| `AI_SERVICE` | openai, siliconflow | AI provider selection |
| `MODEL_NAME` | gpt-4o, gpt-4-turbo, etc. | Model identifier |
| `OPENAI_API_KEY` | sk-... | OpenAI API key |
| `SILICONFLOW_API_KEY` | ... | SiliconFlow API key |
| `API_BASE` | URL | Custom API endpoint (optional) |
| `LANGUAGE` | zh, en | UI language |
| `ENABLE_VERIFICATION` | true, false | Enable verification workflow |

### GUI Update Pattern

```python
class MyTab(ttk.Frame):
    def __init__(self, parent: BaseWindow):
        super().__init__(parent.notebook)
        self.parent = parent

        # Build UI
        self.label = ttk.Label(self, text=t("my_label"))

        # Register observer
        get_i18n().add_observer(self.update_language)

    def update_language(self):
        """Called when language changes"""
        self.label.config(text=t("my_label"))
```

### Threading Pattern

```python
def start_processing(self):
    # Disable UI
    self.button.config(state="disabled")

    # Run in background
    thread = threading.Thread(target=self._worker, daemon=True)
    thread.start()

def _worker(self):
    # Do work
    result = heavy_operation()

    # Update UI thread-safely
    self.root.after(0, self._on_complete, result)

def _on_complete(self, result):
    # Re-enable UI
    self.button.config(state="normal")
    self.show_result(result)
```

## Additional Resources

- **Architecture Deep Dive**: `docs/ARCHITECTURE.md`
- **Developer Guide**: `AGENTS.md`
- **User Documentation**: `README.md` (English), `Chinese_README.md`
- **Example Test**: `tests/test_abstract_verification.py`

## Changelog

### Version 0.1.0 (Current)
- CSV relevance analysis
- Abstract screening with verification
- Literature matrix analysis (NEW - replaces PDF screening)
- PDF screening (LEGACY)
- Bilingual GUI (Chinese/English)
- Multi-provider AI support (OpenAI, SiliconFlow)

### Known Limitations
- Minimal test coverage (~5%)
- No LICENSE file
- No async/await for concurrent API calls
- No result caching
- PDF screener superseded by matrix analyzer

### Future Enhancements
- Complete tab internationalization
- Configuration schema validation
- Plugin system for custom screening modes
- Batch processing with parallelization
- Result caching to reduce API costs
- Customizable export templates

---

**For AI Assistants**: This document is maintained to help you understand and work effectively with this codebase. When in doubt, refer to the architecture patterns, follow existing code conventions, and prioritize user experience (bilingual support, error handling, progress preservation). Happy coding!
