# LitRelevanceAI

An AI-assisted toolkit that evaluates how well academic papers match your research topic. The project includes simple command-line tools for scoring CSV exports from Scopus, configurable screening utilities for abstracts and PDFs, and options for both OpenAI and Gemini models.

[中文说明](Chinese_README.md)

## Features

- **CSV relevance analysis** – `LitRelevance.py` reads Scopus exports and scores each paper from 0–100 while explaining the connection to your research question.
- **Configurable abstract screening** – `abstractScreener.py` applies yes/no criteria and open questions defined in `questions_config.json`. Supports resuming progress and a minimal Tkinter GUI with `--gui`.
- **PDF screening** – `pdfScreener.py` sends full papers to the model, checks custom criteria and detailed questions, and saves structured results.
- **Flexible model support** – Choose between OpenAI or Gemini APIs, with model names and temperature easily customized in the scripts.
- **Automatic saving** – Interim and final results are written to CSV/XLSX files with timestamps so you never lose progress.

## Installation

1. Install Python 3.7 or later.
2. Clone this repository and install required packages:
   ```bash
   pip install pandas openai google-generativeai litellm tqdm openpyxl
   ```
3. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` or `GEMINI_API_KEY`.

## Quick Start

1. Export search results from Scopus in CSV format with titles and abstracts.
2. Run the relevance analyzer:
   ```bash
   python LitRelevance.py
   ```
3. Follow the prompts to choose API provider, enter your research topic, and supply the CSV path. Results are saved beside the input file.

## Advanced Tools

- **Abstract screening**
  ```bash
  python abstractScreener.py            # command-line mode
  python abstractScreener.py --gui      # graphical mode
  ```
  Edit `questions_config.json` to change screening questions or column names.
- **PDF screening**
  ```bash
  python pdfScreener.py --config path/to/config.json --pdf-folder path/to/pdfs
  ```
  The JSON config specifies research questions, screening criteria and output type.

## Customisation Tips

- Modify default model names or temperature values at the top of the scripts.
- Adjust the prompts in `LitRelevance.py` or question sets in `questions_config.json` to collect different information.
- Use `.env` or edit the scripts directly to set API keys.

## License

This project is released under the [MIT License](LICENSE).
