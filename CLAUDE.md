# CLAUDE.md - AI Assistant Guide for LitRelevanceAI

This document provides comprehensive guidance for AI assistants (like Claude Code) working with the LitRelevanceAI codebase. It covers architecture, conventions, workflows, and important context to help you work effectively on this project.

## Project Overview

**LitRelevanceAI** (`litrx` package) is an AI-assisted literature review toolkit for academic researchers. It helps screen and analyze academic papers using large language models (OpenAI GPT and SiliconFlow).

### Core Functionality
- **CSV Relevance Analysis**: Score Scopus exports (0-100) with AI-generated relevance explanations
- **Abstract Screening**: Configurable yes/no criteria and open questions with optional verification workflow and concurrent processing
- **Literature Matrix Analysis**: Structured data extraction with 7 question types (text, yes_no, single_choice, multiple_choice, number, rating, list) featuring concurrent processing for 3-4x speed improvement
- **Concurrent Processing**: High-performance parallel processing with configurable workers, integrated caching, and checkpoint support
- **AI-Assisted Configuration**: Natural language generation of screening modes and matrix dimensions
- **Result Caching**: Intelligent caching to reduce redundant API calls and costs (50-90% reduction)
- **Progress Management**: Atomic checkpoints with automatic recovery from interruptions
- **Secure Key Management**: Optional keyring integration for secure API key storage
- **PDF Screening**: Legacy full-text analysis (superseded by matrix analyzer)
- **Bilingual GUI**: PyQt6 interface with Chinese/English support

### Technology Stack
- **Language**: Python 3.8+
- **AI Provider**: OpenAI SDK (supports OpenAI and SiliconFlow APIs)
- **GUI**: PyQt6
- **Data**: pandas, openpyxl
- **PDF**: pypdf
- **Config**: YAML, JSON, .env files
- **Security**: keyring (secure credential storage)
- **Concurrency**:
  - ThreadPoolExecutor (parallel processing)
  - filelock (atomic file operations)
  - threading.Event (graceful cancellation)
- **Validation**: pydantic >= 2.0
- **Testing**: pytest (minimal coverage currently)

## Repository Structure

```
LitRelevanceAI/
├── litrx/                          # Main package (~7000+ LOC)
│   ├── __init__.py                 # Package initialization
│   ├── __main__.py                 # Entry point: python -m litrx
│   ├── cli.py                      # CLI dispatcher (csv/abstract/matrix commands)
│   ├── config.py                   # Cascading configuration management
│   ├── config_factory.py           # Configuration factory patterns
│   ├── ai_client.py                # OpenAI SDK wrapper for AI providers
│   ├── ai_config_generator.py      # AI-powered configuration generation
│   ├── i18n.py                     # Internationalization (Observer pattern)
│   ├── csv_analyzer.py             # CSV relevance scoring (LiteratureAnalyzer)
│   ├── abstract_screener.py        # Title/abstract screening with verification
│   ├── pdf_screener.py             # PDF analysis (LEGACY - use matrix_analyzer)
│   ├── matrix_analyzer.py          # Literature matrix analysis
│   ├── cache.py                    # Result caching system for AI responses
│   ├── progress_manager.py         # Atomic checkpoint management with file locking
│   ├── task_manager.py             # Cancellable task management
│   ├── key_manager.py              # Secure API key storage via keyring
│   ├── prompt_builder.py           # Reusable prompt building
│   ├── exceptions.py               # Custom exception hierarchy
│   ├── constants.py                # Project-wide constants
│   ├── utils.py                    # Shared utility functions
│   ├── logging_config.py           # Centralized logging configuration
│   ├── resources.py                # Resource path helper for PyInstaller
│   ├── prompts/                    # AI prompt templates
│   │   ├── abstract_mode_generation.txt    # Template for mode generation
│   │   └── matrix_dimension_generation.txt # Template for dimension generation
│   └── gui/                        # PyQt6 GUI components
│       ├── base_window_qt.py       # BaseWindow (Qt) class with shared controls
│       ├── main_window_qt.py       # LitRxApp (Qt) - main application window
│       ├── tabs_qt/                # Feature tabs (Qt)
│       │   ├── csv_tab.py          # CSV analysis tab
│       │   ├── abstract_tab.py     # Abstract screening tab
│       │   └── matrix_tab.py       # Literature matrix tab
│       └── dialogs_qt/             # Qt dialogs
│           ├── dimensions_editor_qt.py     # Basic dimension editor
│           ├── dimensions_editor_qt_v2.py  # Enhanced graphical dimension editor
│           ├── ai_mode_assistant_qt.py     # AI assistant for screening modes
│           └── ai_matrix_assistant_qt.py   # AI assistant for matrix dimensions
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
│   ├── AI_ASSISTED_CONFIG_DESIGN.md           # AI-assisted config design
│   ├── AI_ASSISTED_CONFIG_IMPLEMENTATION_PLAN.md  # Implementation plan
│   ├── GPT5_GUIDE.md               # Guide for newer AI models
│   └── 项目功能与架构概览.md        # Chinese overview
├── tests/                          # Unit tests (minimal coverage)
│   └── test_abstract_verification.py
├── run_gui.py                      # GUI launcher with auto-install
├── test_ai_dialogs.py              # Test script for AI assistant dialogs
├── questions_config.json           # Abstract screening modes
├── prompts_config.json             # AI prompt templates (GUI-editable)
├── pyproject.toml                  # PEP 621 packaging
├── setup.cfg                       # Legacy packaging
├── .env.example                    # API key template
├── README.md                       # English documentation
├── Chinese_README.md               # Chinese documentation
├── AGENTS.md                       # Developer guide
├── TEST_AI_ASSISTANTS.md           # Testing guide for AI assistants
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

# 4. Launch PyQt6 GUI
python run_gui.py  # Auto-installs dependencies (incl. PyQt6)
```

