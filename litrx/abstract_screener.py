"""Abstract screening module with AI-assisted literature analysis.

This module provides functionality for screening academic papers based on
configurable questions and criteria, with optional verification workflow.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import openpyxl
import pandas as pd
import yaml

from .config import (
    DEFAULT_CONFIG as BASE_CONFIG,
    load_env_file,
    load_config as base_load_config,
)
from .ai_client import AIClient
from .constants import DEFAULT_MAX_WORKERS, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from .logging_config import get_logger
from .prompt_builder import PromptBuilder
from .utils import AIResponseParser
from .resources import resource_path
from .exceptions import ConfigurationError, FileProcessingError, ValidationError
from .token_tracker import TokenUsageTracker


load_env_file()
logger = get_logger(__name__)


# Custom exceptions for better error handling
class ColumnNotFoundError(Exception):
    """Raised when required columns are not found in the data."""
    pass


class InvalidFileFormatError(Exception):
    """Raised when file format is not supported."""
    pass


# Configuration defaults
DEFAULT_CONFIG = {
    **BASE_CONFIG,
    # Research configuration
    'RESEARCH_QUESTION': '',
    'GENERAL_SCREENING_MODE': True,

    # File configuration
    'INPUT_FILE_PATH': '',
    'OUTPUT_FILE_SUFFIX': '_analyzed',

    # Processing configuration
    'API_REQUEST_DELAY': 1,
    'ENABLE_VERIFICATION': True,
    'MAX_WORKERS': DEFAULT_MAX_WORKERS,
    'TITLE_COLUMN_VARIANTS': ['Title', 'Article Title', '标题', '文献标题', 'Short Title'],
    'ABSTRACT_COLUMN_VARIANTS': ['Abstract', 'Abstract Note', '摘要', 'Summary'],
}


def load_mode_questions(mode: str) -> Dict[str, Any]:
    """Load questions for a given screening mode.

    First tries to load from unified config (configs/abstract/{mode}.yaml),
    then falls back to legacy format (questions_config.json).

    Args:
        mode: Screening mode name

    Returns:
        Dictionary with open_questions and yes_no_questions
    """
    # Try new unified config format
    unified_path = resource_path("configs", "abstract", f"{mode}.yaml")
    if unified_path.exists():
        try:
            with unified_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return {
                    "open_questions": data.get("open_questions", []),
                    "yes_no_questions": data.get("yes_no_questions", []),
                    "prompts": data.get("prompts", {}),
                    "settings": data.get("settings", {}),
                }
        except Exception as e:
            logger.warning(f"警告: 加载统一配置失败: {e}")

    # Fall back to legacy format
    legacy_path = resource_path("questions_config.json")
    try:
        with legacy_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(mode, {"open_questions": [], "yes_no_questions": []})
    except Exception:
        return {"open_questions": [], "yes_no_questions": []}


def load_prompts() -> Dict[str, str]:
    """Load prompt templates from prompts_config.json."""
    prompts_path = resource_path("prompts_config.json")
    try:
        with prompts_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("abstract_screening", {})
    except Exception:
        return {}


def load_config(path: Optional[str] = None, mode: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load module configuration and questions for the given mode."""

    default_cfg = resource_path("configs", "config.yaml")
    config = base_load_config(str(path or default_cfg), DEFAULT_CONFIG)

    mode = mode or config.get("CONFIG_MODE", "weekly_screening")
    questions = load_mode_questions(mode)

    return config, questions

def get_file_path_from_config(config):
    """Get and validate file path from configuration.

    Args:
        config: Configuration dictionary containing INPUT_FILE_PATH

    Returns:
        str: Validated file path

    Raises:
        ConfigurationError: If file path is not configured or invalid
        FileProcessingError: If file doesn't exist or has unsupported format
    """
    file_path = config.get('INPUT_FILE_PATH', '')

    if not file_path or file_path == 'your_input_file.xlsx':
        raise ConfigurationError(
            "输入文件路径未配置",
            help_text=(
                "请通过以下方式之一配置 INPUT_FILE_PATH：\n"
                "1. 在GUI中选择文件\n"
                "2. 在 configs/config.yaml 中设置\n"
                "3. 在 .env 文件中添加：INPUT_FILE_PATH=/path/to/file.csv\n\n"
                "示例配置：\n"
                "INPUT_FILE_PATH: /home/user/papers.csv"
            )
        )

    if not os.path.exists(file_path):
        raise FileProcessingError(
            f"配置的文件路径不存在: {file_path}\n\n"
            f"请检查：\n"
            f"1. 路径拼写是否正确\n"
            f"2. 文件是否已被移动或删除\n"
            f"3. 是否有文件访问权限"
        )

    if not (file_path.endswith('.csv') or file_path.endswith('.xlsx') or file_path.endswith('.xls')):
        raise FileProcessingError(
            f"不支持的文件格式: {file_path}\n\n"
            f"支持的格式：.csv, .xlsx, .xls\n"
            f"当前文件扩展名：{os.path.splitext(file_path)[1]}"
        )

    return file_path

