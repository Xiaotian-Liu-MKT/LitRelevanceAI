# AGENTS Guidance for LitRelevanceAI

## 1. Project Overview

LitRelevanceAI is an AI‑assisted toolkit for evaluating how well academic papers match a research topic.  It provides command‑line utilities that score literature from CSV exports, apply configurable screening questions to abstracts, and perform detailed analysis of full PDFs.  Both OpenAI and Google Gemini models are supported through the LiteLLM interface, and all scripts persist results to CSV/XLSX files.

### Core Components
- **`LitRelevance.py`** – Scores titles and abstracts from Scopus CSV exports and summarises how each paper relates to the research question.
- **`abstractScreener.py`** – Applies yes/no criteria and open questions to titles/abstracts defined in `questions_config.json`.  Supports CLI and a minimal Tkinter GUI.
- **`pdfScreener.py`** – Sends full PDFs to an LLM for screening criteria and detailed questions.
- **`questions_config.json`** – Default question set used by `abstractScreener.py`.
- **`250515 revised.py`** – Legacy experimental script kept for reference.

## 2. Repository Layout
```
.
├── AGENTS.md              # this guidance file
├── README.md              # project overview and quick start
├── Chinese_README.md      # Chinese translation of README
├── LitRelevance.py        # CSV relevance analysis
├── abstractScreener.py    # abstract screening utility
├── pdfScreener.py         # PDF screening utility
├── questions_config.json  # default screening questions
├── 250515 revised.py      # legacy script
├── .env.example           # template for API keys
└── .gitignore
```

## 3. Coding Guidelines
- **Python Version:** 3.7+
- **Style:** Follow [PEP 8](https://peps.python.org/pep-0008/) with:
  - `snake_case` for functions and variables, `PascalCase` for classes, `ALL_CAPS` for constants.
  - Import order: standard library, third‑party, then local modules.
  - Use type hints and docstrings for public functions.
  - Prefer `pathlib.Path` for filesystem paths.
- **Best Practices:**
  - Avoid hard‑coding API keys; load them from environment variables or `.env`.
  - Handle large datasets carefully—save progress frequently and expose `API_REQUEST_DELAY` to throttle requests.
  - Keep functions small and testable; refactor shared code into helpers when appropriate.

## 4. Installation & Build
1. **Requirements**
   ```bash
   pip install pandas openai google-generativeai litellm tqdm openpyxl
   ```
   Tkinter is required for the GUI mode of `abstractScreener.py` and is bundled with most Python distributions.
2. **Environment Variables**
   Copy `.env.example` to `.env` and set at least one API key:
   ```env
   OPENAI_API_KEY=sk-your-key
   GEMINI_API_KEY=your-key
   API_BASE=https://api.openai.com/v1   # optional override
   ```
3. **Running Scripts**
   - CSV relevance analysis:
     ```bash
     python LitRelevance.py
     ```
   - Abstract screening (CLI / GUI):
     ```bash
     python abstractScreener.py
     python abstractScreener.py --gui
     ```
   - PDF screening:
     ```bash
     python pdfScreener.py --config path/to/config.json --pdf-folder path/to/pdfs
     ```

## 5. Testing & Validation
- The repository currently has no automated tests.  Contributors should:
  - Ensure modified scripts run without syntax errors: `python -m py_compile <script>`.
  - Manually exercise the relevant script using sample data to verify outputs.
  - Add unit tests with `pytest` where feasible when introducing new logic.

## 6. Collaboration & Compliance
- **Branching:** Develop on feature branches derived from `main`; avoid committing directly to `main`.
- **Commits:** Use conventional prefixes such as `feat:`, `fix:`, `docs:`.
- **Pull Requests:**
  - Describe the motivation and major changes.
  - Note any model- or API-related costs.
  - Confirm you executed the commands in the *Testing & Validation* section.
- **Review Checklist:**
  - Code follows guidelines and includes docstrings/type hints.
  - No secrets or API keys appear in commits.
  - Documentation and `questions_config.json` updated when behaviour changes.

## 7. Special Considerations
- **Security:** Keep API keys in `.env` or environment variables; never commit secrets.
- **Performance:** Use `API_REQUEST_DELAY` to respect rate limits.  For large datasets, take advantage of interim file saving.
- **Compatibility:** Scripts rely on network access to OpenAI or Gemini APIs; ensure keys are valid and models exist.
- **File Encodings:** CSV files are expected in UTF‑8 with BOM (`utf-8-sig`) to preserve non‑ASCII characters.

## 8. Examples & FAQ
### Example: Customising Screening Questions
`questions_config.json` snippet:
```json
{
  "weekly_screening": {
    "open_questions": [{"key": "research_area", "question": "主要研究领域?", "column_name": "研究领域"}],
    "yes_no_questions": [{"key": "empirical_study", "question": "是否为实证研究?", "column_name": "实证研究"}]
  }
}
```
### FAQ
- **Which LLM providers are supported?** OpenAI and Google Gemini.
- **How do I resume interrupted abstract screening?** The script saves progress after each record and will resume automatically.
- **The script cannot find title or abstract columns.** Ensure your CSV uses the default column names or provide alternatives in the configuration.

---
This AGENTS file offers baseline guidance.  Extend it as the project evolves.
