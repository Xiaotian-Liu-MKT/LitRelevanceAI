# AGENTS

## Updating this Document
- Keep this guide in sync with the codebase.
- Revise sections when project structure, commands, or dependencies change.
- After editing, rerun installation and tests to ensure instructions remain valid.

## Project Overview
LitRelevanceAI is an AI-assisted toolkit for evaluating how well academic papers match a research topic. The `litrx` package offers:
- **CSV relevance analysis** – scores Scopus exports from 0–100 with model-generated explanations.
- **Abstract screening** – applies configurable yes/no criteria and open questions to titles and abstracts. Modes are loaded from `questions_config.json` so weekly and custom presets can be edited in the GUI.
- **PDF screening** – converts PDFs to text and checks them against research questions and detailed criteria.
- **Modular GUI** – a Tkinter application with dedicated tabs for CSV analysis, abstract screening, and PDF screening.

## Repository Structure
- `litrx/` – core package
  - `__main__.py` – `python -m litrx` entry point
  - `cli.py` – dispatches `csv`, `abstract`, and `pdf` subcommands
  - `csv_analyzer.py` – relevance scoring for Scopus CSV exports
  - `abstract_screener.py` – title/abstract screening with configurable questions
  - `pdf_screener.py` – folder-based PDF screening and metadata matching
  - `ai_client.py` – LiteLLM wrapper for OpenAI/Gemini
  - `config.py` – merges `.env`, YAML/JSON config, and CLI flags into `DEFAULT_CONFIG`
  - `gui/` – Tkinter GUI framework
    - `base_window.py` – shared controls and config persistence
    - `main_window.py` – registers GUI tabs
    - `tabs/` – `csv_tab.py`, `abstract_tab.py`, `pdf_tab.py`
- `configs/` – default settings and question templates
  - `config.yaml` – baseline API configuration
  - `questions/*.yaml` – prompts for CSV, abstract, and PDF workflows
- `run_gui.py` – installs missing dependencies and launches the GUI
- `questions_config.json` – mode-aware question presets for abstract screening; the GUI reads and writes to this file
- `README.md`, `Chinese_README.md` – project documentation
- `pyproject.toml`, `setup.cfg` – packaging metadata

## Coding Conventions
- Follow PEP 8 with 4-space indents and descriptive `snake_case` names.
- Group imports: standard library, third‑party, then local modules.
- Use type hints and informative error messages.
- Reuse shared utilities: `load_env_file`, `load_config`, `AIClient`, and `BaseWindow`.
- GUI configuration loads `configs/config.yaml`, then `~/.litrx_gui.yaml`, then `.env`.
- Prefer `rg` for repository searches; avoid `ls -R` or `grep -R`.
- Update both README files when CLI or packaging changes.

## Installation and Setup
1. Ensure Python ≥ 3.8.
2. Install dependencies:
   ```bash
   python -m pip install -e .
   ```
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` or `GEMINI_API_KEY`.
4. Verify the CLI:
   ```bash
   python -m litrx --help
   ```
5. Launch the GUI:
   ```bash
   python run_gui.py
   ```
   The first run installs any missing packages.

## Testing and Validation
- Always run the following before committing:
  ```bash
  python -m pip install -e .
  python -m litrx --help
  pytest
  ```
- Add unit tests for new functionality. The current suite may be empty; future tests should cover CLI and core utilities.

## Collaboration and Compliance
- Use feature branches and keep commits focused; prefix messages with `feat:`, `fix:`, `docs:`, etc.
- Submit PRs with a summary of changes, testing evidence, and any relevant issues.
- Reviewers should confirm linting, tests, and docs before merging.
- Do not commit secrets or `.env` files. Use configuration utilities instead of hard‑coding API credentials.

## Special Considerations
- **Security** – keep API keys out of source control; rely on environment variables.
- **Performance** – respect `API_REQUEST_DELAY` when batching model calls; process large datasets incrementally.
- **Compatibility** – `AIClient` abstracts OpenAI and Gemini; use cross-platform paths and avoid OS-specific assumptions.
- **GUI** – add new tabs under `litrx/gui/tabs/` and register them in `LitRxApp`.

## Examples and FAQ
### Quick CSV Analysis
```bash
litrx csv
```
### Abstract Screening with GUI
```bash
litrx abstract --gui
```
### PDF Screening
```bash
litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
```
**FAQ**
- *Why does `pytest` report "no tests ran"?* The repository currently lacks tests; add them for new features.
- *Missing GUI dependencies?* `run_gui.py` auto-installs required packages.
- *How are configurations merged?* Defaults → `~/.litrx_gui.yaml` → `.env` → command-line flags.
