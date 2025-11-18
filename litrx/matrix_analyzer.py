"""AI-assisted Literature Matrix Analysis Tool.

This module extends the PDF screening functionality to support a flexible literature
matrix analysis with 7 question types:
- text: Open-ended text responses
- yes_no: Yes/No/Uncertain responses
- single_choice: Select one option from predefined choices
- multiple_choice: Select multiple options from predefined choices
- number: Extract numeric values
- rating: Subjective ratings (1-N scale)
- list: Extract multiple items in a list

The tool supports intelligent metadata matching with Zotero exports, allowing
seamless integration of AI analysis results with bibliographic information.

Example usage::

    python -m litrx.matrix_analyzer --pdf-folder ./papers --metadata-file zotero_export.csv

"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
import openpyxl  # noqa: F401
import pandas as pd
from tqdm import tqdm
from pypdf import PdfReader

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

from .config import (
    DEFAULT_CONFIG as BASE_CONFIG,
    load_config as base_load_config,
    load_env_file,
)
from .ai_client import AIClient
from .constants import TITLE_SIMILARITY_THRESHOLD, FUZZY_MATCH_MIN_SCORE
from .utils import AIResponseParser


load_env_file()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, object] = {
    **BASE_CONFIG,
    # Matrix configuration file path
    "MATRIX_CONFIG_PATH": "",

    # Data file configuration
    "INPUT_PDF_FOLDER_PATH": "",
    "METADATA_FILE_PATH": "",

    # Output configuration
    "OUTPUT_FILE_SUFFIX": "_literature_matrix",
    "OUTPUT_FILE_TYPE": "xlsx",

    # API configuration
    "API_REQUEST_DELAY": 1,
}


def load_matrix_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load matrix dimension configuration from YAML file."""
    if not config_path:
        config_path = Path(__file__).resolve().parent.parent / "configs" / "matrix" / "default.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load module configuration."""
    default_cfg = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    return base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# PDF Text Extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def get_ai_response(
    pdf_path: str,
    prompt: str,
    client: AIClient,
) -> str:
    """Convert a PDF to text, send with the prompt and return raw model text."""
    pdf_text = extract_pdf_text(pdf_path)

    messages = [
        {
            "role": "user",
            "content": f"{prompt}\n\n文献内容：\n\n{pdf_text}",
        }
    ]

    response = client.request(messages)
    try:
        return response["choices"][0]["message"]["content"]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Intelligent Metadata Matching
# ---------------------------------------------------------------------------

