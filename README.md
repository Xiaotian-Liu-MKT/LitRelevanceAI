# LitRelevanceAI

An AI-assisted toolkit that evaluates how well academic papers match your research topic. The project now ships as the `litrx` package with a unified command-line interface for CSV analysis, abstract screening, and PDF screening.

[中文说明](Chinese_README.md)

## Features

- **CSV relevance analysis** – `litrx csv` reads Scopus exports and scores each paper from 0–100 while explaining the connection to your research question.
- **Configurable abstract screening** – `litrx abstract` applies yes/no criteria and open questions defined in `questions_config.json`. Add `--gui` to launch a minimal Tkinter interface.
- **PDF screening** – `litrx pdf` sends full papers to the model, checks custom criteria and detailed questions, and saves structured results.
- **Flexible model support** – Choose between OpenAI or Gemini APIs, with model names and temperature easily customized in the scripts.
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
3. Follow the prompts to choose API provider, enter your research topic, and supply the CSV path. Results are saved beside the input file.

## Advanced Tools

- **Abstract screening**
  ```bash
  litrx abstract            # command-line mode
  litrx abstract --gui      # graphical mode
  ```
  Edit `questions_config.json` to change screening questions or column names.
- **PDF screening**
  ```bash
  litrx pdf --config path/to/config.json --pdf-folder path/to/pdfs
  ```
  The JSON config specifies research questions, screening criteria and output type.

## Customisation Tips

- Modify default model names or temperature values at the top of the scripts.
- Adjust the prompts in `csv_analyzer.py` or question sets in `questions_config.json` to collect different information.
- Use `.env` or edit the scripts directly to set API keys.

## License

This project is released under the [MIT License](LICENSE).