### Running Tests
```bash
pytest tests/  # Currently minimal test coverage
```

## Packaging for Distribution

Two recommended paths to ship a clickable app:

- PyInstaller (recommended)
  - Windows: run `packaging\build_win.bat`
  - macOS: run `bash packaging/build_mac.sh`
  - Outputs:
    - Windows: `dist/LitRelevanceAI/LitRelevanceAI.exe` (ship the whole folder)
    - macOS: `dist/LitRelevanceAI.app`
  - The code uses `litrx.resources.resource_path()` to load bundled files (`configs/`, `questions_config.json`, `prompts_config.json`) in frozen builds.

- Nuitka/Briefcase (advanced)
  - Possible alternatives for performance or native installers; require extra setup.

First-Run Onboarding
- On first launch, the GUI shows a minimal wizard to select provider (OpenAI/SiliconFlow) and enter API key, with an option to save to keyring and config.

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

**Location**: `litrx/gui/base_window_qt.py`

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

### 3. Dependency Injection (GUI Tabs - Qt)

**Location**: `litrx/gui/tabs_qt/*.py`

Tabs receive parent BaseWindow and access shared resources:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from litrx.gui.base_window_qt import BaseWindow
from litrx.i18n import t, get_i18n

class MyTab(QWidget):
    def __init__(self, parent: BaseWindow):
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout(self)
        self.title_label = QLabel(t("my_tab_title"))
        layout.addWidget(self.title_label)

        get_i18n().add_observer(self.update_language)

    def update_language(self):
        self.title_label.setText(t("my_tab_title"))
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

### 5. Result Caching System

**Location**: `litrx/cache.py`

The caching system prevents redundant API calls by storing analysis results:

```python
from litrx.cache import ResultCache

# Initialize cache (defaults to ~/.litrx/cache with 30-day TTL)
cache = ResultCache()

# Check for cached result
cache_key = cache.get(title="Paper Title", abstract="Abstract text")
if cache_key:
    result = cache_key
else:
    # Make API call
    result = ai_client.request(prompt)
    # Cache the result
    cache.set(title="Paper Title", abstract="Abstract text", result=result)
```

**Key Features**:
- SHA256-based cache keys from content
- Configurable TTL (time-to-live)
- Automatic cleanup of expired entries
- Thread-safe operations
- Stored in `~/.litrx/cache/`

### 6. Progress Management System

