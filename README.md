# LitRelevanceAI

An AI-assisted toolkit that evaluates how well academic papers match your research topic. The project now ships as the `litrx` package with a unified command-line interface for CSV analysis, abstract screening, and PDF screening.

[中文说明](Chinese_README.md)

## Features

- **CSV relevance analysis** – `litrx csv` reads Scopus exports and scores each paper from 0–100 while explaining the connection to your research question. The GUI tab displays results in a sortable table, allows double-clicking to view full analyses, and can export the DataFrame.
- **Configurable abstract screening** – `litrx abstract` applies yes/no criteria and open questions defined in `configs/questions/abstract.yaml`. In the GUI, an **Edit Questions** dialog lets you adjust these prompts mid-run, a read-only log shows model summaries, a **Stop** button cancels processing, and export controls save the DataFrame to CSV or Excel.
- **PDF screening** – `litrx pdf` converts papers to text before sending them to the model, checks custom criteria and detailed questions, and saves structured results. The GUI tab lists selected PDFs with matched metadata and processing status, lets you set the research question, criteria, and output type, supports a metadata-only precheck, and can open the result folder when done.
- **Modular tabbed GUI** – `python -m litrx --gui` launches an application with dedicated tabs for CSV analysis, abstract screening, and PDF screening.
- **Flexible model support** – Choose between OpenAI or Gemini APIs, with model names and temperature easily customized in the scripts.
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
   python -m litrx --gui
   ```
3. Follow the prompts to choose API provider, enter your research topic, and supply the CSV path. Results are saved beside the input file.

## Configuration

All commands merge `.env` values with an optional JSON or YAML file passed via `--config`, producing a `DEFAULT_CONFIG` that command-line flags can override. Default settings and question templates live under `configs/`.

When running the GUI, a **Save Config** button writes the current `AI_SERVICE`, `MODEL_NAME`, `API_BASE` and API keys to `~/.litrx_gui.yaml`. On startup the application loads `configs/config.yaml`, the saved file, and `.env` in order of increasing priority (`~/.litrx_gui.yaml` < `.env` < runtime input), so your saved preferences populate the interface automatically.

The base defaults for these values live in `configs/config.yaml`; edit this file if you need to change the starting GUI settings before saving.

## Advanced Tools

- **Abstract screening**
  ```bash
  litrx abstract            # command-line mode
  litrx abstract --gui      # graphical mode
  ```
  Edit files in `configs/questions/` to change screening questions or column names.
- **PDF screening**
  ```bash
  litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
  ```
  The JSON or YAML config specifies research questions, screening criteria and output type. In the GUI, you can also supply an optional metadata file, run a metadata-only precheck without model calls, and open the result folder when processing completes. Question templates default to the YAML files in `configs/questions/`.

## Customisation Tips

- Modify default model names or temperature values at the top of the scripts.
- Adjust the prompts in `csv_analyzer.py` or question sets in `configs/questions/` to collect different information.
- Use `.env` or supply a config file to set API keys and other defaults.

## License

This project is released under the [MIT License](LICENSE).