def parse_zotero_filename(filename: str) -> Dict[str, str]:
    """Parse Zotero-style filename: Author_Year_Title.pdf

    Returns dict with 'author', 'year', 'title' keys or empty dict if parsing fails.
    """
    # Remove .pdf extension
    name = filename.lower().replace('.pdf', '')

    # Common Zotero patterns:
    # - Author_Year_Title
    # - Author et al_Year_Title
    # - LastName_Year_FirstWords

    parts = name.split('_')
    if len(parts) >= 3:
        # Try to identify year (4 digits)
        year_idx = None
        for i, part in enumerate(parts):
            if re.match(r'^\d{4}$', part):
                year_idx = i
                break

        if year_idx is not None:
            return {
                'author': '_'.join(parts[:year_idx]),
                'year': parts[year_idx],
                'title': '_'.join(parts[year_idx+1:]) if year_idx+1 < len(parts) else ''
            }

    return {}


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles (0-100 scale).

    Uses rapidfuzz if available, otherwise falls back to simple substring matching.
    """
    if not title1 or not title2:
        return 0.0

    t1 = title1.lower().strip()
    t2 = title2.lower().strip()

    if fuzz:
        return fuzz.ratio(t1, t2)
    else:
        # Simple fallback: check if one is substring of the other
        if t1 in t2 or t2 in t1:
            return 80.0
        return 0.0


def match_pdf_to_metadata(
    pdf_filename: str,
    metadata_df: pd.DataFrame,
    id_columns: List[str],
    title_threshold: float = 80.0,
    enable_filename_parsing: bool = True,
) -> Tuple[Optional[int], str, float]:
    """Match a single PDF to metadata row.

    Returns:
        Tuple of (matched_index, match_type, confidence)
        - matched_index: DataFrame index of matched row, or None
        - match_type: 'doi'|'title_exact'|'title_fuzzy'|'filename_parsed'|'not_matched'
        - confidence: 0-100
    """
    pdf_lower = pdf_filename.lower()

    # Priority 1: DOI exact match
    if 'DOI' in id_columns and 'DOI' in metadata_df.columns:
        doi_series = metadata_df['DOI'].astype(str).str.lower()
        for idx, doi in doi_series.items():
            if doi and doi != 'nan' and doi in pdf_lower:
                return idx, 'doi', 100.0

    # Priority 2: Title exact substring match
    if 'Title' in id_columns and 'Title' in metadata_df.columns:
        title_series = metadata_df['Title'].astype(str).str.lower()
        for idx, title in title_series.items():
            if title and title != 'nan' and title in pdf_lower:
                return idx, 'title_exact', 95.0

    # Priority 3: Fuzzy title matching
    if 'Title' in metadata_df.columns and fuzz:
        best_match_idx = None
        best_similarity = 0.0

        for idx, title in metadata_df['Title'].items():
            if pd.notna(title):
                similarity = calculate_title_similarity(str(title), pdf_filename)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = idx

        if best_similarity >= title_threshold:
            return best_match_idx, 'title_fuzzy', best_similarity

    # Priority 4: Parse filename and match components
    if enable_filename_parsing:
        parsed = parse_zotero_filename(pdf_filename)
        if parsed:
            # Try to match by author + year
            for idx, row in metadata_df.iterrows():
                author_match = False
                year_match = False

                # Check author
                if 'Author' in metadata_df.columns and pd.notna(row.get('Author')):
                    author = str(row['Author']).lower()
                    if parsed['author'] in author or author.split()[0] in parsed['author']:
                        author_match = True

                # Check year
                if 'Year' in metadata_df.columns and pd.notna(row.get('Year')):
                    year = str(row['Year'])
                    if parsed['year'] == year:
                        year_match = True

                if author_match and year_match:
                    return idx, 'filename_parsed', 70.0

    # Priority 5: Zotero Key match
    if 'Key' in id_columns and 'Key' in metadata_df.columns:
        key_series = metadata_df['Key'].astype(str).str.lower()
        for idx, key in key_series.items():
            if key and key != 'nan' and key in pdf_lower:
                return idx, 'key', 90.0

    return None, 'not_matched', 0.0


def build_pdf_metadata_mapping(
    pdf_files: List[str],
    metadata_df: pd.DataFrame,
    matching_config: Dict[str, Any],
) -> pd.DataFrame:
    """Match PDFs to metadata rows using intelligent multi-level matching.

    Args:
        pdf_files: List of PDF filenames
        metadata_df: DataFrame containing metadata
        matching_config: Configuration dict with id_columns, thresholds, etc.

    Returns:
        DataFrame with matched metadata plus match status columns
    """
    id_columns = matching_config.get('id_columns', ['DOI', 'Title'])
    title_threshold = matching_config.get('title_similarity_threshold', TITLE_SIMILARITY_THRESHOLD)
    enable_parsing = matching_config.get('enable_filename_parsing', True)

    mapping_rows = []

    for pdf in pdf_files:
        matched_idx, match_type, confidence = match_pdf_to_metadata(
            pdf, metadata_df, id_columns, title_threshold, enable_parsing
        )

        if matched_idx is not None:
            row = metadata_df.loc[matched_idx].to_dict()
        else:
            row = {}

        row['PDF_File'] = pdf
        row['Match_Status'] = match_type
        row['Match_Confidence'] = confidence

        mapping_rows.append(row)

    return pd.DataFrame(mapping_rows)


# ---------------------------------------------------------------------------
# Prompt Construction
# ---------------------------------------------------------------------------

def construct_dimension_prompt(dimension: Dict[str, Any]) -> Tuple[str, str]:
    """Construct prompt for a single dimension.

    Returns:
        Tuple of (json_key, prompt_instruction)
    """
    dim_type = dimension['type']
    key = dimension['key']
    question = dimension['question']

    if dim_type == 'text':
        instruction = f'"{key}": "{question}"'

    elif dim_type == 'yes_no':
        instruction = f'"{key}": "{question} 请回答\'是\'、\'否\'或\'不确定\'"'

    elif dim_type == 'single_choice':
        options = dimension.get('options', [])
        options_str = '、'.join([f"'{opt}'" for opt in options])
        instruction = f'"{key}": "{question} 请从以下选项中选择一个：{options_str}"'

    elif dim_type == 'multiple_choice':
        options = dimension.get('options', [])
        options_str = '、'.join([f"'{opt}'" for opt in options])
        instruction = f'"{key}": "{question} 请从以下选项中选择所有适用的（多选），用分号分隔：{options_str}"'

    elif dim_type == 'number':
        unit = dimension.get('unit', '')
        instruction = f'"{key}": "{question} 请回答具体数值{("（单位：" + unit + "）") if unit else ""}，如无法确定请回答\'N/A\'"'

    elif dim_type == 'rating':
        scale = dimension.get('scale', 5)
        scale_desc = dimension.get('scale_description', f'1-{scale}分')
        instruction = f'"{key}": "{question} 请给出1-{scale}的评分（{scale_desc}）"'

    elif dim_type == 'list':
        separator = dimension.get('separator', '; ')
        instruction = f'"{key}": "{question} 请列出多个条目，用\'{separator.strip()}\'分隔"'

    else:
        instruction = f'"{key}": "{question}"'

    return key, instruction


def construct_ai_prompt(
    dimensions: List[Dict[str, Any]],
) -> str:
    """Construct the complete AI prompt from matrix configuration."""

    # Build dimension instructions
    dimension_prompts = []
    for dim in dimensions:
        _, instruction = construct_dimension_prompt(dim)
        dimension_prompts.append(f'    {instruction}')

    dimensions_str = ',\n'.join(dimension_prompts)

    # Construct full prompt
    prompt_template = """请仔细阅读以下文献，并根据要求进行分析。