def load_and_validate_data(file_path, config, title_column=None, abstract_column=None):
    """Load and validate data from CSV or Excel file.

    Args:
        file_path: Path to the data file
        config: Configuration dictionary
        title_column: Optional explicit title column name
        abstract_column: Optional explicit abstract column name

    Returns:
        Tuple of (DataFrame, title_column_name, abstract_column_name)

    Raises:
        InvalidFileFormatError: If file format is not supported
        ColumnNotFoundError: If required columns cannot be found
        IOError: If file cannot be read
    """
    # Validate file format
    if not (file_path.endswith('.csv') or file_path.endswith('.xlsx')):
        raise InvalidFileFormatError(
            f"不支持的文件格式。请使用 CSV 或 Excel 文件。\n"
            f"当前文件: {file_path}"
        )

    # Load data
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise IOError(f"读取文件失败: {file_path}\n错误: {e}")

    # Auto-detect or validate title column
    title_variants = config.get('TITLE_COLUMN_VARIANTS', DEFAULT_CONFIG.get('TITLE_COLUMN_VARIANTS', []))
    if title_column:
        if title_column not in df.columns:
            raise ColumnNotFoundError(
                f"指定的标题列 '{title_column}' 不存在。\n"
                f"可用列: {', '.join(df.columns)}"
            )
    else:
        for col_name_variant in title_variants:
            if col_name_variant in df.columns:
                title_column = col_name_variant
                break
        if not title_column:
            raise ColumnNotFoundError(
                f"无法自动识别标题列。\n"
                f"尝试过的列名: {', '.join(title_variants)}\n"
                f"可用列: {', '.join(df.columns)}\n"
                f"请在GUI中手动选择标题列。"
            )

    # Auto-detect or validate abstract column
    abstract_variants = config.get('ABSTRACT_COLUMN_VARIANTS', DEFAULT_CONFIG.get('ABSTRACT_COLUMN_VARIANTS', []))
    if abstract_column:
        if abstract_column not in df.columns:
            raise ColumnNotFoundError(
                f"指定的摘要列 '{abstract_column}' 不存在。\n"
                f"可用列: {', '.join(df.columns)}"
            )
    else:
        for col_name_variant in abstract_variants:
            if col_name_variant in df.columns:
                abstract_column = col_name_variant
                break
        if not abstract_column:
            raise ColumnNotFoundError(
                f"无法自动识别摘要列。\n"
                f"尝试过的列名: {', '.join(abstract_variants)}\n"
                f"可用列: {', '.join(df.columns)}\n"
                f"请在GUI中手动选择摘要列。"
            )

    logger.info(f"成功识别列 - 标题: '{title_column}', 摘要: '{abstract_column}'")
    return df, title_column, abstract_column

def prepare_dataframe(df, open_questions, yes_no_questions):
    for q in open_questions:
        df[q['column_name']] = ''
        df[f"{q['column_name']}_verified"] = ''
    for q in yes_no_questions:
        df[q['column_name']] = ''
        df[f"{q['column_name']}_verified"] = ''
    return df

def construct_ai_prompt(title, abstract, research_question, screening_criteria, detailed_analysis_questions, prompts=None):
    """Construct detailed analysis prompt using PromptBuilder."""
    if prompts is None:
        prompts = load_prompts()

    builder = PromptBuilder(prompts)
    return builder.build_screening_prompt(
        title=title,
        abstract=abstract,
        research_question=research_question,
        criteria=screening_criteria,
        detailed_questions=detailed_analysis_questions
    )


