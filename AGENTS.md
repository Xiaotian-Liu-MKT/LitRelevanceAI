# AGENTS

## Project Overview
- **Name:** LitRelevanceAI (`litrx` package)
- **Purpose:** AI-assisted toolkit that assesses how closely academic papers align with a research topic, offering CSV analysis, abstract screening, PDF screening, and a unified GUI interface.
- **Core Logic:** Central configuration (`litrx.config`) merges `.env`, YAML/JSON files, and CLI flags. `AIClient` (`litrx.ai_client`) wraps LiteLLM to send requests to OpenAI or Gemini.

## Project Structure
```
.
├── configs/               # Default YAML/JSON configs and question templates
│   ├── config.yaml        # Base API/model settings
│   └── questions/         # YAML templates for csv/abstract/pdf modules
├── litrx/                 # Python package
│   ├── cli.py             # Command-line entry point with csv/abstract/pdf subcommands
│   ├── ai_client.py       # AI client abstraction over LiteLLM
│   ├── config.py          # Environment and config loading utilities
│   ├── csv_analyzer.py    # Scores Scopus CSV exports for relevance
│   ├── abstract_screener.py # Applies yes/no criteria and open questions to abstracts
│   ├── pdf_screener.py    # Converts PDFs to text and evaluates against criteria
│   └── gui/               # Tkinter GUI modules
├── README.md / Chinese_README.md
└── questions_config.json  # Example JSON question set
```

## Coding Guidelines
- Follow **PEP 8** and keep imports grouped as: standard library, third‑party, then local modules.
- Use `snake_case` for variables/functions and `UPPER_CASE` for constants.
- Write concise docstrings for public functions and classes.
- Prefer `rg` for code search.
- Use shared utilities:
  - `litrx.config` for configuration loading.
  - `litrx.ai_client` for all model requests.
- Keep both `README.md` and `Chinese_README.md` updated when CLI or packaging changes occur.

## Installation & Run
1. Install Python ≥3.8.
2. Install dependencies and project:
   ```bash
   python -m pip install -e .
   ```
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` or `GEMINI_API_KEY`.
4. Verify CLI loads:
   ```bash
   python -m litrx --help
   ```

## Testing & Validation
- Run the CLI help check above to ensure entry points work.
- Execute unit tests before committing:
  ```bash
  pytest
  ```

## Collaboration & Compliance
- Work directly on the default branch; avoid creating new branches.
- Use clear commit messages in the form `type: short description` (e.g., `docs: update AGENTS guide`).
- Each PR should describe the change, testing performed, and any relevant configuration updates.
- Ensure the working tree is clean (`git status`) before pushing.

## Special Notes
- **API Keys:** Never commit secrets. Use `.env` or environment variables.
- **Performance:** `API_REQUEST_DELAY` in configs throttles requests to avoid rate limits.
- **Compatibility:** Stick to Python ≥3.8 and listed dependencies in `pyproject.toml`.

## Examples
- Analyze CSV relevance:
  ```bash
  litrx csv
  ```
- Run abstract screening with GUI:
  ```bash
  litrx abstract --gui
  ```
- Screen PDFs with a custom config:
  ```bash
  litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
  ```

## FAQ
- **Q:** How do I add new screening questions?
  **A:** Edit the YAML files under `configs/questions/` or provide a JSON file like `questions_config.json`.
- **Q:** Which AI services are supported?
  **A:** OpenAI and Gemini; set `AI_SERVICE` and `MODEL_NAME` in `config.yaml` or via CLI.
- **Q:** Tests show “no tests ran”. Is that expected?
  **A:** Yes, the repository currently has no test files. Add tests under a `tests/` directory as needed.

