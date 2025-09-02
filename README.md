# LitRelevanceAI

An AI-assisted toolkit that evaluates how well academic papers match your research topic. The project now ships as the `litrx` package with a unified command-line interface for CSV analysis, abstract screening, and PDF screening.

[中文说明](Chinese_README.md)

## Features

- **CSV relevance analysis** – `litrx csv` reads Scopus exports and scores each paper from 0–100 while explaining the connection to your research question. The GUI tab displays results in a sortable table, allows double-clicking to view full analyses, and can export the DataFrame.
- **Configurable abstract screening** – `litrx abstract` applies yes/no criteria and open questions defined per mode in `questions_config.json`. Each AI answer is rechecked against the source text and written to a matching `<column>_verified` field. In the GUI, a dropdown selects the mode, an **Add Mode** button creates new presets, the **Edit Questions** dialog modifies questions, a read-only log shows model summaries, a **Stop** button cancels processing, and export controls save the DataFrame to CSV or Excel.
- **PDF screening** – `litrx pdf` converts papers to text before sending them to the model, checks custom criteria and detailed questions, and saves structured results. The GUI tab lists selected PDFs with matched metadata and processing status, lets you set the research question, criteria, and output type, supports a metadata-only precheck, and can open the result folder when done.
- **Modular tabbed GUI** – `python run_gui.py` (or `python -m litrx --gui`) launches an application with dedicated tabs for CSV analysis, abstract screening, and PDF screening. The script auto-installs missing dependencies before starting.
- **Flexible model support** – A settings dropdown lets you switch between OpenAI and Gemini. The API key field updates to match the chosen provider and remembers previously entered keys, while model names and temperature remain customizable in the scripts.
- **Unified configuration** – `.env` values merge with JSON or YAML config files, and command-line options override the resulting `DEFAULT_CONFIG`.
- **Automatic saving** – Interim and final results are written to CSV/XLSX files with timestamps so you never lose progress.

## Installation

1. Install Python 3.7 or later.
2. Clone this repository and install the package:
   ```bash
   python -m pip install -e .
   ```
   The `-e` flag is optional; omit it to perform a standard install.
3. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` or `GEMINI_API_KEY`.

## Quick Start

1. Export search results from Scopus in CSV format with titles and abstracts.
2. Run the relevance analyzer:
   ```bash
   litrx csv
   ```
   (or `python -m litrx csv` if the `litrx` command is unavailable)
   For a graphical interface, run:
   ```bash
   python run_gui.py
   ```
   The first run may take a moment while required packages are installed automatically.
3. Follow the prompts to choose API provider, enter your research topic, and supply the CSV path. In the GUI, switching providers updates the API key field and restores any previously saved key. Results are saved beside the input file.

## Configuration

All commands merge `.env` values with an optional JSON or YAML file passed via `--config`, producing a `DEFAULT_CONFIG` that command-line flags can override. Default settings and question templates live under `configs/`.

When running the GUI, a **Save Config** button writes the current `AI_SERVICE`, `MODEL_NAME`, `API_BASE` and provider-specific API keys to `~/.litrx_gui.yaml`. Switching the service dropdown repopulates the key field with any previously saved value. On startup the application loads `configs/config.yaml`, the saved file, and `.env` in order of increasing priority (`~/.litrx_gui.yaml` < `.env` < runtime input), so your saved preferences populate the interface automatically.

The base defaults for these values live in `configs/config.yaml`; edit this file if you need to change the starting GUI settings before saving.

## Advanced Tools

- **Abstract screening**
  ```bash
  litrx abstract            # command-line mode
  litrx abstract --gui      # graphical mode
  ```
  Manage modes in `questions_config.json` or use the GUI's **Add Mode** and **Edit Questions** dialogs to customise prompts and output columns. The resulting DataFrame includes `<column>` for each question and `<column>_verified` to show whether the AI's answer is supported by the title or abstract.
- **PDF screening**
  ```bash
  litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
  ```
  The JSON or YAML config specifies research questions, screening criteria and output type. In the GUI, you can also supply an optional metadata file, run a metadata-only precheck without model calls, and open the result folder when processing completes. Question templates default to the YAML files in `configs/questions/`.

## Customisation Tips

- Modify default model names or temperature values at the top of the scripts.
- Adjust the prompts in `csv_analyzer.py`, question sets in `questions_config.json` for abstract screening, or YAML files in `configs/questions/` for other workflows to collect different information.
- Use `.env` or supply a config file to set API keys and other defaults.

## License

This project is released under the [MIT License](LICENSE).