def construct_flexible_prompt(title, abstract, config, open_questions, yes_no_questions):
    """Construct prompt using PromptBuilder."""
    prompts = load_prompts()
    builder = PromptBuilder(prompts)

    if config.get('GENERAL_SCREENING_MODE') or not config.get('RESEARCH_QUESTION'):
        return builder.build_flexible_prompt(
            title=title,
            abstract=abstract,
            open_questions=open_questions,
            yes_no_questions=yes_no_questions,
            general_mode=True
        )
    else:
        screening_criteria = [q['question'] for q in yes_no_questions]
        detailed = [{'prompt_key': q['key'], 'question_text': q['question'], 'df_column_name': q['column_name']} for q in open_questions]
        return construct_ai_prompt(title, abstract, config['RESEARCH_QUESTION'], screening_criteria, detailed, prompts)

def get_ai_response_with_retry(prompt_text, client, config, open_questions, yes_no_questions, max_retries=3, token_tracker=None):
    def build_error_response(msg):
        data: Dict[str, Dict[str, str]] = {"quick_analysis": {}, "screening_results": {}}
        for q in open_questions:
            data["quick_analysis"][q['key']] = msg
        for q in yes_no_questions:
            data["screening_results"][q['key']] = msg
        return json.dumps(data)

    for attempt in range(max_retries):
        try:
            req_kwargs = {"response_format": {"type": "json_object"}}
            # Only include temperature if model supports it
            if getattr(client, "supports_temperature", True):
                req_kwargs["temperature"] = 0.3
            response = client.request(messages=[{"role": "user", "content": prompt_text}], **req_kwargs)

            # Track token usage
            if token_tracker and 'token_usage' in response:
                token_tracker.add_usage(response['token_usage'])

            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return build_error_response(f"重试{max_retries}次后仍失败: {e}")


def parse_ai_response_json(ai_json_string, open_questions, yes_no_questions):
    """Parse an AI JSON string into quick analysis and screening results.

    The model is expected to return a structure containing ``quick_analysis`` and
    ``screening_results`` sections.  When verifying previous answers, the model
    may wrap these sections inside ``verification_results``.  Missing entries are
    populated with a default "AI未提供此项信息或解析失败" message to simplify
    downstream logic.

    Parameters
    ----------
    ai_json_string:
        Raw JSON string returned by the model.
    open_questions / yes_no_questions:
        Question metadata used to align model keys with dataframe columns.

    Returns
    -------
    dict
        Normalised dictionary with ``quick_analysis`` and ``screening_results``
        subsections.
    """

    final_structure = {
        "quick_analysis": {q['key']: "AI未提供此项信息或解析失败" for q in open_questions},
        "screening_results": {q['key']: "AI未提供此项信息或解析失败" for q in yes_no_questions}
    }

    try:
        if not ai_json_string or not isinstance(ai_json_string, str):
            logger.warning("AI响应为空或格式不正确")
            return final_structure

        # Use unified parser with fallback (though json_object format should prevent this)
        data = AIResponseParser.parse_json_with_fallback(ai_json_string)

        if "verification_results" in data:
            data = data.get("verification_results", {})

        qa = data.get("quick_analysis", {})
        sr = data.get("screening_results", {})
        for q in open_questions:
            final_structure["quick_analysis"][q['key']] = qa.get(q['key'], final_structure["quick_analysis"][q['key']])
        for q in yes_no_questions:
            final_structure["screening_results"][q['key']] = sr.get(q['key'], final_structure["screening_results"][q['key']])

        return final_structure

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON解析错误: {e}。AI原始响应: '{ai_json_string[:500]}...'")
    except Exception as e:
        logger.error(f"解析AI响应时发生未知错误: {e}", exc_info=True)

    return final_structure


