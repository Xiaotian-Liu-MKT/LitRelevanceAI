"""AI-assisted PDF screening tool.

This module mirrors the structure of ``abstractScreener.py`` but operates on
PDF files.  Each PDF is converted to plain text and sent to the model.  It uses
LiteLLM so that either OpenAI-, Gemini-, or locally hosted OpenAI-compatible
APIs can be used transparently.  A folder of PDFs can be screened against
user-defined criteria and optional detailed-analysis questions.  When a
metadata file is supplied, the script will attempt to match PDFs to their
metadata rows via identifiers such as DOI or Title and output a mapping table
for later reuse.

The script reads configuration from ``DEFAULT_CONFIG`` which can be overridden
by providing a JSON configuration file or command line arguments.  Environment
variables may be supplied in a ``.env`` file similar to ``abstractScreener``.

Example usage::

    python pdfScreener.py --pdf-folder ./papers --metadata-file meta.xlsx

"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

import openpyxl  # noqa: F401  # needed for pandas Excel writer
import pandas as pd
from tqdm import tqdm
from pypdf import PdfReader

from .config import (
    DEFAULT_CONFIG as BASE_CONFIG,
    load_config as base_load_config,
    load_env_file,
)
from .ai_client import AIClient
from .utils import AIResponseParser


load_env_file()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


DEFAULT_CONFIG: Dict[str, object] = {
    **BASE_CONFIG,
    # Research configuration
    "RESEARCH_QUESTION": "",
    "CRITERIA": [],  # e.g. ["是否为field study"]
    "DETAILED_ANALYSIS_QUESTIONS": [],  # same structure as abstractScreener

    # Data file configuration
    "INPUT_PDF_FOLDER_PATH": "",
    "METADATA_FILE_PATH": "",  # optional CSV/XLSX containing article metadata
    "METADATA_ID_COLUMNS": ["DOI", "Title"],
    "OUTPUT_FILE_SUFFIX": "_analyzed",
    "OUTPUT_FILE_TYPE": "xlsx",  # "xlsx" or "csv"

    # Other configuration
    "API_REQUEST_DELAY": 1,
}


def load_prompts() -> Dict[str, str]:
    """Load prompt templates from prompts_config.json."""
    prompts_path = Path(__file__).resolve().parent.parent / "prompts_config.json"
    try:
        with prompts_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("pdf_screening", {})
    except Exception:
        return {}


def load_config(path: Optional[str] = None, questions_path: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load module configuration and question templates."""

    default_cfg = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    config = base_load_config(str(path or default_cfg), DEFAULT_CONFIG)

    q_path = questions_path or Path(__file__).resolve().parent.parent / "configs" / "questions" / "pdf.yaml"
    with open(q_path, 'r', encoding='utf-8') as f:
        questions = yaml.safe_load(f) or {}

    return config, questions


