"""AI-assisted PDF screening tool.

This module mirrors the structure of ``abstractScreener.py`` but operates on
PDF files.  It uses LiteLLM so that either OpenAI-, Gemini-, or locally hosted
OpenAI-compatible APIs can be used transparently.  A folder of PDFs can be
screened against user-defined criteria and optional detailed-analysis
questions.  When a metadata file is supplied, the script will attempt to match
PDFs to their metadata rows via identifiers such as DOI or Title and output a
mapping table for later reuse.

The script reads configuration from ``DEFAULT_CONFIG`` which can be overridden
by providing a JSON configuration file or command line arguments.  Environment
variables may be supplied in a ``.env`` file similar to ``abstractScreener``.

Example usage::

    python pdfScreener.py --pdf-folder ./papers --metadata-file meta.xlsx

"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl  # noqa: F401  # needed for pandas Excel writer
import pandas as pd
from litellm import completion
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Environment loading (shared with ``abstractScreener``)
# ---------------------------------------------------------------------------


def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from a .env file if present."""

    path = Path(env_path)
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


DEFAULT_CONFIG: Dict[str, object] = {
    # AI service configuration
    "AI_SERVICE": "openai",  # "openai" or "gemini"
    "MODEL_NAME": "gpt-4o",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "API_BASE": "",  # optional base url for local deployments

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


def load_config_from_json(path: Optional[str]) -> Dict[str, object]:
    """Load configuration from a JSON file and merge with defaults."""

    config = DEFAULT_CONFIG.copy()
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        config.update(user_cfg)
    return config


# ---------------------------------------------------------------------------
# AI initialisation and helpers
# ---------------------------------------------------------------------------


def initialize_ai(config: Dict[str, object]) -> None:
    """Validate API keys and configure environment for LiteLLM."""

    service = config.get("AI_SERVICE")
    model = config.get("MODEL_NAME")
    api_base = config.get("API_BASE") or os.getenv("API_BASE")
    if api_base:
        os.environ["OPENAI_BASE_URL"] = api_base

    if service == "openai":
        api_key = config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("错误：OpenAI API密钥未配置。")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = api_key
    elif service == "gemini":
        api_key = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("错误：Gemini API密钥未配置。")
            sys.exit(1)
        os.environ["GEMINI_API_KEY"] = api_key
    else:
        print(f"错误：无效的AI服务 '{service}'。必须是 'openai' 或 'gemini'。")
        sys.exit(1)

    print(f"LiteLLM 已使用模型 {model} 初始化 (服务: {service})。")


def get_ai_response(
    pdf_path: str,
    prompt: str,
    config: Dict[str, object],
) -> str:
    """Send a PDF and prompt to the configured model and return raw text."""

    mime_type = mimetypes.guess_type(pdf_path)[0] or "application/pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_file",
                    "input_file": {
                        "file_name": os.path.basename(pdf_path),
                        "mime_type": mime_type,
                        "data": pdf_bytes,
                    },
                },
            ],
        }
    ]

    response = completion(model=config["MODEL_NAME"], messages=messages)
    # LiteLLM returns a dict similar to OpenAI responses
    try:
        return response["choices"][0]["message"]["content"][0]["text"]
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
    """Construct the textual instructions for the model."""

    criteria_str = ",\n".join(
        [f'        "{c}": "请回答 \'是\', \'否\', 或 \'不确定\'"' for c in screening_criteria]
    )

    da_list = [f'        "{q["prompt_key"]}": "{q["question_text"]}"' for q in detailed_questions]
    da_str = ",\n".join(da_list)
    da_section = f"\n    \"detailed_analysis\": {{\n{da_str}\n    }}," if da_str else ""

    return f"""请阅读所提供的文献并根据研究问题进行分析。请严格按照以下JSON格式以中文回答：
{{{da_section}
    "screening_results": {{
{criteria_str}
    }}
}}
"""


def parse_ai_response_json(
    ai_json_string: str,
    criteria_list: List[str],
    detailed_questions: List[Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Parse the JSON response, ensuring all keys exist."""

    final = {"detailed_analysis": {}, "screening_results": {}}
    try:
        data = json.loads(ai_json_string)
    except Exception:
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
    parser.add_argument("--config", help="Path to JSON config file", default=None)
    parser.add_argument("--pdf-folder", help="Folder containing PDFs", default=None)
    parser.add_argument("--metadata-file", help="Optional metadata CSV/XLSX", default=None)
    args = parser.parse_args()

    config = load_config_from_json(args.config)
    if args.pdf_folder:
        config["INPUT_PDF_FOLDER_PATH"] = args.pdf_folder
    if args.metadata_file:
        config["METADATA_FILE_PATH"] = args.metadata_file

    initialize_ai(config)

    research_question = config.get("RESEARCH_QUESTION", "")
    criteria_list = config.get("CRITERIA", [])
    detailed_questions = config.get("DETAILED_ANALYSIS_QUESTIONS", [])

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
        raw_text = get_ai_response(full_path, base_prompt, config)
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