def verify_ai_response(title, abstract, initial_json, client, open_questions, yes_no_questions, token_tracker=None):
    """Verify that AI answers are supported by the supplied title and abstract.

    The function sends the model a summary of its previous answers and asks it
    to confirm whether each one is backed by the source text.  The model should
    respond with "是", "否" or "不确定" for each question.  The parsed results are
    returned in the same structure as ``parse_ai_response_json``.
    """
    prompts = load_prompts()

    verification_data = {
        "quick_analysis": {
            q["key"]: {
                "question": q["question"],
                "answer": initial_json.get("quick_analysis", {}).get(q["key"], "")
            }
            for q in open_questions
        },
        "screening_results": {
            q["key"]: {
                "question": q["question"],
                "answer": initial_json.get("screening_results", {}).get(q["key"], "")
            }
            for q in yes_no_questions
        },
    }

    open_keys = ", ".join([f'\"{q["key"]}\": \"\"' for q in open_questions])
    yes_no_keys = ", ".join([f'\"{q["key"]}\": \"\"' for q in yes_no_questions])

    # Use template from prompts_config.json or fall back to default
    template = prompts.get("verification_prompt", """请根据以下文献标题和摘要,核对AI之前的回答是否与文献内容一致。
文献标题:{title}
文献摘要:{abstract}

问题与AI初始回答如下:
{verification_data}

请判断每个回答是否得到标题或摘要支持。如支持回答\"是\",不支持回答\"否\",无法判断回答\"不确定\"。请按如下JSON格式返回:
{{
    \"quick_analysis\": {{{open_keys}}},
    \"screening_results\": {{{yes_no_keys}}}
}}""")

    prompt = template.format(
        title=title,
        abstract=abstract,
        verification_data=json.dumps(verification_data, ensure_ascii=False, indent=2),
        open_keys=open_keys,
        yes_no_keys=yes_no_keys
    )

    try:
        req_kwargs = {"response_format": {"type": "json_object"}}
        if getattr(client, "supports_temperature", True):
            req_kwargs["temperature"] = 0
        response = client.request(messages=[{"role": "user", "content": prompt}], **req_kwargs)

        # Track token usage
        if token_tracker and 'token_usage' in response:
            token_tracker.add_usage(response['token_usage'])

        content = response["choices"][0]["message"]["content"].strip()
        return parse_ai_response_json(content, open_questions, yes_no_questions)
    except Exception as e:
        logger.error(f"验证AI响应失败: {e}")
        return {
            "quick_analysis": {q["key"]: "验证失败" for q in open_questions},
            "screening_results": {q["key"]: "验证失败" for q in yes_no_questions},
        }


def save_progress(df, output_path, current_index):
    temp_path = output_path.replace('.', '_temp.')
    if output_path.endswith('.csv'):
        df.to_csv(temp_path, index=False, encoding='utf-8-sig')
    else:
        df.to_excel(temp_path, index=False, engine='openpyxl')
    progress_info = {
        'last_processed_index': current_index,
        'timestamp': time.time()
    }
    with open(output_path.replace('.', '_progress.json'), 'w', encoding='utf-8') as f:
        json.dump(progress_info, f)


def resume_from_progress(output_path):
    progress_file = output_path.replace('.', '_progress.json')
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        return progress.get('last_processed_index', -1) + 1
    return 0


def generate_weekly_summary(df, criteria_columns):
    summary = {
        'total_articles': len(df),
        'screening_results': {}
    }
    for col in criteria_columns:
        if col in df.columns:
            value_counts = df[col].value_counts()
            summary['screening_results'][col] = {
                '是': int(value_counts.get('是', 0)),
                '否': int(value_counts.get('否', 0)),
                '不确定': int(value_counts.get('不确定', 0))
            }
    return summary

def analyze_article(df, index, row, title_col, abstract_col, open_questions, yes_no_questions, config, client):
    """Analyze a single article (legacy function for backward compatibility)."""
    screener = AbstractScreener(config, client)
    return screener.analyze_single_article(
        df, index, row, title_col, abstract_col, open_questions, yes_no_questions
    )


# ==============================================================================
# AbstractScreener Class
# ==============================================================================