**Location**: `litrx/progress_manager.py`

Atomic checkpoint system with file locking prevents data loss:

```python
from litrx.progress_manager import ProgressManager

# Initialize for output file
pm = ProgressManager("output.csv")

# Save checkpoint (atomic with file locking)
pm.save_checkpoint(
    df=results_dataframe,
    last_index=100,
    metadata={"total": 500, "timestamp": "..."}
)

# Load checkpoint on restart
checkpoint = pm.load_checkpoint()
if checkpoint:
    df = checkpoint["df"]
    last_index = checkpoint["last_index"]
    # Resume from last_index + 1
```

**Key Features**:
- Atomic file writes (write to temp, then rename)
- File locking to prevent corruption
- Automatic .bak backup before overwrite
- Checkpoint stored in `.litrx_checkpoints/` directory
- Resume capability after crashes

### 7. Task Management System

**Location**: `litrx/task_manager.py`

Provides cancellable long-running operations:

```python
from litrx.task_manager import CancellableTask, TaskCancelledException

task = CancellableTask()

def long_operation():
    for i in range(1000):
        if task.is_cancelled():
            raise TaskCancelledException("User cancelled")
        # Do work
        process_item(i)

# In GUI: Cancel button
cancel_button.clicked.connect(task.cancel)
```

**Key Features**:
- Thread-safe cancellation
- Automatic executor cleanup
- Cancellation state tracking
- Integration with GUI cancel buttons

### 8. Secure Key Management

**Location**: `litrx/key_manager.py`

Optional secure storage using system keyring:

```python
from litrx.key_manager import KeyManager

km = KeyManager()

# Store API key securely
km.set_key("openai_api_key", "sk-...")

# Retrieve API key
api_key = km.get_key("openai_api_key")

# Delete API key
km.delete_key("openai_api_key")
```

**Key Features**:
- Uses system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Fallback to config files if keyring unavailable
- Service name: `litrx`
- Key identifiers: `openai_api_key`, `siliconflow_api_key`

### 9. Custom Exception Hierarchy

**Location**: `litrx/exceptions.py`

Provides clear error messages and better error handling:

```python
from litrx.exceptions import (
    LitRxError,              # Base exception
    ConfigurationError,      # Config-related errors
    APIKeyMissingError,      # Missing API key
    APIRequestError,         # API request failures
    ValidationError,         # Data validation errors
    FileProcessingError      # File I/O errors
)

try:
    client = AIClient(config)
except APIKeyMissingError as e:
    # User-friendly message in Chinese with instructions
    show_error_dialog(str(e))
```

**Benefits**:
- User-friendly error messages (often in Chinese)
- Specific exception types for different error categories
- Helpful troubleshooting instructions included
- Better error tracking and logging

### 10. AI-Assisted Configuration Generation

**Location**: `litrx/ai_config_generator.py`

Generate screening modes and matrix dimensions from natural language:

```python
from litrx.ai_config_generator import AbstractModeGenerator, MatrixDimensionGenerator

# Generate abstract screening mode
mode_gen = AbstractModeGenerator(config)
mode_config = mode_gen.generate_mode(
    description="我想筛选心理学实证研究，需要知道样本量和研究方法",
    language="zh"
)
# Returns: {"mode_name": "...", "criteria": [...], "questions": [...]}

# Generate matrix dimensions
dim_gen = MatrixDimensionGenerator(config)
dimensions = dim_gen.generate_dimensions(
    description="提取研究方法、样本量、主要发现",
    language="zh"
)
# Returns: [{"name": "...", "type": "...", "prompt": "..."}, ...]
```

**Key Features**:
- Natural language input (Chinese/English)
- Uses prompt templates from `litrx/prompts/`
- Automatic JSON/YAML parsing from AI responses
- Code fence stripping for clean output
- Integration with GUI dialogs

### 11. Concurrent Processing System (NEW)

**Location**: `litrx/matrix_analyzer.py`, `litrx/abstract_screener.py`

High-performance parallel processing for literature analysis:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from litrx.matrix_analyzer import process_single_pdf, process_literature_matrix

