# LitRelevanceAI Architecture (PyQt6)

## Overview

LitRelevanceAI is an AI-assisted toolkit for screening and analyzing academic literature. It supports CLI and a modern PyQt6 GUI, with OpenAI-compatible providers (OpenAI and SiliconFlow). The codebase emphasizes modular analysis pipelines, internationalization (i18n), and robust configuration management. Packaging scripts enable click-to-run apps for non-developers.

## Project Structure

```
LitRelevanceAI/
├── litrx/
│   ├── __init__.py
│   ├── __main__.py                 # `python -m litrx` (delegates to CLI or GUI)
│   ├── cli.py                      # CLI dispatcher (csv / abstract / matrix)
│   ├── ai_client.py                # OpenAI SDK wrapper (OpenAI & SiliconFlow)
│   ├── config.py                   # Cascading configuration
│   ├── i18n.py                     # Translations + observer pattern
│   ├── resources.py                # resource_path() for frozen builds
│   ├── csv_analyzer.py             # CSV relevance analysis
│   ├── abstract_screener.py        # Title/abstract screening + verification
│   ├── matrix_analyzer.py          # Literature matrix analysis from PDFs
│   └── gui/
│       ├── base_window_qt.py       # PyQt6 base window (+ onboarding)
│       ├── main_window_qt.py       # PyQt6 main window
│       └── tabs_qt/
│           ├── csv_tab.py          # CSV analysis tab (auto-save)
│           ├── abstract_tab.py     # Abstract screening tab (auto-save)
│           └── matrix_tab.py       # Matrix analysis tab
├── configs/                        # Default YAML + question templates
├── prompts_config.json             # Prompt templates
├── questions_config.json           # Screening modes and questions
├── packaging/
│   ├── build_win.bat               # Windows PyInstaller build script
│   ├── build_mac.sh                # macOS PyInstaller build script
│   └── pyinstaller/litrx.spec      # Spec file (bundles resources)
├── docs/                           # Documentation
├── tests/                          # Unit tests (minimal)
└── run_gui.py                      # GUI launcher (PyQt6-only)
```

## Key Components

### Internationalization (i18n)

Location: `litrx/i18n.py`
- Translations in zh/en via a dictionary
- Global instance via `get_i18n()` and shorthand `t(key)`
- Observer pattern to notify UI widgets on language changes

Language change flow:
1. User selects language in GUI
2. `BaseWindow._on_language_changed()` updates base UI
3. `LitRxApp._on_language_changed()` updates tab labels
4. Tabs implement `update_language()` when needed

### Configuration Management

Location: `litrx/config.py`
Cascade order (low → high):
1. `DEFAULT_CONFIG` in code
2. `configs/config.yaml`
3. `~/.litrx_gui.yaml` (persisted GUI settings)
4. `.env`
5. Runtime/CLI flags

Common keys: `AI_SERVICE`, `MODEL_NAME`, `OPENAI_API_KEY`, `SILICONFLOW_API_KEY`, `API_BASE`, `LANGUAGE`, `ENABLE_VERIFICATION`, `OUTPUT_FILE_SUFFIX`.

### AI Client

Location: `litrx/ai_client.py`
- Uses the official OpenAI SDK; SiliconFlow via OpenAI-compatible base_url
- Model capability heuristics cached at init (e.g., GPT‑5/o* often disallow custom `temperature`)
- Request layer auto-sanitizes unsupported params and has a targeted retry without `temperature` if needed

### GUI Architecture (PyQt6)

Base window (Location: `litrx/gui/base_window_qt.py`):
- Config panel (provider, key, model, language)
- Prompt settings dialog
- First-run onboarding wizard to collect provider + API key
- Keyring integration (if available)
- `resource_path()` for bundled files in frozen builds

Tabs (Location: `litrx/gui/tabs_qt/`):
- `csv_tab.py`: CSV relevance analysis with progress and auto-save to `<name>_analyzed_<timestamp>.csv`
- `abstract_tab.py`: Abstract screening (open + yes/no) with optional verification and auto-save; supports Zotero headers (`Abstract Note`, `Short Title`)
- `matrix_tab.py`: PDF-driven matrix analysis with flexible dimensions (see `configs/matrix/`)

Signals/threads: worker threads emit signals; UI updates occur in main thread slots.

### Resource Handling

Location: `litrx/resources.py`
- `resource_path(*parts)` resolves to PyInstaller `_MEIPASS` in frozen builds, or repository root in dev.
- All modules that read resources (configs, prompts, questions) use `resource_path()`.

## Best Practices

Adding translations:
1. Add keys to both zh and en in `i18n.py`
2. Use `t(key)` in UI code
3. Register `update_language()` in tabs that have translatable widgets

Adding config keys:
1. Add defaults in `config.py` or module-level `DEFAULT_CONFIG`
2. Persist in `base_window_qt.py` if GUI-exposed

Adding features:
1. Implement logic in a dedicated module (e.g., `my_feature.py`)
2. Add a PyQt6 tab under `gui/tabs_qt/`
3. Register the tab in `main_window_qt.py`
4. Add translations in `i18n.py`

## Configuration & Templates

- `questions_config.json`: screening modes and questions (GUI can add/edit modes)
- `prompts_config.json`: prompt templates; editable via GUI
- `configs/config.yaml`: base defaults for the GUI; merged with persisted and env values

## Testing

Tests live under `tests/` (currently minimal). Run with:

```bash
pytest tests/
```

## Packaging & Distribution

Use PyInstaller for click-to-run builds:
- Windows: `packaging\build_win.bat`
- macOS: `bash packaging/build_mac.sh`

Outputs:
- Windows: `dist/LitRelevanceAI/LitRelevanceAI.exe` (ship the whole folder)
- macOS: `dist/LitRelevanceAI.app`

The spec bundles `configs/`, `questions_config.json`, `prompts_config.json`. All resource access goes through `resource_path()`.

## Notable Behaviors

- Zotero columns: title detection includes `Short Title`; abstract includes `Abstract Note`
- Auto-save: Abstract/CSV tabs auto-save results to the input folder on completion
- Temperature handling: for GPT‑5/o* families, client strips `temperature` automatically and logs once per session