class AbstractScreener:
    """AI-assisted abstract screening with concurrent processing support.

    This class encapsulates all logic for screening academic papers based on
    configurable questions and criteria, with optional verification workflow.
    """

    def __init__(self, config: Dict[str, Any], client: Optional[AIClient] = None):
        """Initialize the screener.

        Args:
            config: Configuration dictionary
            client: Optional pre-initialized AIClient
        """
        logger.info("Initializing AbstractScreener")
        self.config = config
        self.client = client or AIClient(config)
        self.prompts = load_prompts()
        self.token_tracker = TokenUsageTracker()
        logger.debug(f"AbstractScreener initialized with max_workers={config.get('MAX_WORKERS', DEFAULT_MAX_WORKERS)}, verification={config.get('ENABLE_VERIFICATION', True)}")

    def analyze_single_article(
        self,
        df: pd.DataFrame,
        index: int,
        row: pd.Series,
        title_col: str,
        abstract_col: str,
        open_questions: List[Dict],
        yes_no_questions: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze a single article.

        DEPRECATED: This method directly mutates the DataFrame, which is not thread-safe.
        Use compute_single_article_results() for concurrent processing.

        Args:
            df: DataFrame to store results
            index: Row index in DataFrame
            row: Row data
            title_col: Title column name
            abstract_col: Abstract column name
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions

        Returns:
            Dictionary with 'initial' and 'verification' results
        """
        # Compute results without mutating DataFrame
        results = self.compute_single_article_results(
            row, title_col, abstract_col, open_questions, yes_no_questions
        )

        # Apply results to DataFrame (not thread-safe - use only in sequential processing)
        self._apply_results_to_dataframe(df, index, results, open_questions, yes_no_questions)

        return {"initial": results.get("parsed_data", {}), "verification": results.get("verification", {})}

    def compute_single_article_results(
        self,
        row: pd.Series,
        title_col: str,
        abstract_col: str,
        open_questions: List[Dict],
        yes_no_questions: List[Dict]
    ) -> Dict[str, Any]:
        """Compute analysis results for a single article without DataFrame mutation.

        This method is thread-safe and suitable for concurrent processing.

        Args:
            row: Row data
            title_col: Title column name
            abstract_col: Abstract column name
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions

        Returns:
            Dictionary with all computed values for DataFrame columns
        """
        title = str(row[title_col]) if pd.notna(row[title_col]) else "无标题"
        abstract = str(row[abstract_col]) if pd.notna(row[abstract_col]) else "无摘要"

        # Handle missing data
        if title == "无标题" and abstract == "无摘要":
            results = {"missing_data": True, "columns": {}}
            for q in open_questions:
                results["columns"][q['column_name']] = "标题和摘要均缺失"
                results["columns"][f"{q['column_name']}_verified"] = "未验证"
            for q in yes_no_questions:
                results["columns"][q['column_name']] = "无法处理"
                results["columns"][f"{q['column_name']}_verified"] = "未验证"
            return results

        # Get AI analysis
        prompt = construct_flexible_prompt(
            title, abstract, self.config, open_questions, yes_no_questions
        )
        ai_response_json_str = get_ai_response_with_retry(
            prompt, self.client, self.config, open_questions, yes_no_questions,
            token_tracker=self.token_tracker
        )
        parsed_data = parse_ai_response_json(
            ai_response_json_str, open_questions, yes_no_questions
        )

        # Prepare results dictionary
        results = {
            "parsed_data": parsed_data,
            "verification": {},
            "columns": {}
        }

        # Extract initial results
        qa = parsed_data.get('quick_analysis', {})
        for q in open_questions:
            results["columns"][q['column_name']] = qa.get(q['key'], "信息缺失")

        sr = parsed_data.get('screening_results', {})
        for q in yes_no_questions:
            results["columns"][q['column_name']] = sr.get(q['key'], "信息缺失")

        # Verification
        if self.config.get('ENABLE_VERIFICATION', True):
            verification = verify_ai_response(
                title, abstract, parsed_data, self.client, open_questions, yes_no_questions,
                token_tracker=self.token_tracker
            )
            results["verification"] = verification

            vqa = verification.get('quick_analysis', {})
            for q in open_questions:
                results["columns"][f"{q['column_name']}_verified"] = vqa.get(q['key'], "验证失败")

            vsr = verification.get('screening_results', {})
            for q in yes_no_questions:
                results["columns"][f"{q['column_name']}_verified"] = vsr.get(q['key'], "验证失败")
        else:
            for q in open_questions:
                results["columns"][f"{q['column_name']}_verified"] = '未验证'
            for q in yes_no_questions:
                results["columns"][f"{q['column_name']}_verified"] = '未验证'

        return results

    def _apply_results_to_dataframe(
        self,
        df: pd.DataFrame,
        index: int,
        results: Dict[str, Any],
        open_questions: List[Dict],
        yes_no_questions: List[Dict]
    ) -> None:
        """Apply computed results to DataFrame.

        This method is NOT thread-safe and should only be called from the main thread.

        Args:
            df: DataFrame to update
            index: Row index
            results: Results dictionary from compute_single_article_results
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions
        """
        for col_name, value in results.get("columns", {}).items():
            df.at[index, col_name] = value

    def analyze_batch_concurrent(
        self,
        df: pd.DataFrame,
        title_col: str,
        abstract_col: str,
        open_questions: List[Dict],
        yes_no_questions: List[Dict],
        progress_callback: Optional[Callable[[int, int, Optional[Dict[str, Any]]], None]] = None,
        stop_event: Optional[Any] = None
    ) -> pd.DataFrame:
        """Analyze multiple articles concurrently with improved error handling.

        This method is thread-safe: workers compute results without mutating the DataFrame,
        and the main thread applies updates sequentially.

        Features:
        - Concurrent processing with configurable workers
        - Timeout handling for individual tasks
        - Exception handling with detailed logging
        - Graceful cancellation via stop_event
        - Progress tracking with callbacks

        Args:
            df: DataFrame with articles
            title_col: Title column name
            abstract_col: Abstract column name
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions
            progress_callback: Optional callback(index, total, result)
            stop_event: Optional threading.Event to stop processing

        Returns:
            DataFrame with analysis results

        Raises:
            KeyboardInterrupt: If stop_event is set
        """
        max_workers = self.config.get('MAX_WORKERS', DEFAULT_MAX_WORKERS)
        task_timeout = self.config.get('TASK_TIMEOUT_SECONDS', 300)  # 5 minutes default
        total = len(df)
        completed_count = 0
        failed_count = 0

        logger.info(f"Starting concurrent analysis of {total} articles with {max_workers} workers")
        logger.debug(f"Open questions: {len(open_questions)}, Yes/No questions: {len(yes_no_questions)}")
        logger.debug(f"Task timeout: {task_timeout}s per article")

        def process_article(index_row_tuple):
            """Process a single article (for thread pool) - thread-safe.

            Returns:
                Tuple of (index, results) where results may be None if cancelled or failed.
            """
            index, row = index_row_tuple

            # Check cancellation before starting
            if stop_event and stop_event.is_set():
                logger.debug(f"Article {index} skipped (cancelled)")
                return index, None

            try:
                # Compute results without mutating DataFrame (thread-safe)
                results = self.compute_single_article_results(
                    row, title_col, abstract_col,
                    open_questions, yes_no_questions
                )

                # Add delay to avoid rate limiting
                delay = self.config.get('API_REQUEST_DELAY', 1)
                if delay > 0:
                    time.sleep(delay)

                return index, results

            except Exception as e:
                # Log error with sanitized message
                from .security_utils import safe_log_error
                logger.error(f"Failed to process article {index}: {safe_log_error(e, include_type=True)}")
                logger.debug(f"Article {index} details: row keys={list(row.keys())}", exc_info=True)
                return index, None

        # Process articles concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_article, (index, row)): index
                for index, row in df.iterrows()
            }

            # Process completed tasks as they finish
            for future in as_completed(futures, timeout=None):
                # Check cancellation in main thread
                if stop_event and stop_event.is_set():
                    logger.warning("Analysis cancelled by user - stopping after current batch")
                    # Cancel pending futures
                    for pending_future in futures:
                        pending_future.cancel()
                    break

                try:
                    # Get result with timeout
                    index, results = future.result(timeout=task_timeout)
                    completed_count += 1

                    # Apply results to DataFrame in main thread (thread-safe)
                    if results is not None:
                        self._apply_results_to_dataframe(
                            df, index, results, open_questions, yes_no_questions
                        )
                    else:
                        failed_count += 1
                        logger.warning(f"Article {index} returned no results (failed or cancelled)")

                    # Prepare callback result in legacy format
                    callback_result = None
                    if results and not results.get("missing_data", False):
                        callback_result = {
                            "initial": results.get("parsed_data", {}),
                            "verification": results.get("verification", {})
                        }

                    # Progress callback
                    if progress_callback:
                        try:
                            progress_callback(index, total, callback_result)
                        except Exception as e:
                            logger.error(f"Progress callback failed: {e}", exc_info=True)

                except TimeoutError:
                    failed_count += 1
                    index = futures[future]
                    logger.error(f"Article {index} timed out after {task_timeout}s")

                except Exception as e:
                    failed_count += 1
                    index = futures.get(future, "unknown")
                    from .security_utils import safe_log_error
                    logger.error(f"Unexpected error processing article {index}: {safe_log_error(e)}", exc_info=True)

        # Summary logging
        logger.info(f"Batch analysis complete: {completed_count}/{total} processed, {failed_count} failed")

        # Log token usage statistics
        token_summary = self.token_tracker.get_summary()
        logger.info(f"\nToken usage statistics:")
        logger.info(f"  API calls: {token_summary['call_count']}")
        logger.info(f"  {token_summary['summary_text']}")
        logger.info(f"  In millions: Input={token_summary['input_M']:.3f}M, Output={token_summary['output_M']:.3f}M, Total={token_summary['total_M']:.3f}M")
        if token_summary['call_count'] > 0:
            logger.info(f"  Average tokens per call: {token_summary['avg_tokens_per_call']:.0f}")

        if stop_event and stop_event.is_set():
            raise KeyboardInterrupt("Analysis stopped by user")

        return df

    def generate_statistics(
        self,
        df: pd.DataFrame,
        open_questions: List[Dict],
        yes_no_questions: List[Dict]
    ) -> Dict[str, Any]:
        """Generate statistics summary from screening results.

        Args:
            df: DataFrame with screening results
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions

        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_articles': len(df),
            'verification_enabled': self.config.get('ENABLE_VERIFICATION', True),
            'yes_no_results': {},
            'open_question_stats': {}
        }

        # Statistics for yes/no questions
        for q in yes_no_questions:
            col = q['column_name']
            if col in df.columns:
                value_counts = df[col].value_counts()
                stats['yes_no_results'][q['question']] = {
                    '是': int(value_counts.get('是', 0)),
                    '否': int(value_counts.get('否', 0)),
                    '不确定': int(value_counts.get('不确定', 0)),
                    '其他': int(len(df) - value_counts.get('是', 0) -
                               value_counts.get('否', 0) -
                               value_counts.get('不确定', 0))
                }

                # Verification stats if enabled
                if self.config.get('ENABLE_VERIFICATION', True):
                    vcol = f"{col}_verified"
                    if vcol in df.columns:
                        ver_counts = df[vcol].value_counts()
                        stats['yes_no_results'][q['question']]['verification'] = {
                            '已验证': int(ver_counts.get('是', 0)),
                            '未验证': int(ver_counts.get('否', 0)),
                            '不确定': int(ver_counts.get('不确定', 0)),
                        }

        # Statistics for open questions
        for q in open_questions:
            col = q['column_name']
            if col in df.columns:
                non_empty = df[col].notna() & (df[col] != '') & (df[col] != '信息缺失')
                stats['open_question_stats'][q['question']] = {
                    'answered': int(non_empty.sum()),
                    'missing': int((~non_empty).sum())
                }

        return stats