# Automatic concurrent processing
results_df, mapping_df = process_literature_matrix(
    pdf_folder="./papers",
    metadata_path="metadata.csv",
    matrix_config=matrix_config,
    app_config={
        'MAX_WORKERS': 4,  # Number of concurrent threads
        'TASK_TIMEOUT_SECONDS': 600,  # Timeout per task
        'ENABLE_CACHE': True,  # Enable result caching
        'ENABLE_PROGRESS_CHECKPOINTS': True,  # Enable checkpoints
        'CHECKPOINT_INTERVAL': 5  # Save every 5 items
    },
    progress_callback=lambda current, total: print(f"{current}/{total}"),
    status_callback=lambda pdf, status: print(f"{pdf}: {status}"),
    stop_event=stop_event  # For graceful cancellation
)
```

**Key Features**:
- ThreadPoolExecutor-based parallel processing (3-4x speed improvement)
- Configurable worker count (MAX_WORKERS, default: 4)
- Thread-safe single item processing functions
- Task timeout protection (TASK_TIMEOUT_SECONDS)
- Integrated with result caching (50-90% cost reduction)
- Integrated with progress checkpoints (fault tolerance)
- Graceful cancellation via stop_event
- Real-time progress and status callbacks

**Performance Impact**:
- **First run**: 3-4x faster with concurrent processing
- **Repeated runs**: Near-instant with caching (>100x)
- **Incremental processing**: Only new items analyzed
- **API cost**: 50-90% reduction for iterative workflows

**Implementation Pattern**:
```python
def process_single_item(item_data):
    """Thread-safe processing function (no shared state mutation)."""
    # Process item and return results
    return computed_results

# Main processing with ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(process_single_item, item): item for item in items}

    for future in as_completed(futures):
        result = future.result(timeout=task_timeout)
        # Aggregate results in main thread (thread-safe)
        results.append(result)
```

**Used in**:
- `matrix_analyzer.py`: PDF literature matrix analysis
- `abstract_screener.py`: Abstract screening with verification

## Common Development Workflows

### Adding a New GUI Tab (Qt)

1. **Create tab class** in `litrx/gui/tabs_qt/my_tab.py`:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from litrx.gui.base_window_qt import BaseWindow
from litrx.i18n import t, get_i18n

class MyTab(QWidget):
    def __init__(self, parent: BaseWindow):
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout(self)
        self.title_label = QLabel(t("my_tab_title"))
        layout.addWidget(self.title_label)

        get_i18n().add_observer(self.update_language)

    def update_language(self):
        self.title_label.setText(t("my_tab_title"))
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

3. **Register tab** in `litrx/gui/main_window_qt.py`:
```python
from litrx.gui.tabs_qt.my_tab import MyTab

class LitRxApp(BaseWindow):
    def __init__(self):
        super().__init__()

        my_tab = MyTab(self)
        self.tab_widget.addTab(my_tab, t("my_tab"))
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

2. **Save in GUI** (`litrx/gui/base_window_qt.py`):
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

### Using AI-Assisted Configuration Generation (NEW)

**For Abstract Screening Modes**:

1. **Open AI Assistant**: In Abstract Screening tab, click "AI Assistant" button
2. **Describe Requirements**: Enter natural language description
   - Example: "我想筛选心理学实证研究，需要知道是否使用实验方法、样本量、是否有对照组"
3. **Generate**: Click "Generate" button
4. **Review**: Preview generated JSON configuration
5. **Apply**: Click "Apply" to save to `questions_config.json`

**Code Integration**:
```python
from litrx.ai_config_generator import AbstractModeGenerator

# Initialize generator
generator = AbstractModeGenerator(config)

# Generate mode from natural language
mode_config = generator.generate_mode(
    description="筛选实证研究，关注样本量和研究方法",
    language="zh"
)

# Result structure:
# {
#     "mode_name": "empirical_research",
#     "criteria": [
#         {"question": "是否使用实验方法？", "type": "yes_no"},
#         {"question": "是否有对照组？", "type": "yes_no"}
#     ],
#     "questions": [
#         {"question": "样本量是多少？", "type": "text"}
#     ]
# }
```

**For Matrix Dimensions**:

1. **Open AI Assistant**: In Matrix tab, click "🤖 AI 生成维度" button
2. **Describe Dimensions**: Enter what data to extract
   - Example: "提取研究方法、样本量、主要发现、研究局限"
3. **Generate**: Click "Generate" button
4. **Review & Edit**: Use graphical editor to refine dimensions
5. **Save**: Save to YAML configuration file

**Code Integration**:
```python
from litrx.ai_config_generator import MatrixDimensionGenerator

# Initialize generator
generator = MatrixDimensionGenerator(config)

# Generate dimensions
dimensions = generator.generate_dimensions(
    description="提取研究方法、样本量、主要发现",
    language="zh"
)

# Result structure:
# [
#     {
#         "name": "research_method",
#         "display_name": "研究方法",
#         "type": "single_choice",
#         "prompt": "识别研究采用的方法",
#         "options": ["实验", "问卷", "访谈", "其他"]
#     },
#     {
#         "name": "sample_size",
#         "display_name": "样本量",
#         "type": "number",
#         "prompt": "提取样本量数值"
#     }
# ]
```

### Implementing Caching for Performance

To add caching to a new analysis module:

```python
from litrx.cache import ResultCache

class MyAnalyzer:
    def __init__(self, config: dict, enable_cache: bool = True):
        self.config = config
        self.client = AIClient(config)
        self.cache = ResultCache() if enable_cache else None

    def analyze_item(self, title: str, abstract: str) -> dict:
        # Check cache first
        if self.cache:
            cached = self.cache.get(title=title, abstract=abstract)
            if cached:
                logger.info(f"Cache hit for: {title[:50]}...")
                return cached

        # Make API call
        result = self.client.request(
            messages=[{"role": "user", "content": f"Analyze: {abstract}"}]
        )

        # Store in cache
        if self.cache:
            self.cache.set(
                title=title,
                abstract=abstract,
                result=result,
                metadata={"analysis_type": "my_analysis"}
            )

        return result
```

### Implementing Progress Checkpoints

For long-running batch operations:

```python
from litrx.progress_manager import ProgressManager

def batch_analysis(input_csv: str, output_csv: str):
    # Load data
    df = pd.read_csv(input_csv)

    # Initialize progress manager
    pm = ProgressManager(output_csv)

    # Try to resume from checkpoint
    checkpoint = pm.load_checkpoint()
    if checkpoint:
        df = checkpoint["df"]
        start_index = checkpoint["last_index"] + 1
        logger.info(f"Resuming from index {start_index}")
    else:
        start_index = 0

    # Process items
    for idx in range(start_index, len(df)):
        # Analyze item
        df.loc[idx, "result"] = analyze(df.loc[idx])

        # Save checkpoint every 5 items
        if (idx + 1) % 5 == 0:
            pm.save_checkpoint(
                df=df,
                last_index=idx,
                metadata={"total": len(df), "timestamp": datetime.now().isoformat()}
            )
            logger.info(f"Checkpoint saved at index {idx}")

    # Final save
    df.to_csv(output_csv, index=False)
    pm.cleanup()  # Remove checkpoint files
```

### Implementing Concurrent Processing (NEW)

For high-performance batch operations with parallel processing:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from litrx.cache import ResultCache
from litrx.progress_manager import ProgressManager

def process_item_concurrent(
    item_data: dict,
    client: AIClient,
    cache: ResultCache
) -> dict:
    """Thread-safe processing function (no shared state mutation).

    This function can be safely called from multiple threads.
    """
    title = item_data['title']
    abstract = item_data['abstract']

    # Check cache (thread-safe)
    if cache:
        cached = cache.get(title=title, abstract=abstract)
        if cached:
            return cached

    # Process item
    result = client.request(
        messages=[{"role": "user", "content": f"Analyze: {abstract}"}]
    )

    # Cache result (thread-safe)
    if cache:
        cache.set(title=title, abstract=abstract, result=result)

    return result

