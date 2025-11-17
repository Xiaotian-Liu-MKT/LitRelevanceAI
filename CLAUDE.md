# CLAUDE.md - AI Assistant Guide for LitRelevanceAI

**Last Updated**: 2025-11-17
**Repository**: LitRelevanceAI
**Package Name**: litrx
**Primary Language**: Python 3.8+

## Table of Contents
1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Architecture & Design](#architecture--design)
4. [Development Workflows](#development-workflows)
5. [Coding Conventions](#coding-conventions)
6. [Key Components](#key-components)
7. [Configuration Management](#configuration-management)
8. [Internationalization](#internationalization)
9. [Testing Guidelines](#testing-guidelines)
10. [Git Workflow](#git-workflow)
11. [Common Tasks](#common-tasks)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

LitRelevanceAI (`litrx`) is an AI-assisted toolkit for academic literature review and analysis. It helps researchers evaluate how well academic papers match their research topics using various AI models (OpenAI, Gemini, SiliconFlow).

### Core Features

1. **CSV Relevance Analysis** (`litrx csv`)
   - Scores Scopus CSV exports from 0-100
   - Provides model-generated explanations for each paper
   - Sortable GUI table with double-click to view full analyses

2. **Abstract Screening** (`litrx abstract`)
   - Configurable yes/no criteria and open questions
   - Optional AI answer verification against source text
   - Mode-based question presets from `questions_config.json`
   - Supports both CLI and GUI (`--gui` flag)

3. **Literature Matrix Analysis** (`litrx matrix`) **[NEW]**
   - Replaces the older PDF screening functionality
   - Converts PDFs to text and analyzes them against configurable dimensions
   - Supports 7 question types: text, yes_no, single_choice, multiple_choice, number, rating, list
   - Metadata matching with Zotero integration
   - Configurable via `configs/matrix/default.yaml`

4. **Modular Tkinter GUI** (`python run_gui.py`)
   - Dedicated tabs: CSV Analysis, Abstract Screening, Literature Matrix
   - Unified configuration panel with provider switching (OpenAI/Gemini/SiliconFlow)
   - API key persistence and config saving to `~/.litrx_gui.yaml`
   - Language support: Chinese (zh) and English (en)

### Technology Stack
- **Python**: ≥3.8
- **AI Integration**: LiteLLM (unified interface for OpenAI/Gemini)
- **GUI**: Tkinter (standard library)
- **Data Processing**: pandas, openpyxl
- **PDF Processing**: pypdf
- **Configuration**: PyYAML, dotenv pattern

---

## Repository Structure

```
LitRelevanceAI/
├── litrx/                          # Main package
│   ├── __init__.py
│   ├── __main__.py                 # python -m litrx entry point
│   ├── cli.py                      # Command dispatcher (csv/abstract/matrix)
│   ├── config.py                   # Config loading utilities
│   ├── ai_client.py                # LiteLLM wrapper for AI providers
│   ├── i18n.py                     # Internationalization (zh/en)
│   ├── csv_analyzer.py             # CSV relevance scoring
│   ├── abstract_screener.py        # Abstract screening with verification
│   ├── matrix_analyzer.py          # Literature matrix analysis [NEW]
│   └── gui/
│       ├── __init__.py
│       ├── base_window.py          # BaseWindow class, shared controls
│       ├── main_window.py          # LitRxApp - tab registration
│       ├── tabs/
│       │   ├── __init__.py
│       │   ├── csv_tab.py          # CSV analysis GUI
│       │   ├── abstract_tab.py     # Abstract screening GUI
│       │   └── matrix_tab.py       # Literature matrix GUI [NEW]
│       └── dialogs/
│           ├── __init__.py
│           └── dimension_editor.py # Matrix dimension editor [NEW]
│
├── configs/
│   ├── config.yaml                 # Default API configuration
│   ├── questions/                  # Prompt templates (YAML)
│   └── matrix/
│       └── default.yaml            # Matrix dimensions config [NEW]
│
├── docs/                           # Additional documentation
├── tests/                          # Test suite (currently minimal)
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore patterns
├── pyproject.toml                  # Package metadata and dependencies
├── setup.cfg                       # Additional package configuration
├── run_gui.py                      # GUI launcher with auto-install
├── questions_config.json           # Abstract screening question presets
├── prompts_config.json             # Prompt templates
├── README.md                       # English documentation
├── Chinese_README.md               # Chinese documentation
├── AGENTS.md                       # Simpler agent guide (superseded by this file)
└── CLAUDE.md                       # This file (comprehensive AI assistant guide)
```

### Key File Purposes

| File | Purpose |
|------|---------|
| `litrx/cli.py` | Command-line interface dispatcher for all subcommands |
| `litrx/config.py` | Unified configuration loading (env → YAML/JSON → CLI args) |
| `litrx/ai_client.py` | Abstraction layer for OpenAI/Gemini/SiliconFlow via LiteLLM |
| `litrx/i18n.py` | Translation management with observer pattern |
| `litrx/gui/base_window.py` | Shared GUI framework, config persistence |
| `configs/config.yaml` | Baseline defaults for AI service, model, API keys |
| `questions_config.json` | Mode-aware question templates for abstract screening |
| `configs/matrix/default.yaml` | Literature matrix dimension definitions |

---

## Architecture & Design

### Configuration Hierarchy

Configuration merges in this order (later values override earlier):

1. **`configs/config.yaml`** - Baseline defaults
2. **`~/.litrx_gui.yaml`** - User GUI preferences
3. **`.env` file** - Environment variables
4. **Command-line arguments** - Runtime overrides

Implementation: `litrx/config.py` → `load_config()`, `load_env_file()`

### AI Client Pattern

**File**: `litrx/ai_client.py`

The `AIClient` class provides a unified interface to multiple AI providers:

```python
class AIClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        # Sets up credentials based on AI_SERVICE: openai/gemini/siliconflow
        # Uses LiteLLM for abstraction

    def request(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        # Sends chat completion request
        # Returns raw LiteLLM response
```

**Key Points**:
- SiliconFlow uses OpenAI-compatible API with custom base URL
- API keys set via environment variables
- Error messages currently in Chinese (consider i18n)

### GUI Architecture

**Base Class**: `litrx/gui/base_window.py` → `BaseWindow`

All GUI tabs inherit from `BaseWindow`, which provides:
- AI service selector dropdown (OpenAI/Gemini/SiliconFlow)
- API key field with provider-specific persistence
- Model name and temperature controls
- Language selector (zh/en) with i18n integration
- Config save/load to `~/.litrx_gui.yaml`

**Tab Registration**: `litrx/gui/main_window.py` → `LitRxApp`

```python
class LitRxApp(BaseWindow):
    def __init__(self):
        super().__init__()
        # Registers tabs via self.notebook.add(...)
        # CSV, Abstract, Matrix tabs
```

**Pattern**: Each tab is a self-contained module under `litrx/gui/tabs/`.

### Internationalization (i18n)

**File**: `litrx/i18n.py`

Uses observer pattern for language switching:

```python
from litrx.i18n import get_i18n, t

i18n = get_i18n()
i18n.add_observer(self.update_ui_language)  # Re-render on language change

text = t("config_settings")  # Returns translated string
```

**Supported Languages**: `zh` (Chinese), `en` (English)

---

## Development Workflows

### Installation

```bash
# Clone repository
git clone https://github.com/Xiaotian-Liu-MKT/LitRelevanceAI.git
cd LitRelevanceAI

# Install in editable mode
python -m pip install -e .

# Configure environment
cp .env.example .env
# Edit .env to add API keys
```

### Running the Application

**CLI Usage**:
```bash
# CSV analysis
litrx csv
python -m litrx csv

# Abstract screening (CLI)
litrx abstract

# Abstract screening (GUI)
litrx abstract --gui

# Literature matrix
litrx matrix
```

**GUI Usage**:
```bash
python run_gui.py
# Auto-installs missing dependencies on first run
```

### Adding a New Feature

1. **Create feature branch**: `git checkout -b claude/feature-name-<session-id>`
2. **Implement changes** following coding conventions
3. **Update configuration** if needed (`configs/`, `.env.example`)
4. **Add tests** in `tests/` (see Testing Guidelines)
5. **Update documentation**: `README.md`, `Chinese_README.md`, this file
6. **Test thoroughly**:
   ```bash
   python -m pip install -e .
   python -m litrx --help
   pytest
   ```
7. **Commit with conventional commits**: `feat:`, `fix:`, `docs:`, etc.
8. **Push to branch**: `git push -u origin <branch-name>`
9. **Create pull request** with summary and testing evidence

---

## Coding Conventions

### Python Style

- **PEP 8** compliance (4-space indents, snake_case)
- **Type hints** for function signatures
- **Docstrings** for public functions (NumPy style preferred)
- **Import order**: stdlib → third-party → local modules

Example:
```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from litellm import completion

from .config import load_config
from .i18n import t


def analyze_csv(file_path: str, topic: str) -> pd.DataFrame:
    """Analyze CSV file for relevance to research topic.

    Parameters
    ----------
    file_path : str
        Path to Scopus CSV export
    topic : str
        Research topic description

    Returns
    -------
    pd.DataFrame
        Analysis results with scores and explanations
    """
    ...
```

### Error Handling

- Use informative error messages
- Consider i18n for user-facing errors
- Raise `RuntimeError` for configuration issues
- Use `try-except` for external API calls

```python
try:
    response = client.request(messages)
except Exception as e:
    raise RuntimeError(f"AI 请求失败: {e}") from e
```

### File Naming

- Python modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Configuration Files

- **YAML**: Preferred for nested configs (`configs/matrix/default.yaml`)
- **JSON**: Used for mode presets (`questions_config.json`, `prompts_config.json`)
- **Comments**: Use YAML comments (`#`) for documentation

---

## Key Components

### 1. CSV Analyzer (`litrx/csv_analyzer.py`)

**Purpose**: Score Scopus CSV exports for relevance to research topic

**Key Functions**:
- `main()`: CLI entry point
- Reads CSV with pandas
- Sends title/abstract to AI for scoring (0-100)
- Saves results with timestamp

**GUI Tab**: `litrx/gui/tabs/csv_tab.py`
- Research topic input
- File selection
- Sortable results table
- Double-click to view full analysis

### 2. Abstract Screener (`litrx/abstract_screener.py`)

**Purpose**: Apply configurable criteria to abstracts with optional verification

**Key Features**:
- Mode-based questions from `questions_config.json`
- `ENABLE_VERIFICATION` flag: second-pass AI validation
- Verification results in `<column>_verified` fields
- GUI log with ✔/✖ markers

**GUI Tab**: `litrx/gui/tabs/abstract_tab.py`
- Mode selector dropdown
- "Add Mode" and "Edit Questions" dialogs
- "Enable verification" checkbox
- Export to CSV/Excel

### 3. Matrix Analyzer (`litrx/matrix_analyzer.py`) **[NEW]**

**Purpose**: Extract structured information from PDFs using configurable dimensions

**Question Types**:
1. **text**: Open-ended responses
2. **yes_no**: Yes/No/Uncertain
3. **single_choice**: Select one option
4. **multiple_choice**: Select multiple options
5. **number**: Extract numeric values
6. **rating**: 1-5 scale subjective assessment
7. **list**: Extract multiple items (semicolon-separated)

**Configuration**: `configs/matrix/default.yaml`
- `research_question`: Optional context
- `dimensions[]`: List of dimension objects
- `metadata_matching`: Zotero integration settings
- `output`: File format and column ordering

**GUI Tab**: `litrx/gui/tabs/matrix_tab.py`
- PDF folder selection
- Dimension editor dialog (`litrx/gui/dialogs/dimension_editor.py`)
- Metadata file upload
- Processing status and result viewing

**Metadata Matching**:
- Prioritizes: DOI → Title → Key (Zotero Item Key)
- Title similarity threshold: 80%
- Filename parsing: Recognizes `Author_Year_Title.pdf` format

### 4. AI Client (`litrx/ai_client.py`)

**Purpose**: Unified AI provider interface

**Supported Providers**:
- **OpenAI**: Standard GPT models
- **Gemini**: Google AI models
- **SiliconFlow**: OpenAI-compatible API with Chinese providers

**Configuration**:
```python
config = {
    "AI_SERVICE": "openai",  # or "gemini" or "siliconflow"
    "MODEL_NAME": "gpt-4o",
    "OPENAI_API_KEY": "sk-...",
    "API_BASE": ""  # Optional custom endpoint
}
client = AIClient(config)
response = client.request(messages=[{"role": "user", "content": "..."}])
```

### 5. Configuration Manager (`litrx/config.py`)

**Key Functions**:
- `load_env_file(env_path=".env")`: Parse .env file
- `load_config(path, default=None)`: Load YAML/JSON config
- `DEFAULT_CONFIG`: Base configuration dictionary

**Merge Strategy**:
```python
config = DEFAULT_CONFIG.copy()
config.update(yaml_config)
config.update(env_vars)
config.update(cli_args)
```

### 6. Internationalization (`litrx/i18n.py`)

**Classes**:
- `I18n`: Manages translations with observer pattern
- Global instance: `get_i18n()`
- Shorthand: `t(key, **kwargs)`

**Usage**:
```python
from litrx.i18n import t, get_i18n

# Simple translation
label_text = t("config_settings")  # " Configuration Settings "

# With formatting
message = t("config_saved", path="/path/to/file")

# Language switching
i18n = get_i18n()
i18n.current_language = "zh"  # Triggers observer callbacks
```

---

## Configuration Management

### Environment Variables (`.env`)

```bash
# API Keys (choose one or more)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SILICONFLOW_API_KEY=...

# Optional
API_BASE=https://custom-endpoint.com/v1
ENABLE_VERIFICATION=true
```

### Config Files

**`configs/config.yaml`** (Baseline):
```yaml
AI_SERVICE: openai
MODEL_NAME: gpt-4o
OPENAI_API_KEY: ""
GEMINI_API_KEY: ""
SILICONFLOW_API_KEY: ""
API_BASE: ""
```

**`~/.litrx_gui.yaml`** (User Preferences):
```yaml
AI_SERVICE: openai
OPENAI_API_KEY: sk-...
MODEL_NAME: gpt-4o-mini
LANGUAGE: zh
```

### Question Configuration

**`questions_config.json`** (Abstract Screening):
```json
{
  "weekly": {
    "questions": [
      {"key": "relevant", "question": "Is this relevant?", "type": "yes_no"}
    ]
  },
  "custom_mode": { ... }
}
```

**`configs/matrix/default.yaml`** (Literature Matrix):
```yaml
research_question: "Your research question here"
dimensions:
  - type: text
    key: main_findings
    question: "What are the main findings?"
    column_name: "Main Findings"
  # ... more dimensions
```

---

## Internationalization

### Adding New Translations

Edit `litrx/i18n.py`:

```python
TRANSLATIONS = {
    "zh": {
        "new_key": "新功能",
        # ...
    },
    "en": {
        "new_key": "New Feature",
        # ...
    }
}
```

### Using in GUI

```python
class MyTab(BaseWindow):
    def _create_ui(self):
        label = tk.Label(self, text=t("new_key"))

        # Register for language change updates
        i18n = get_i18n()
        i18n.add_observer(self._update_language)

    def _update_language(self):
        # Re-render UI with new translations
        ...
```

### Language Persistence

Language is saved in `~/.litrx_gui.yaml` as a language code (`zh` or `en`), not the display name.

**Recent Fix**: Language selection now saves as ISO code instead of display name (see commit `6e366f9`).

---

## Testing Guidelines

### Current State

The `tests/` directory is currently minimal. Future development should expand test coverage.

### Running Tests

```bash
pytest
# Or with coverage
pytest --cov=litrx
```

### Adding Tests

**Structure**:
```
tests/
├── test_config.py          # Config loading tests
├── test_ai_client.py       # AI client tests (mock LiteLLM)
├── test_csv_analyzer.py    # CSV analysis logic
├── test_matrix_analyzer.py # Matrix analysis tests
└── fixtures/               # Sample data files
```

**Example Test**:
```python
import pytest
from litrx.config import load_config

def test_load_config_yaml(tmp_path):
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("AI_SERVICE: gemini\n")

    config = load_config(str(config_file))
    assert config["AI_SERVICE"] == "gemini"
```

### Pre-Commit Checklist

Before committing, always run:

```bash
# 1. Install in editable mode
python -m pip install -e .

# 2. Verify CLI
python -m litrx --help

# 3. Run tests
pytest

# 4. Test GUI launch
python run_gui.py  # Should open without errors
```

---

## Git Workflow

### Branch Naming

**Pattern**: `claude/<feature-description>-<session-id>`

Example: `claude/literature-matrix-feature-0171HJL4mKnd4hSgRdnG6f72`

### Commit Message Convention

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

**Examples**:
```bash
git commit -m "feat: implement literature matrix analysis"
git commit -m "fix: resolve language selection bug"
git commit -m "docs: update README with matrix feature"
```

### Push Strategy

Always push with upstream tracking:

```bash
git push -u origin claude/feature-name-<session-id>
```

**Critical**: Branch must start with `claude/` and end with matching session ID, otherwise push fails with 403.

**Network Retry**: If push fails due to network, retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s).

### Pull Request Process

1. **Title**: Clear, descriptive summary
2. **Description**:
   - Summary of changes
   - Related issues (if any)
   - Testing evidence
   - Screenshots for UI changes
3. **Reviewers**: Confirm linting, tests, and docs before merging
4. **Merge**: Use squash merge for cleaner history

---

## Common Tasks

### Task 1: Add a New GUI Tab

1. **Create tab file**: `litrx/gui/tabs/my_new_tab.py`

```python
import tkinter as tk
from ..base_window import BaseWindow
from litrx.i18n import t

class MyNewTab(BaseWindow):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_ui()

    def _create_ui(self):
        label = tk.Label(self, text=t("my_tab_title"))
        label.pack()
```

2. **Add translation keys** to `litrx/i18n.py`:

```python
TRANSLATIONS["zh"]["my_tab_title"] = "我的新标签"
TRANSLATIONS["en"]["my_tab_title"] = "My New Tab"
```

3. **Register in main window** (`litrx/gui/main_window.py`):

```python
from .tabs.my_new_tab import MyNewTab

class LitRxApp(BaseWindow):
    def __init__(self):
        super().__init__()
        # ...
        my_tab = MyNewTab(self.notebook)
        self.notebook.add(my_tab, text=t("my_tab_title"))
```

4. **Update observer for language switching**:

```python
def _update_language(self):
    # Update tab title when language changes
    self.notebook.tab(tab_index, text=t("my_tab_title"))
```

### Task 2: Add a New Matrix Dimension Type

1. **Define type in config** (`configs/matrix/default.yaml`):

```yaml
dimensions:
  - type: custom_type
    key: my_field
    question: "Your question here"
    column_name: "Column Name"
    # ... custom parameters
```

2. **Update parser** in `litrx/matrix_analyzer.py`:

```python
def parse_dimension_response(dimension, response_text):
    if dimension["type"] == "custom_type":
        # Custom parsing logic
        return parsed_value
    # ... existing types
```

3. **Update dimension editor** (`litrx/gui/dialogs/dimension_editor.py`):

```python
# Add UI controls for new type
if dimension_type == "custom_type":
    # Create custom input fields
    ...
```

### Task 3: Add a New AI Provider

1. **Update `litrx/ai_client.py`**:

```python
class AIClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        service = config.get("AI_SERVICE", "openai")
        # ...
        elif service == "new_provider":
            api_key = config.get("NEW_PROVIDER_API_KEY") or os.getenv("NEW_PROVIDER_API_KEY")
            if not api_key:
                raise RuntimeError("New Provider API key not configured.")
            os.environ["OPENAI_API_KEY"] = api_key  # If OpenAI-compatible
            os.environ["OPENAI_BASE_URL"] = "https://api.newprovider.com/v1"
```

2. **Update `litrx/config.py`**:

```python
DEFAULT_CONFIG = {
    # ...
    "NEW_PROVIDER_API_KEY": "",
}
```

3. **Update `configs/config.yaml`**:

```yaml
NEW_PROVIDER_API_KEY: ""
```

4. **Update GUI** (`litrx/gui/base_window.py`):

```python
self.service_selector["values"] = ["openai", "gemini", "siliconflow", "new_provider"]
```

### Task 4: Update Documentation

When adding features, update **all** of:

1. **README.md** (English)
2. **Chinese_README.md** (Chinese)
3. **CLAUDE.md** (this file)
4. **AGENTS.md** (if applicable)
5. Inline docstrings and comments

### Task 5: Debug Configuration Issues

**Problem**: API key not being recognized

**Solution**:
```bash
# Check env loading
python -c "from litrx.config import load_env_file; import os; load_env_file(); print(os.environ.get('OPENAI_API_KEY'))"

# Check config merging
python -c "from litrx.ai_client import load_config; print(load_config())"

# Check GUI config
cat ~/.litrx_gui.yaml
```

---

## Troubleshooting

### Issue: pytest reports "no tests ran"

**Cause**: The repository currently lacks comprehensive tests.

**Solution**: Add tests for new features. See [Testing Guidelines](#testing-guidelines).

### Issue: Missing GUI dependencies

**Cause**: First-time GUI launch.

**Solution**: `run_gui.py` auto-installs required packages. Wait for installation to complete.

### Issue: Language selection not persisting

**Cause**: Fixed in commit `6e366f9`. Ensure you're on latest `main`.

**Solution**:
```bash
git pull origin main
python -m pip install -e .
```

### Issue: Push fails with 403

**Cause**: Branch name doesn't match required pattern.

**Solution**: Branch must start with `claude/` and end with session ID matching the current session.

```bash
# Correct
git checkout -b claude/fix-language-bug-013zcuHoXk5oVXEKeNTMyufL

# Incorrect
git checkout -b fix-language-bug
```

### Issue: Configuration not loading

**Cause**: Config file format error or wrong path.

**Debug**:
```python
from litrx.config import load_config
try:
    config = load_config("path/to/config.yaml")
    print(config)
except Exception as e:
    print(f"Error: {e}")
```

**Common Fixes**:
- Check YAML syntax (indentation, colons)
- Verify file path is absolute or relative to CWD
- Ensure PyYAML is installed: `pip install pyyaml`

### Issue: AI requests fail

**Cause**: Invalid API key or network issue.

**Debug**:
```python
from litrx.ai_client import AIClient

config = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "gpt-4o",
    "OPENAI_API_KEY": "your-key"
}

try:
    client = AIClient(config)
    response = client.request([{"role": "user", "content": "Test"}])
    print(response)
except Exception as e:
    print(f"Error: {e}")
```

**Common Fixes**:
- Verify API key is valid and has credits
- Check `API_BASE` if using custom endpoint
- Test network connectivity: `curl https://api.openai.com/v1/models`

---

## Recent Changes & Features

### Literature Matrix Feature (2025-11-17)

**Commit**: `badd6b4` - `feat: 实现文献矩阵分析功能，替换PDF筛选`

**Changes**:
- Added `litrx/matrix_analyzer.py` - Core analysis engine
- Added `litrx/gui/tabs/matrix_tab.py` - GUI interface
- Added `litrx/gui/dialogs/dimension_editor.py` - Dimension configuration
- Added `configs/matrix/default.yaml` - Default dimension templates
- Updated CLI to include `matrix` subcommand
- Replaced PDF screening with more flexible matrix approach

**Key Features**:
- 7 dimension types (text, yes_no, single_choice, multiple_choice, number, rating, list)
- Metadata matching with Zotero
- Configurable output format and column ordering

### Language Selection Fix (2025-11-17)

**Commit**: `6e366f9` - `fix: normalize persisted GUI language selection`

**Change**: Language now saves as ISO code (`zh`/`en`) instead of display name, preventing KeyError on load.

**Files Modified**:
- `litrx/gui/base_window.py`
- `litrx/i18n.py`

---

## Best Practices for AI Assistants

### When Modifying Code

1. **Always read files before editing** - Use Read tool first
2. **Preserve exact indentation** - Match existing style
3. **Update all language versions** - Both README files
4. **Test after changes**:
   ```bash
   python -m pip install -e .
   python -m litrx --help
   pytest
   ```
5. **Update this file** if architecture changes

### When Adding Features

1. **Check existing patterns** - Follow established conventions
2. **Add i18n support** - Both `zh` and `en` translations
3. **Update config files** - `.env.example`, `configs/`
4. **Write tests** - At least smoke tests for new functionality
5. **Document in docstrings** - NumPy-style preferred

### When Debugging

1. **Use specialized tools** - Read, Grep, Glob (not bash commands)
2. **Check recent commits** - `git log --oneline -10`
3. **Review related issues** - GitHub issue tracker
4. **Test in isolation** - Use Python REPL for quick checks

### Communication

1. **Be concise** - CLI output should be short and clear
2. **Use code references** - Format: `file_path:line_number`
3. **Provide context** - Explain *why*, not just *what*
4. **Link to docs** - Reference this file or README when helpful

---

## Useful Commands

### Development

```bash
# Install dependencies
python -m pip install -e .

# Run specific subcommand
litrx csv
litrx abstract --gui
litrx matrix

# Launch GUI
python run_gui.py

# Run tests
pytest
pytest -v  # Verbose
pytest --cov=litrx  # With coverage
```

### Git Operations

```bash
# Create feature branch
git checkout -b claude/feature-name-<session-id>

# Check status
git status

# Stage and commit
git add .
git commit -m "feat: description"

# Push with upstream tracking
git push -u origin claude/feature-name-<session-id>

# View recent commits
git log --oneline -10
```

### Code Search

```bash
# Find files
find . -name "*.py" | grep matrix

# Search content (use Grep tool in Claude, not bash)
# Example: Grep pattern="class.*Analyzer" type="py"
```

### Configuration Debugging

```bash
# Check environment
python -c "from litrx.config import load_env_file; import os; load_env_file(); print(os.environ)"

# Test config loading
python -c "from litrx.ai_client import load_config; import json; print(json.dumps(load_config(), indent=2))"

# View GUI config
cat ~/.litrx_gui.yaml
```

---

## Appendix: File Reference

### Core Python Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `litrx/cli.py` | ~30 | CLI dispatcher |
| `litrx/config.py` | ~70 | Config utilities |
| `litrx/ai_client.py` | ~70 | AI provider abstraction |
| `litrx/i18n.py` | ~330 | Internationalization |
| `litrx/csv_analyzer.py` | ~400 | CSV relevance analysis |
| `litrx/abstract_screener.py` | ~800 | Abstract screening |
| `litrx/matrix_analyzer.py` | ~700 | Literature matrix [NEW] |
| `litrx/gui/base_window.py` | ~700 | GUI base class |
| `litrx/gui/main_window.py` | ~50 | Tab registration |
| `litrx/gui/tabs/csv_tab.py` | ~200 | CSV GUI |
| `litrx/gui/tabs/abstract_tab.py` | ~700 | Abstract GUI |
| `litrx/gui/tabs/matrix_tab.py` | ~650 | Matrix GUI [NEW] |
| `litrx/gui/dialogs/dimension_editor.py` | ~200 | Dimension editor [NEW] |

### Configuration Files

| File | Format | Purpose |
|------|--------|---------|
| `.env` | ENV | Environment variables (gitignored) |
| `.env.example` | ENV | Template for .env |
| `configs/config.yaml` | YAML | Baseline API config |
| `configs/matrix/default.yaml` | YAML | Matrix dimensions [NEW] |
| `questions_config.json` | JSON | Abstract screening modes |
| `prompts_config.json` | JSON | Prompt templates |
| `~/.litrx_gui.yaml` | YAML | User GUI preferences |

---

**Document Maintenance**: Update this file whenever:
- New features are added
- Architecture changes
- Configuration system is modified
- New conventions are established
- Breaking changes occur

**Feedback**: If this guide is missing information, please update it or note the gap in a TODO comment.