# --- 主程序 ---
def main():
    logger.info("--- AI辅助文献分析脚本启动 ---")

    config, questions = load_config()

    open_questions = questions.get('open_questions', [])
    yes_no_questions = questions.get('yes_no_questions', [])

    logger.info("正在加载数据文件...")
    input_file_path = get_file_path_from_config(config)
    df, title_col, abstract_col = load_and_validate_data(input_file_path, config)

    # 准备DataFrame以存储结果
    df = prepare_dataframe(df, open_questions, yes_no_questions)

    base, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"

    total_articles = len(df)
    max_workers = config.get('MAX_WORKERS', DEFAULT_MAX_WORKERS)
    logger.info(f"共找到 {total_articles} 篇文章待处理。")
    logger.info(f"使用并发处理模式，工作线程数: {max_workers}")

    # Create screener with concurrent processing support
    logger.info("正在初始化AI客户端和分析器...")
    screener = AbstractScreener(config)

    # Progress callback for CLI output
    def progress_callback(index: int, total_count: int, result: Optional[Dict[str, Any]]) -> None:
        """Log progress to console."""
        title = str(df.iloc[index].get(title_col, ''))[:50]
        logger.info(f"[{index + 1}/{total_count}] 已完成: {title}")

    # Use concurrent batch processing (5-10x faster than serial!)
    try:
        logger.info("开始并发分析...")
        df = screener.analyze_batch_concurrent(
            df=df,
            title_col=title_col,
            abstract_col=abstract_col,
            open_questions=open_questions,
            yes_no_questions=yes_no_questions,
            progress_callback=progress_callback,
            stop_event=None  # No cancellation support in CLI mode
        )
    except KeyboardInterrupt:
        logger.warning("用户中断处理。正在保存已完成的结果...")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        logger.warning("正在保存已完成的结果...")

    # Save results
    try:
        if output_file_path.endswith('.csv'):
            df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        elif output_file_path.endswith('.xlsx'):
            df.to_excel(output_file_path, index=False, engine='openpyxl')
        logger.info(f"\n处理完成！结果已保存到: {output_file_path}")
    except Exception as e:
        logger.error(f"保存结果文件时出错: {e}")

    # Generate summary statistics
    criteria_columns = [q['column_name'] for q in yes_no_questions]
    summary = generate_weekly_summary(df, criteria_columns)
    logger.info(f"筛选摘要： {summary}")

    logger.info("--- 脚本执行完毕 ---")