def get_ai_response(
    pdf_path: str,
    prompt: str,
    client: AIClient,
) -> str:
    """Convert a PDF to text, send with the prompt and return raw model text."""

    reader = PdfReader(pdf_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    messages = [
        {
            "role": "user",
            "content": f"{prompt}\n\n{pdf_text}",
        }
    ]

    response = client.request(messages)
    try:
        return response["choices"][0]["message"]["content"]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Metadata matching utilities
# ---------------------------------------------------------------------------


def load_metadata_file(path: str) -> pd.DataFrame:
    """Load metadata from CSV or XLSX."""

    if not path:
        raise ValueError("metadata path empty")
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def build_pdf_metadata_mapping(
    pdf_files: List[str],
    metadata: pd.DataFrame,
    id_columns: List[str],
) -> pd.DataFrame:
    """Match PDFs to metadata rows via identifiers (substring match)."""

    mapping_rows = []
    lower_cols = {col: metadata[col].astype(str).str.lower() for col in id_columns if col in metadata.columns}

    for pdf in pdf_files:
        name = pdf.lower()
        matched_idx = None
        for col, series in lower_cols.items():
            hits = series[series.notna() & series.apply(lambda x: x in name)]
            if not hits.empty:
                matched_idx = hits.index[0]
                break
        row = metadata.loc[matched_idx].to_dict() if matched_idx is not None else {}
        row["PDF File"] = pdf
        mapping_rows.append(row)

    return pd.DataFrame(mapping_rows)


# ---------------------------------------------------------------------------
# Prompt construction and parsing
# ---------------------------------------------------------------------------


def construct_ai_prompt_instructions(
    research_question: str,
    screening_criteria: List[str],
    detailed_questions: List[Dict[str, str]],
) -> str:
    """Construct the textual instructions for the model using template."""
    prompts = load_prompts()

    criteria_str = ",\n".join(
        [f'        "{c}": "请回答 \'是\', \'否\', 或 \'不确定\'"' for c in screening_criteria]
    )

    da_list = [f'        "{q["prompt_key"]}": "{q["question_text"]}"' for q in detailed_questions]
    da_str = ",\n".join(da_list)
    da_section = f"\n    \"detailed_analysis\": {{\n{da_str}\n    }}," if da_str else ""

    # Use template from prompts_config.json or fall back to default
    template = prompts.get("main_prompt", """请阅读所提供的文献并根据研究问题进行分析。请严格按照以下JSON格式以中文回答:
{{{da_section}
    "screening_results": {{
{criteria_str}
    }}
}}
""")

    return template.format(da_section=da_section, criteria_str=criteria_str)


def parse_ai_response_json(
    ai_json_string: str,
    criteria_list: List[str],
    detailed_questions: List[Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Parse the JSON response with fallback, ensuring all keys exist."""

    final = {"detailed_analysis": {}, "screening_results": {}}
    try:
        # Use unified parser with markdown cleaning and regex fallback
        data = AIResponseParser.parse_json_with_fallback(ai_json_string)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON解析失败: {e}")
        for q in detailed_questions:
            final["detailed_analysis"][q["prompt_key"]] = "解析失败"
        for c in criteria_list:
            final["screening_results"][c] = "解析失败"
        return final

    for q in detailed_questions:
        final["detailed_analysis"][q["prompt_key"]] = data.get("detailed_analysis", {}).get(q["prompt_key"], "缺失")
    for c in criteria_list:
        final["screening_results"][c] = data.get("screening_results", {}).get(c, "缺失")
    return final


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-assisted PDF screening")
    parser.add_argument("--config", help="Path to JSON or YAML config file", default=None)
    parser.add_argument("--pdf-folder", help="Folder containing PDFs", default=None)
    parser.add_argument("--metadata-file", help="Optional metadata CSV/XLSX", default=None)
    args = parser.parse_args()

    config, questions = load_config(args.config)
    if args.pdf_folder:
        config["INPUT_PDF_FOLDER_PATH"] = args.pdf_folder
    if args.metadata_file:
        config["METADATA_FILE_PATH"] = args.metadata_file
    client = AIClient(config)

    research_question = config.get("RESEARCH_QUESTION", "")
    yes_no = questions.get("yes_no_questions", [])
    open_q = questions.get("open_questions", [])
    criteria_list = [q["question"] for q in yes_no]
    detailed_questions = [
        {"prompt_key": q["key"], "question_text": q["question"], "df_column_name": q["column_name"]}
        for q in open_q
    ]

    pdf_folder = config.get("INPUT_PDF_FOLDER_PATH")
    if not pdf_folder or not os.path.isdir(pdf_folder):
        print("错误：未提供有效的PDF文件夹路径。")
        sys.exit(1)

    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("在指定文件夹中未找到PDF文件。")
        sys.exit(0)

    metadata_path = config.get("METADATA_FILE_PATH")
    if metadata_path:
        try:
            metadata_df = load_metadata_file(metadata_path)
            mapping_df = build_pdf_metadata_mapping(
                pdf_files, metadata_df, config.get("METADATA_ID_COLUMNS", [])
            )
            map_path = os.path.join(pdf_folder, "pdf_metadata_mapping.csv")
            mapping_df.to_csv(map_path, index=False, encoding="utf-8-sig")
            print(f"已生成PDF与元数据映射表: {map_path}")
        except Exception as e:
            print(f"元数据匹配失败: {e}")

    base_prompt = construct_ai_prompt_instructions(
        research_question, criteria_list, detailed_questions
    )

    results = []
    for pdf in tqdm(pdf_files, desc="Processing PDFs"):
        full_path = os.path.join(pdf_folder, pdf)
        raw_text = get_ai_response(full_path, base_prompt, client)
        parsed = parse_ai_response_json(raw_text, criteria_list, detailed_questions)

        row: Dict[str, object] = {"PDF文件名": pdf}
        for q in detailed_questions:
            row[q["df_column_name"]] = parsed["detailed_analysis"][q["prompt_key"]]
        for c in criteria_list:
            row[f"筛选_{c}"] = parsed["screening_results"][c]
        results.append(row)
        time.sleep(config.get("API_REQUEST_DELAY", 1))

    df = pd.DataFrame(results)
    folder_name = os.path.basename(os.path.normpath(pdf_folder))
    output_base = f"{folder_name}{config['OUTPUT_FILE_SUFFIX']}"
    output_ext = f".{config.get('OUTPUT_FILE_TYPE', 'xlsx')}"
    output_path = os.path.join(pdf_folder, f"{output_base}{output_ext}")

    if output_ext == ".csv":
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"处理完成，结果已保存到 {output_path}")