def batch_analysis_concurrent(items: list, output_csv: str, config: dict):
    """Batch analysis with concurrent processing, caching, and checkpoints."""
    # Initialize components
    client = AIClient(config)
    cache = ResultCache() if config.get('ENABLE_CACHE', True) else None
    pm = ProgressManager(output_csv) if config.get('ENABLE_PROGRESS_CHECKPOINTS', True) else None

    # Configuration
    max_workers = config.get('MAX_WORKERS', 4)
    task_timeout = config.get('TASK_TIMEOUT_SECONDS', 600)
    checkpoint_interval = config.get('CHECKPOINT_INTERVAL', 5)

    # Load checkpoint if available
    start_index = 0
    results = []
    if pm:
        checkpoint = pm.load_checkpoint()
        if checkpoint:
            results = checkpoint['df'].to_dict('records')
            start_index = checkpoint['last_index'] + 1
            logger.info(f"Resuming from index {start_index}")

    # Process items concurrently
    items_to_process = [(i, item) for i, item in enumerate(items) if i >= start_index]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_item_concurrent, item, client, cache): (i, item)
            for i, item in items_to_process
        }

        # Process results as they complete
        for future in as_completed(futures, timeout=None):
            try:
                # Get result with timeout
                result = future.result(timeout=task_timeout)
                results.append(result)

                idx, _ = futures[future]

                # Save checkpoint periodically (main thread only - thread-safe)
                if pm and (len(results) % checkpoint_interval == 0):
                    checkpoint_df = pd.DataFrame(results)
                    pm.save_checkpoint(
                        df=checkpoint_df,
                        last_index=idx,
                        metadata={'total': len(items)}
                    )
                    logger.info(f"Checkpoint saved: {len(results)}/{len(items)}")

            except TimeoutError:
                logger.error(f"Task timed out after {task_timeout}s")
            except Exception as e:
                logger.error(f"Task failed: {e}")

    # Save final results
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)

    if pm:
        pm.cleanup()

    logger.info(f"Completed: {len(results)}/{len(items)} items processed")
```

**Key Points for Concurrent Processing**:
- Use thread-safe functions that don't mutate shared state
- Aggregate results in main thread only
- Integrate caching for cost savings
- Integrate checkpoints for fault tolerance
- Configure worker count based on workload (I/O-bound: 4-8, CPU-bound: CPU count)
- Set appropriate timeouts to handle stuck tasks

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
- `AIClient(config)`: Create AI client (auto-detects service)
- `client.request(messages=[...])`: Make AI request
- `ResultCache()`: Initialize result cache
- `ProgressManager(output_path)`: Initialize progress manager
- `CancellableTask()`: Create cancellable task
- `KeyManager()`: Manage secure API keys
- `get_logger(__name__)`: Get configured logger
- `resource_path(*parts)`: Get PyInstaller-compatible resource path

## Critical Implementation Details

### AI Assistant Dialogs (NEW)

**Location**: `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py` and `ai_matrix_assistant_qt.py`

The AI assistant dialogs use **lazy initialization** to prevent crashes when API keys are not configured:

**Pattern**:
```python
class AIModeAssistantDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self._generator = None  # ✅ NOT initialized in __init__

    def _generate_config(self):
        """Called when user clicks Generate button"""
        try:
            # Lazy initialization - only create when needed
            if self._generator is None:
                self._generator = AbstractModeGenerator(self.config)

            result = self._generator.generate_mode(description, language)
            # Show result
        except APIKeyMissingError as e:
            # Show user-friendly error dialog
            QMessageBox.critical(self, "错误", str(e))
```

**Why This Matters**:
- **Old behavior**: Creating `AIClient` in `__init__` would crash if API key missing
- **New behavior**: Client created only when user clicks "Generate", with proper error handling
- **User experience**: Dialog opens successfully, shows helpful error message if key missing

**Testing**: See `TEST_AI_ASSISTANTS.md` for comprehensive testing guide

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

**Implementation**: `litrx/gui/base_window_qt.py`

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

### Threading Model (GUI - Qt)

Prefer emitting Qt signals from worker threads and handle them in main thread slots; avoid updating widgets directly from threads.
```python
from PyQt6.QtCore import pyqtSignal