请严格按照以下JSON格式回答所有问题（使用中文）：

{{
{dimensions_str}
}}

重要说明：
1. 请确保输出是有效的JSON格式
2. 所有问题都必须回答，如果文中未提及或无法确定，请回答"N/A"或"不确定"
3. 对于选择题，请严格从给定选项中选择
4. 对于数值题，只回答数字或"N/A"
5. 保持回答简洁但完整
"""

    return prompt_template.format(dimensions_str=dimensions_str)


# ---------------------------------------------------------------------------
# Response Parsing
# ---------------------------------------------------------------------------

def parse_ai_response(
    ai_response: str,
    dimensions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Parse AI response JSON and ensure all dimension keys exist.

    Returns dict with dimension keys mapped to their values.
    """
    result = {}

    # Initialize all keys with default values
    for dim in dimensions:
        key = dim['key']
        result[key] = "解析失败"

    # Try to parse JSON using unified parser
    try:
        data = AIResponseParser.parse_json_with_fallback(ai_response)

        # Extract values for each dimension
        for dim in dimensions:
            key = dim['key']
            if key in data:
                result[key] = data[key]
            else:
                result[key] = "缺失"

    except (json.JSONDecodeError, ValueError) as e:
        # JSON parsing failed completely
        print(f"JSON解析错误: {e}")
        # Keep default "解析失败" values

    return result


# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------

