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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
from .cache import ResultCache
from .constants import TITLE_SIMILARITY_THRESHOLD, FUZZY_MATCH_MIN_SCORE
from .exceptions import FileProcessingError
from .i18n import t
from .logging_config import get_logger
from .progress_manager import ProgressManager
from .utils import AIResponseParser
from .resources import resource_path
from .token_tracker import TokenUsageTracker


load_env_file()
logger = get_logger(__name__)


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

    # Performance optimization
    "MAX_WORKERS": 4,  # Number of concurrent workers for parallel processing
    "TASK_TIMEOUT_SECONDS": 600,  # Timeout per PDF (10 minutes default)
    "ENABLE_CACHE": True,  # Enable result caching to avoid redundant API calls
    "CACHE_TTL_DAYS": 30,  # Cache time-to-live in days
    "ENABLE_PROGRESS_CHECKPOINTS": True,  # Enable automatic progress checkpoints
    "CHECKPOINT_INTERVAL": 5,  # Save checkpoint every N PDFs
}


def load_matrix_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load matrix dimension configuration from YAML file."""
    if not config_path:
        config_path = resource_path("configs", "matrix", "default.yaml")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load module configuration."""
    default_cfg = resource_path("configs", "config.yaml")
    return base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)


def load_prompts() -> Dict[str, Any]:
    """Load prompt templates from prompts_config.json.

    Returns:
        Dictionary containing matrix analysis prompt templates
    """
    prompts_path = resource_path("prompts_config.json")
    try:
        import json
        with prompts_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matrix_analysis", {})
    except Exception as e:
        logger.warning(f"Failed to load matrix prompts: {e}")
        return {}


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
    token_tracker: Optional[TokenUsageTracker] = None,
    cache: Optional[ResultCache] = None,
) -> str:
    """Convert a PDF to text, send with the prompt and return raw model text.

    Args:
        pdf_path: Path to PDF file
        prompt: Analysis prompt
        client: AI client
        token_tracker: Optional token usage tracker
        cache: Optional result cache

    Returns:
        AI response text
    """
    pdf_text = extract_pdf_text(pdf_path)
    pdf_filename = os.path.basename(pdf_path)

    # Try to get cached result
    if cache:
        # Use first 1000 chars of PDF text as abstract for cache key
        pdf_preview = pdf_text[:1000] if len(pdf_text) > 1000 else pdf_text
        cached_result = cache.get(
            title=pdf_filename,
            abstract=pdf_preview,
            questions=prompt[:500]  # Use first 500 chars of prompt
        )
        if cached_result:
            logger.info(f"Cache hit for {pdf_filename}")
            return cached_result.get("content", "")

    messages = [
        {
            "role": "user",
            "content": f"{prompt}\n\n文献内容：\n\n{pdf_text}",
        }
    ]

    response = client.request(messages)

    # Track token usage
    if token_tracker and 'token_usage' in response:
        token_tracker.add_usage(response['token_usage'])

    try:
        content = response["choices"][0]["message"]["content"]

        # Cache the result
        if cache:
            pdf_preview = pdf_text[:1000] if len(pdf_text) > 1000 else pdf_text
            cache.set(
                title=pdf_filename,
                abstract=pdf_preview,
                questions=prompt[:500],
                result={"content": content},
                metadata={"pdf_path": pdf_path}
            )
            logger.debug(f"Cached result for {pdf_filename}")

        return content
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