class CsvTab(QWidget):
    update_progress = pyqtSignal(float)
    def __init__(self, parent):
        super().__init__()
        self.update_progress.connect(lambda v: self.progress_bar.setValue(int(v)))

    def start(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        # ... work ...
        self.update_progress.emit(50.0)
```

Critical: update widgets only in the main thread (via signals/slots).

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

### Issue: AI Dialog Crashes on Open

**Problem**: AI assistant dialogs crash immediately when opened without API key

**Solution**: Use lazy initialization pattern:
```python
class MyAIDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self._generator = None  # Don't initialize here!

    def _on_generate_click(self):
        try:
            if self._generator is None:
                self._generator = MyGenerator(self.config)
            result = self._generator.generate(...)
        except APIKeyMissingError as e:
            QMessageBox.critical(self, "错误", str(e))
```

**Reference**: See `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py:62-85`

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
5. **Use custom exceptions**: Import from `litrx.exceptions` for consistent error handling
6. **Add logging**: Use `get_logger(__name__)` for trackable operations
7. **Implement caching**: Use `ResultCache` for AI operations to reduce costs
8. **Save progress**: Use `ProgressManager` for long operations with checkpoint support
9. **Enable cancellation**: Use `CancellableTask` for user-cancellable operations
10. **Document in code**: Add docstrings and comments for complex logic
11. **Handle lazy initialization**: For AI-related dialogs, initialize clients only when needed
12. **Use constants**: Import from `litrx.constants` instead of magic numbers

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
| `litrx/config_factory.py` | Configuration factory patterns |
| `litrx/i18n.py` | Internationalization system |
| `litrx/ai_client.py` | AI provider wrapper |
| `litrx/ai_config_generator.py` | AI-assisted config generation |
| `litrx/cache.py` | Result caching system |
| `litrx/progress_manager.py` | Atomic checkpoint management |
| `litrx/task_manager.py` | Cancellable task management |
| `litrx/key_manager.py` | Secure API key storage |
| `litrx/exceptions.py` | Custom exception hierarchy |
| `litrx/constants.py` | Project-wide constants |
| `litrx/utils.py` | Shared utility functions |
| `litrx/logging_config.py` | Logging configuration |
| `litrx/resources.py` | Resource path helper |
| `litrx/gui/base_window_qt.py` | GUI base class with shared controls (PyQt6) |
| `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py` | AI assistant for screening modes |
| `litrx/gui/dialogs_qt/ai_matrix_assistant_qt.py` | AI assistant for matrix dimensions |
| `litrx/csv_analyzer.py` | CSV relevance scoring |
| `litrx/abstract_screener.py` | Abstract screening with verification |
| `litrx/matrix_analyzer.py` | Literature matrix analysis |
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
client = AIClient(config)  # Auto-detects service from config
response = client.request(messages=[{"role": "user", "content": "..."}])

# Caching
from litrx.cache import ResultCache
cache = ResultCache()
result = cache.get(title="...", abstract="...")

# Progress Management
from litrx.progress_manager import ProgressManager
pm = ProgressManager("output.csv")
pm.save_checkpoint(df, last_index=100)

# Task Cancellation
from litrx.task_manager import CancellableTask
task = CancellableTask()
task.cancel()  # Call from cancel button

# Secure Keys
from litrx.key_manager import KeyManager
km = KeyManager()
km.set_key("openai_api_key", "sk-...")

# Exceptions
from litrx.exceptions import APIKeyMissingError, APIRequestError
try:
    client = AIClient(config)
except APIKeyMissingError as e:
    show_error(str(e))

# Logging
from litrx.logging_config import get_logger
logger = get_logger(__name__)
logger.info("Processing started")

# Resources (PyInstaller-compatible)
from litrx.resources import resource_path
config_path = resource_path("configs", "config.yaml")

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
| **Performance Optimization** | | |
| `MAX_WORKERS` | 1-16 (default: 4) | Number of concurrent workers for parallel processing |
| `TASK_TIMEOUT_SECONDS` | 60-3600 (default: 600) | Timeout per task in seconds |
| `ENABLE_CACHE` | true, false (default: true) | Enable result caching to avoid redundant API calls |
| `CACHE_TTL_DAYS` | 1-365 (default: 30) | Cache time-to-live in days |
| `ENABLE_PROGRESS_CHECKPOINTS` | true, false (default: true) | Enable automatic progress checkpoints |
| `CHECKPOINT_INTERVAL` | 1-100 (default: 5) | Save checkpoint every N items |

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
- **AI-Assisted Config Design**: `docs/AI_ASSISTED_CONFIG_DESIGN.md`
- **AI-Assisted Config Implementation**: `docs/AI_ASSISTED_CONFIG_IMPLEMENTATION_PLAN.md`
- **GPT-5 Model Guide**: `docs/GPT5_GUIDE.md`
- **AI Assistant Testing**: `TEST_AI_ASSISTANTS.md`
- **User Documentation**: `README.md` (English), `Chinese_README.md`
- **Example Test**: `tests/test_abstract_verification.py`
- **AI Dialog Test Script**: `test_ai_dialogs.py`

## Changelog

### Version 0.2.0 (Current - November 2024)
**Major Features**:
- 🤖 **AI-Assisted Configuration**: Generate screening modes and matrix dimensions from natural language
  - `ai_mode_assistant_qt.py` - Natural language to screening mode
  - `ai_matrix_assistant_qt.py` - Natural language to matrix dimensions
  - Prompt templates in `litrx/prompts/`
- ⚡ **Concurrent Processing**: High-performance parallel processing for literature analysis
  - ThreadPoolExecutor-based parallel processing (3-4x speed improvement)
  - Configurable worker count (MAX_WORKERS, default: 4)
  - Thread-safe processing functions (`process_single_pdf`, `compute_single_article_results`)
  - Task timeout protection (TASK_TIMEOUT_SECONDS)
  - Integrated with caching and checkpoints for optimal performance
  - Graceful cancellation support via stop_event
- 💾 **Result Caching**: Intelligent caching system to reduce API costs
  - SHA256-based cache keys
  - Configurable TTL (default 30 days)
  - Stored in `~/.litrx/cache/`
  - Integrated with matrix analyzer (50-90% cost reduction)
- 📊 **Progress Management**: Atomic checkpoints with automatic recovery
  - File locking to prevent corruption
  - Automatic .bak backups
  - Resume capability after crashes
  - Integrated with concurrent processing
- 🔐 **Secure Key Management**: Optional keyring integration
  - macOS Keychain, Windows Credential Manager, Linux Secret Service
  - Fallback to config files
- ⚙️ **Enhanced Architecture**:
  - Custom exception hierarchy with user-friendly messages
  - Centralized logging with rotation
  - Cancellable task management
  - Project-wide constants
  - Utility functions for common patterns
  - PyInstaller resource path helper
- 🎨 **UI Improvements**:
  - Enhanced dimension editor (v2) with graphical interface
  - Lazy initialization for dialogs (prevents crashes)
  - Better error handling and user feedback

**Infrastructure**:
- New dependencies: `keyring`, `pydantic>=2.0`, `filelock>=3.12.0`
- ~7000+ LOC (up from ~4000)
- Comprehensive documentation for AI-assisted features

### Version 0.1.0 (Initial Release)
- CSV relevance analysis
- Abstract screening with verification
- Literature matrix analysis
- PDF screening (LEGACY)
- Bilingual GUI (Chinese/English)
- Multi-provider AI support (OpenAI, SiliconFlow)

### Known Limitations
- Minimal test coverage (~5%)
- No LICENSE file
- Uses threading instead of async/await (works well for I/O-bound API calls)
- PDF screener superseded by matrix analyzer
- AI assistant dialogs require API key configuration

### Future Enhancements
- Complete test coverage (target: 80%+)
- Consider async/await as alternative to threading (optional optimization)
- Configuration schema validation with pydantic
- Plugin system for custom screening modes
- Advanced caching strategies (cache warming, cache sharing)
- Customizable export templates
- Dynamic worker scaling based on system resources
- Integration with more AI providers
- Desktop notifications for long-running tasks
- Distributed processing across multiple machines

---

**For AI Assistants**: This document is maintained to help you understand and work effectively with this codebase. When in doubt, refer to the architecture patterns, follow existing code conventions, and prioritize user experience (bilingual support, error handling, progress preservation). Happy coding!