def process_literature_matrix(
    pdf_folder: str,
    metadata_path: Optional[str],
    matrix_config: Dict[str, Any],
    app_config: Dict[str, Any],
    progress_callback: Optional[callable] = None,
    status_callback: Optional[callable] = None,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Main processing function for literature matrix analysis.

    Args:
        pdf_folder: Path to folder containing PDF files
        metadata_path: Optional path to metadata CSV/XLSX file
        matrix_config: Matrix configuration dict (from YAML)
        app_config: Application configuration dict
        progress_callback: Optional callback(current, total) for progress updates
        status_callback: Optional callback(pdf_name, status) for status updates

    Returns:
        Tuple of (results_df, mapping_df)
        - results_df: Final combined results
        - mapping_df: PDF to metadata mapping (if metadata provided)
    """
    # Initialize AI client
    client = AIClient(app_config)

    # Get PDF files
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        raise ValueError("在指定文件夹中未找到PDF文件")

    total_files = len(pdf_files)

    # Load metadata if provided
    metadata_df = None
    mapping_df = None
    if metadata_path:
        try:
            if metadata_path.lower().endswith('.csv'):
                metadata_df = pd.read_csv(metadata_path, encoding='utf-8-sig')
            else:
                metadata_df = pd.read_excel(metadata_path)

            # Build metadata mapping
            matching_config = matrix_config.get('metadata_matching', {})
            mapping_df = build_pdf_metadata_mapping(pdf_files, metadata_df, matching_config)

        except Exception as e:
            print(f"元数据加载失败: {e}")
            metadata_df = None

    # Get dimensions and construct prompt
    dimensions = matrix_config.get('dimensions', [])
    base_prompt = construct_ai_prompt(dimensions)

    # Process each PDF
    results = []
    for idx, pdf in enumerate(pdf_files):
        if status_callback:
            status_callback(pdf, "处理中")

        full_path = os.path.join(pdf_folder, pdf)

        try:
            # Get AI analysis
            raw_response = get_ai_response(full_path, base_prompt, client)
            parsed = parse_ai_response(raw_response, dimensions)

            # Build result row
            row = {'PDF_File': pdf}

            # Add matched metadata if available
            if mapping_df is not None:
                matched_row = mapping_df[mapping_df['PDF_File'] == pdf]
                if not matched_row.empty:
                    for col in metadata_df.columns:
                        if col in matched_row.columns:
                            row[col] = matched_row.iloc[0][col]
                    row['Match_Status'] = matched_row.iloc[0]['Match_Status']
                    row['Match_Confidence'] = matched_row.iloc[0]['Match_Confidence']

            # Add dimension analysis results
            for dim in dimensions:
                key = dim['key']
                col_name = dim.get('column_name', key)
                row[col_name] = parsed.get(key, "缺失")

            results.append(row)

            if status_callback:
                status_callback(pdf, "完成")

        except Exception as e:
            print(f"处理 {pdf} 时出错: {e}")
            row = {'PDF_File': pdf, 'Error': str(e)}
            results.append(row)

            if status_callback:
                status_callback(pdf, f"错误: {str(e)}")

        if progress_callback:
            progress_callback(idx + 1, total_files)

        # API delay
        time.sleep(app_config.get('API_REQUEST_DELAY', 1))

    results_df = pd.DataFrame(results)
    return results_df, mapping_df


def save_results(
    results_df: pd.DataFrame,
    mapping_df: Optional[pd.DataFrame],
    output_folder: str,
    output_config: Dict[str, Any],
) -> str:
    """Save results to file.

    Returns:
        Path to the output file
    """
    folder_name = os.path.basename(os.path.normpath(output_folder))
    suffix = output_config.get('file_suffix', '_literature_matrix')
    file_type = output_config.get('file_type', 'xlsx')

    output_path = os.path.join(output_folder, f"{folder_name}{suffix}.{file_type}")

    if file_type == 'csv':
        results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    else:
        results_df.to_excel(output_path, index=False, engine='openpyxl')

    # Optionally save mapping table
    if mapping_df is not None:
        mapping_path = os.path.join(output_folder, f"{folder_name}_metadata_mapping.csv")
        mapping_df.to_csv(mapping_path, index=False, encoding='utf-8-sig')

    return output_path


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for literature matrix analysis."""
    parser = argparse.ArgumentParser(
        description="AI-assisted Literature Matrix Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python -m litrx.matrix_analyzer --pdf-folder ./papers --metadata-file zotero_export.csv
  python -m litrx.matrix_analyzer --pdf-folder ./papers --matrix-config my_matrix.yaml
        """
    )

    parser.add_argument('--pdf-folder', required=True, help='文件夹路径（包含PDF文件）')
    parser.add_argument('--metadata-file', help='元数据文件路径（CSV或XLSX）')
    parser.add_argument('--matrix-config', help='矩阵配置文件路径（YAML）')
    parser.add_argument('--app-config', help='应用配置文件路径（YAML或JSON）')

    args = parser.parse_args()

    # Load configurations
    app_config = load_config(args.app_config)
    app_config['INPUT_PDF_FOLDER_PATH'] = args.pdf_folder

    if args.metadata_file:
        app_config['METADATA_FILE_PATH'] = args.metadata_file

    matrix_config = load_matrix_config(args.matrix_config)

    # Validate inputs
    if not os.path.isdir(args.pdf_folder):
        print(f"错误：PDF文件夹不存在: {args.pdf_folder}")
        sys.exit(1)

    # Process
    print("开始处理文献矩阵分析...")
    print(f"PDF文件夹: {args.pdf_folder}")
    if args.metadata_file:
        print(f"元数据文件: {args.metadata_file}")

    try:
        results_df, mapping_df = process_literature_matrix(
            args.pdf_folder,
            args.metadata_file,
            matrix_config,
            app_config,
        )

        # Save results
        output_config = matrix_config.get('output', {})
        output_path = save_results(results_df, mapping_df, args.pdf_folder, output_config)

        print(f"\n✓ 处理完成！结果已保存到: {output_path}")

        if mapping_df is not None:
            matched_count = (mapping_df['Match_Status'] != 'not_matched').sum()
            print(f"✓ 元数据匹配: {matched_count}/{len(mapping_df)} 个PDF成功匹配")

    except Exception as e:
        print(f"\n✗ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