def construct_dimension_prompt(dimension: Dict[str, Any], prompts: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """Construct prompt for a single dimension using templates and i18n.

    Args:
        dimension: Dimension configuration dictionary
        prompts: Optional prompt templates (loaded from prompts_config.json)

    Returns:
        Tuple of (json_key, prompt_instruction)
    """
    if prompts is None:
        prompts = load_prompts()

    dim_type = dimension['type']
    key = dimension['key']
    question = dimension['question']

    # Get template for this dimension type
    templates = prompts.get('dimension_prompts', {})
    template = templates.get(dim_type, '"{key}": "{question}"')

    if dim_type == 'text':
        instruction = template.format(key=key, question=question)

    elif dim_type == 'yes_no':
        instruction = template.format(
            key=key,
            question=question,
            answer_instruction=t('matrix_answer_instruction')
        )

    elif dim_type == 'single_choice':
        options = dimension.get('options', [])
        options_str = '、'.join([f"'{opt}'" for opt in options])
        instruction = template.format(
            key=key,
            question=question,
            select_instruction=t('matrix_select_instruction'),
            options=options_str
        )

    elif dim_type == 'multiple_choice':
        options = dimension.get('options', [])
        options_str = '、'.join([f"'{opt}'" for opt in options])
        instruction = template.format(
            key=key,
            question=question,
            multi_select_instruction=t('matrix_multi_select_instruction'),
            options=options_str
        )

    elif dim_type == 'number':
        unit = dimension.get('unit', '')
        unit_instruction = t('matrix_unit_instruction', unit=unit) if unit else ''
        instruction = template.format(
            key=key,
            question=question,
            number_instruction=t('matrix_number_instruction'),
            unit_instruction=unit_instruction,
            na_instruction=t('matrix_na_instruction')
        )

    elif dim_type == 'rating':
        scale = dimension.get('scale', 5)
        scale_desc = dimension.get('scale_description', f'1-{scale}分')
        instruction = template.format(
            key=key,
            question=question,
            rating_instruction=t('matrix_rating_instruction', scale=scale, scale_description=scale_desc)
        )

    elif dim_type == 'list':
        separator = dimension.get('separator', '; ')
        instruction = template.format(
            key=key,
            question=question,
            list_instruction=t('matrix_list_instruction', separator=separator.strip())
        )

    else:
        # Fallback for unknown types
        instruction = template.format(key=key, question=question)

    return key, instruction


def construct_ai_prompt(
    dimensions: List[Dict[str, Any]],
    prompts: Optional[Dict[str, Any]] = None
) -> str:
    """Construct the complete AI prompt from matrix configuration using templates and i18n.

    Args:
        dimensions: List of dimension configuration dictionaries
        prompts: Optional prompt templates (loaded from prompts_config.json)

    Returns:
        Complete formatted prompt string
    """
    if prompts is None:
        prompts = load_prompts()

    # Build dimension instructions
    dimension_prompts = []
    for dim in dimensions:
        _, instruction = construct_dimension_prompt(dim, prompts)
        dimension_prompts.append(f'    {instruction}')

    dimensions_str = ',\n'.join(dimension_prompts)

    # Get main prompt template
    main_template = prompts.get('main_prompt', '{instruction_header}\n\n{json_format_instruction}\n\n{{\n{dimensions_str}\n}}\n\n{important_notes}')

    # Build prompt components using i18n
    instruction_header = t('matrix_read_instruction')
    json_format_instruction = t('matrix_format_instruction')
    important_notes = '\n'.join([
        t('matrix_note1'),
        t('matrix_note2'),
        t('matrix_note3'),
        t('matrix_note4'),
        t('matrix_note5')
    ])

    # Construct full prompt
    return main_template.format(
        instruction_header=instruction_header,
        json_format_instruction=json_format_instruction,
        dimensions_str=dimensions_str,
        important_notes=important_notes,
        read_instruction=instruction_header,
        format_instruction=json_format_instruction,
        note1=t('matrix_note1'),
        note2=t('matrix_note2'),
        note3=t('matrix_note3'),
        note4=t('matrix_note4'),
        note5=t('matrix_note5')
    )


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
        logger.error(f"JSON解析错误: {e}")
        # Keep default "解析失败" values

    return result


# ---------------------------------------------------------------------------
# Single PDF Processing (Thread-Safe)
# ---------------------------------------------------------------------------

def process_single_pdf(
    pdf_path: str,
    pdf_filename: str,
    base_prompt: str,
    dimensions: List[Dict[str, Any]],
    client: AIClient,
    token_tracker: Optional[TokenUsageTracker] = None,
    cache: Optional[ResultCache] = None,
    metadata_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process a single PDF file (thread-safe).

    Args:
        pdf_path: Full path to PDF file
        pdf_filename: PDF filename
        base_prompt: Analysis prompt
        dimensions: List of dimension configurations
        client: AI client instance
        token_tracker: Optional token usage tracker
        cache: Optional result cache
        metadata_row: Optional metadata dictionary for this PDF

    Returns:
        Dictionary containing analysis results for all dimensions
    """
    try:
        # Get AI analysis (with caching support)
        raw_response = get_ai_response(pdf_path, base_prompt, client, token_tracker, cache)
        parsed = parse_ai_response(raw_response, dimensions)

        # Build result row
        row = {'PDF_File': pdf_filename}

        # Add matched metadata if available
        if metadata_row:
            for key, value in metadata_row.items():
                if key != 'PDF_File':  # Avoid duplicate
                    row[key] = value

        # Add dimension analysis results
        for dim in dimensions:
            key = dim['key']
            col_name = dim.get('column_name', key)
            row[col_name] = parsed.get(key, "缺失")

        return row

    except Exception as e:
        logger.error(f"处理 {pdf_filename} 时出错: {e}")
        return {
            'PDF_File': pdf_filename,
            'Error': str(e)
        }


# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------

def process_literature_matrix(
    pdf_folder: str,
    metadata_path: Optional[str],
    matrix_config: Dict[str, Any],
    app_config: Dict[str, Any],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    status_callback: Optional[Callable[[str, str], None]] = None,
    stop_event: Optional[Any] = None,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Main processing function for literature matrix analysis with concurrent processing.

    Args:
        pdf_folder: Path to folder containing PDF files
        metadata_path: Optional path to metadata CSV/XLSX file
        matrix_config: Matrix configuration dict (from YAML)
        app_config: Application configuration dict
        progress_callback: Optional callback(current, total) for progress updates
        status_callback: Optional callback(pdf_name, status) for status updates
        stop_event: Optional threading.Event to stop processing

    Returns:
        Tuple of (results_df, mapping_df)
        - results_df: Final combined results
        - mapping_df: PDF to metadata mapping (if metadata provided)
    """
    # Initialize AI client and token tracker
    client = AIClient(app_config)
    token_tracker = TokenUsageTracker()

    # Initialize cache if enabled
    cache = None
    if app_config.get('ENABLE_CACHE', True):
        cache_ttl = app_config.get('CACHE_TTL_DAYS', 30)
        cache = ResultCache(ttl_days=cache_ttl)
        logger.info(f"Result caching enabled (TTL: {cache_ttl} days)")

    # Get PDF files
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        raise ValueError("在指定文件夹中未找到PDF文件")

    total_files = len(pdf_files)

    # Load metadata if provided
    metadata_df = None
    mapping_df = None
    metadata_dict = {}  # PDF filename -> metadata dict
    if metadata_path:
        try:
            if metadata_path.lower().endswith('.csv'):
                metadata_df = pd.read_csv(metadata_path, encoding='utf-8-sig')
            else:
                metadata_df = pd.read_excel(metadata_path)

            # Build metadata mapping
            matching_config = matrix_config.get('metadata_matching', {})
            mapping_df = build_pdf_metadata_mapping(pdf_files, metadata_df, matching_config)

            # Create lookup dict for quick access
            for _, row in mapping_df.iterrows():
                pdf_name = row['PDF_File']
                metadata_dict[pdf_name] = row.to_dict()

        except Exception as e:
            logger.error(f"元数据加载失败: {e}")
            metadata_df = None

    # Get dimensions and construct prompt
    dimensions = matrix_config.get('dimensions', [])
    base_prompt = construct_ai_prompt(dimensions)

    # Initialize progress manager if enabled
    progress_manager = None
    start_index = 0
    results_list = []

    if app_config.get('ENABLE_PROGRESS_CHECKPOINTS', True):
        # Create temporary output path for checkpoint
        folder_name = os.path.basename(os.path.normpath(pdf_folder))
        suffix = app_config.get('OUTPUT_FILE_SUFFIX', '_literature_matrix')
        temp_output = os.path.join(pdf_folder, f"{folder_name}{suffix}_temp.csv")

        progress_manager = ProgressManager(temp_output)

        # Try to load checkpoint
        checkpoint = progress_manager.load_checkpoint()
        if checkpoint:
            results_df_checkpoint = checkpoint.get('df')
            start_index = checkpoint.get('last_index', -1) + 1
            if results_df_checkpoint is not None and start_index > 0:
                results_list = results_df_checkpoint.to_dict('records')
                logger.info(f"从检查点恢复，已完成 {start_index}/{total_files} 个PDF")

    # Configuration for concurrent processing
    max_workers = app_config.get('MAX_WORKERS', 4)
    task_timeout = app_config.get('TASK_TIMEOUT_SECONDS', 600)
    checkpoint_interval = app_config.get('CHECKPOINT_INTERVAL', 5)

    logger.info(f"开始并发处理 {total_files} 个PDF文件 (工作线程数: {max_workers})")

    # Process PDFs concurrently
    completed_count = start_index
    failed_count = 0

    def process_pdf_wrapper(pdf_info):
        """Wrapper for processing a single PDF (for thread pool)."""
        idx, pdf = pdf_info

        # Check cancellation
        if stop_event and stop_event.is_set():
            logger.debug(f"PDF {pdf} 跳过 (已取消)")
            return idx, None

        if status_callback:
            status_callback(pdf, "处理中")

        full_path = os.path.join(pdf_folder, pdf)
        metadata_row = metadata_dict.get(pdf)

        # Process PDF (thread-safe)
        result = process_single_pdf(
            full_path, pdf, base_prompt, dimensions,
            client, token_tracker, cache, metadata_row
        )

        # Add delay to avoid rate limiting
        delay = app_config.get('API_REQUEST_DELAY', 1)
        if delay > 0:
            time.sleep(delay)

        return idx, result

    # Only process PDFs starting from start_index
    pdfs_to_process = [(i, pdf) for i, pdf in enumerate(pdf_files) if i >= start_index]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_pdf_wrapper, pdf_info): pdf_info[1]
            for pdf_info in pdfs_to_process
        }

        # Process completed tasks as they finish
        for future in as_completed(futures, timeout=None):
            # Check cancellation
            if stop_event and stop_event.is_set():
                logger.warning("分析已被用户取消 - 在当前批次后停止")
                for pending_future in futures:
                    pending_future.cancel()
                break

            try:
                # Get result with timeout
                idx, result = future.result(timeout=task_timeout)
                completed_count += 1

                if result is not None:
                    results_list.append(result)

                    # Status callback
                    if status_callback:
                        pdf_name = result.get('PDF_File', 'unknown')
                        if 'Error' in result:
                            status_callback(pdf_name, f"错误: {result['Error']}")
                            failed_count += 1
                        else:
                            status_callback(pdf_name, "完成")
                else:
                    failed_count += 1

                # Progress callback
                if progress_callback:
                    progress_callback(completed_count, total_files)

                # Save checkpoint periodically
                if progress_manager and (completed_count % checkpoint_interval == 0):
                    checkpoint_df = pd.DataFrame(results_list)
                    progress_manager.save_checkpoint(
                        df=checkpoint_df,
                        last_index=idx,
                        metadata={'completed': completed_count, 'total': total_files}
                    )
                    logger.info(f"检查点已保存 (进度: {completed_count}/{total_files})")

            except TimeoutError:
                failed_count += 1
                pdf_name = futures[future]
                logger.error(f"PDF {pdf_name} 处理超时 (超过 {task_timeout}秒)")
                if status_callback:
                    status_callback(pdf_name, "超时")

            except Exception as e:
                failed_count += 1
                pdf_name = futures.get(future, "unknown")
                logger.error(f"处理PDF {pdf_name} 时发生意外错误: {e}", exc_info=True)
                if status_callback:
                    status_callback(pdf_name, f"错误: {str(e)}")

    # Create final DataFrame
    results_df = pd.DataFrame(results_list) if results_list else pd.DataFrame()

    # Clean up checkpoint if processing completed successfully
    if progress_manager and not (stop_event and stop_event.is_set()):
        progress_manager.cleanup()
        logger.info("处理完成，已清理检查点文件")

    # Summary logging
    logger.info(f"批量分析完成: {completed_count}/{total_files} 已处理, {failed_count} 失败")

    # Log token usage statistics
    token_summary = token_tracker.get_summary()
    logger.info(f"\nToken 使用统计:")
    logger.info(f"  API 调用次数: {token_summary['call_count']}")
    logger.info(f"  {token_summary['summary_text']}")
    logger.info(f"  百万级统计: Input={token_summary['input_M']:.3f}M, Output={token_summary['output_M']:.3f}M, Total={token_summary['total_M']:.3f}M")
    if token_summary['call_count'] > 0:
        logger.info(f"  平均每次调用: {token_summary['avg_tokens_per_call']:.0f} tokens")

    if stop_event and stop_event.is_set():
        raise KeyboardInterrupt("分析已被用户停止")

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
        raise FileProcessingError(
            f"PDF文件夹不存在: {args.pdf_folder}",
            help_text="请检查路径是否正确，或使用绝对路径。"
        )

    # Process
    logger.info("开始处理文献矩阵分析...")
    logger.info(f"PDF文件夹: {args.pdf_folder}")
    if args.metadata_file:
        logger.info(f"元数据文件: {args.metadata_file}")

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

        logger.info(f"\n✓ 处理完成！结果已保存到: {output_path}")

        if mapping_df is not None:
            matched_count = (mapping_df['Match_Status'] != 'not_matched').sum()
            logger.info(f"✓ 元数据匹配: {matched_count}/{len(mapping_df)} 个PDF成功匹配")

    except Exception as e:
        logger.error(f"\n✗ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise the exception for the caller to handle


if __name__ == '__main__':
    main()