def run_gui():
    """创建增强的GUI界面"""
    import threading
    from .tk_compat import ensure_native_macos_version

    ensure_native_macos_version()

    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("文献快速筛选工具")

    file_path_var = tk.StringVar()
    status_var = tk.StringVar()
    q_path = Path(__file__).resolve().parent.parent / "questions_config.json"
    try:
        with q_path.open("r", encoding="utf-8") as f:
            mode_options = list(json.load(f).keys())
    except Exception:
        mode_options = ["weekly_screening"]
    mode_var = tk.StringVar(value=mode_options[0] if mode_options else "")
    progress_var = tk.DoubleVar()

    def browse_file():
        path = filedialog.askopenfilename(filetypes=[("CSV or Excel", ("*.csv", "*.xlsx"))])
        if path:
            file_path_var.set(path)

    def process_file(path, mode):
        config, questions = load_config(mode=mode)
        config['INPUT_FILE_PATH'] = path
        config['CONFIG_MODE'] = mode
        try:
            client = AIClient(config)
            open_q = questions.get('open_questions', [])
            yes_no_q = questions.get('yes_no_questions', [])
            df, title_col, abstract_col = load_and_validate_data(path, config)
            df = prepare_dataframe(df, open_q, yes_no_q)
            total = len(df)
            for index, row in df.iterrows():
                status_var.set(f"处理中: {index + 1}/{total}")
                progress_var.set((index + 1) / total * 100)
                analyze_article(df, index, row, title_col, abstract_col, open_q, yes_no_q, config, client)
                time.sleep(config['API_REQUEST_DELAY'])
            base, ext = os.path.splitext(path)
            output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
            if output_file_path.endswith('.csv'):
                df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(output_file_path, index=False, engine='openpyxl')
            messagebox.showinfo("完成", f"处理完成，结果已保存到: {output_file_path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))
        finally:
            status_var.set("")
            progress_var.set(0)

    def start_analysis():
        path = file_path_var.get()
        if not path:
            messagebox.showerror("错误", "请先选择文件")
            return
        threading.Thread(target=process_file, args=(path, mode_var.get()), daemon=True).start()

    config_frame = ttk.Frame(root)
    config_frame.pack(pady=10)
    ttk.Label(config_frame, text="筛选模式:").pack(side=tk.LEFT)
    ttk.Combobox(config_frame, textvariable=mode_var, values=mode_options).pack(side=tk.LEFT)

    tk.Label(root, text="选择CSV/XLSX文件:").pack(pady=5)
    tk.Entry(root, textvariable=file_path_var, width=40).pack(padx=5)
    tk.Button(root, text="浏览", command=browse_file).pack(pady=5)
    tk.Button(root, text="开始分析", command=start_analysis).pack(pady=5)
    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill=tk.X, padx=20, pady=10)
    tk.Label(root, textvariable=status_var).pack(pady=5)
    root.mainloop()
