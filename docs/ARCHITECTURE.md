# LitRelevanceAI Architecture

## Overview

LitRelevanceAI is a literature analysis tool that uses AI to assist researchers in screening and analyzing academic papers. The application supports multiple AI providers (OpenAI, Google Gemini, and SiliconFlow) and provides both CLI and GUI interfaces.

## Project Structure

```
LitRelevanceAI/
├── litrx/                      # Main package
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # Entry point for `python -m litrx`
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # Configuration management
│   ├── i18n.py                 # Internationalization support
│   ├── ai_client.py            # AI service wrapper (LiteLLM)
│   ├── csv_analyzer.py         # CSV relevance analysis
│   ├── abstract_screener.py    # Abstract/title screening
│   ├── pdf_screener.py         # PDF document screening
│   └── gui/                    # GUI components
│       ├── base_window.py      # Base window with shared controls
│       ├── main_window.py      # Main application window
│       └── tabs/               # Feature tabs
│           ├── csv_tab.py      # CSV analysis tab
│           ├── abstract_tab.py # Abstract screening tab
│           └── pdf_tab.py      # PDF screening tab
├── configs/                    # Configuration files
│   ├── config.yaml             # Default AI service configuration
│   └── questions/              # Question templates
│       ├── abstract.yaml
│       ├── csv.yaml
│       └── pdf.yaml
├── tests/                      # Unit tests
├── docs/                       # Documentation
└── run_gui.py                  # GUI launcher script
```

## Key Components

### 1. Internationalization (i18n)

**Location:** `litrx/i18n.py`

The i18n module provides language support for Chinese and English. It uses a simple translation dictionary pattern with an observer pattern for dynamic UI updates.

**Features:**
- Translation dictionary for zh (Chinese) and en (English)
- Global i18n instance accessible via `get_i18n()`
- Shorthand function `t(key)` for translations
- Observer pattern to notify UI components when language changes
- Persistent language preference stored in configuration

**Usage Example:**
```python
from litrx.i18n import get_i18n, t

# Get translation
title = t("app_title")  # Returns translated text based on current language

# Change language
i18n = get_i18n()
i18n.current_language = "en"  # Switch to English

# Register observer for language changes
def on_language_change():
    update_ui()

i18n.add_observer(on_language_change)
```

### 2. Configuration Management

**Location:** `litrx/config.py`

Handles cascading configuration from multiple sources:
1. Default configuration (`config.yaml`)
2. User-persisted configuration (`~/.litrx_gui.yaml`)
3. Environment variables (highest priority)
4. Runtime parameters

**Configuration Keys:**
- `AI_SERVICE`: "openai", "gemini", or "siliconflow"
- `MODEL_NAME`: Model identifier
- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SILICONFLOW_API_KEY`: API credentials
- `API_BASE`: Custom API endpoint (optional)
- `LANGUAGE`: UI language preference ("zh" or "en")

### 3. AI Client

**Location:** `litrx/ai_client.py`

Wraps LiteLLM to provide a unified interface for multiple AI providers.

**Supported Providers:**
- OpenAI (GPT-4, GPT-4o, etc.)
- Google Gemini (gemini-1.5-pro, etc.)
- SiliconFlow (various models)

### 4. GUI Architecture

**Base Window Pattern:**

The GUI uses a base window pattern where `BaseWindow` provides common functionality:
- Configuration controls (AI service, API key, model)
- Language selector
- Prompt settings editor
- Configuration persistence
- Notebook (tab) container

**Tab Pattern:**

Each feature is implemented as a separate tab class:
- `CsvTab`: CSV relevance analysis
- `AbstractTab`: Abstract screening with verification
- `PdfTab`: PDF document screening

**Language Update Flow:**

1. User selects new language from dropdown
2. `BaseWindow.on_language_change()` updates i18n instance
3. i18n notifies all observers via `_notify_observers()`
4. `BaseWindow._on_language_changed()` updates base UI elements
5. `LitRxApp._on_language_changed()` (override) updates tab labels
6. Individual tabs update their UI via `update_language()` method (if implemented)

## Design Patterns

### 1. Observer Pattern (Language Changes)

The i18n system uses the observer pattern to notify UI components when the language changes. This allows for dynamic UI updates without tight coupling.

### 2. Template Method (Base Window)

`BaseWindow` provides template methods that subclasses can override:
- `_on_language_changed()`: Called when language changes
- `build_config()`: Build configuration dictionary

### 3. Dependency Injection (Tabs)

Tabs receive the parent `BaseWindow` instance in their constructor, allowing them to access shared resources like configuration and file dialogs.

## Best Practices

### Adding New Translations

1. Add translation keys to both "zh" and "en" dictionaries in `litrx/i18n.py`
2. Use `t(key)` function to access translations in code
3. Store references to UI widgets that need updating
4. Implement `update_language()` method in tabs if needed

### Adding New Configuration Keys

1. Add default value to `DEFAULT_CONFIG` in `litrx/config.py`
2. Update `save_config()` in `base_window.py` to persist the key
3. Update `build_config()` to include the key in runtime config

### Adding New Features

1. Create a new tab class in `litrx/gui/tabs/`
2. Add tab instantiation in `LitRxApp.__init__()`
3. Add translation keys for the tab
4. Implement core logic in a separate module (e.g., `csv_analyzer.py`)

## Configuration Files

### questions_config.json

Defines screening modes with customizable questions:
- `weekly_screening`: Quick analysis with yes/no questions
- `detailed_analysis`: In-depth analysis with open-ended questions
- Custom modes can be added via GUI

### prompts_config.json

Contains AI prompt templates for different analysis types:
- `csv_analysis.main_prompt`: CSV relevance scoring
- `abstract_screening.detailed_prompt`: Detailed abstract analysis
- `abstract_screening.quick_prompt`: Quick weekly screening
- `abstract_screening.verification_prompt`: Answer verification
- `pdf_screening.main_prompt`: PDF document analysis

All prompts are editable via the GUI prompt settings dialog.

## Testing

Tests are located in the `tests/` directory:
- `test_abstract_verification.py`: Tests for abstract verification workflow

Run tests with:
```bash
pytest tests/
```

## Future Enhancements

1. **Complete Tab Internationalization**: Add `update_language()` methods to all tabs
2. **Configuration Validation**: Add schema validation for config files
3. **Plugin System**: Allow users to add custom screening modes
4. **Batch Processing**: Parallel processing for large datasets
5. **Result Caching**: Cache AI responses to reduce API costs
6. **Export Templates**: Customizable export formats
