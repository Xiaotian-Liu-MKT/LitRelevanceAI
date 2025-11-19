# Import modules in the order of standard libraries, third-party libraries, and local modules
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

from .config import (
    DEFAULT_CONFIG as BASE_CONFIG,
    load_env_file,
    load_config as base_load_config,
)
from .ai_client import AIClient
from .progress_manager import ProgressManager, create_progress_manager
from .cache import get_cache
from .constants import CHECKPOINT_INTERVAL, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from .logging_config import get_logger
from .utils import AIResponseParser, ColumnDetector
from .resources import resource_path
from .exceptions import FileProcessingError, APIError, ValidationError


load_env_file()
logger = get_logger(__name__)

DEFAULT_CONFIG = {
    **BASE_CONFIG,
    "MODEL_NAME": DEFAULT_MODEL,
    "TEMPERATURE": DEFAULT_TEMPERATURE,
}


def load_config(path: Optional[str] = None, questions_path: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load module configuration and question templates."""

    default_cfg = resource_path("configs", "config.yaml")
    config = base_load_config(str(path or default_cfg), DEFAULT_CONFIG)

    q_path = questions_path or resource_path("configs", "questions", "csv.yaml")
    with open(q_path, 'r', encoding='utf-8') as f:
        questions = yaml.safe_load(f) or {}

    return config, questions

class LiteratureAnalyzer:
    def __init__(self, config: Dict[str, Any], research_topic: str = "", questions: Dict[str, Any] = None):
        self.research_topic = research_topic
        self.config = config
        self.questions = questions or {}
        self.client = AIClient(config)
        self.prompt_template = self._load_prompt_template()
        self.cache = get_cache() if config.get("ENABLE_CACHE", True) else None
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info(f"LiteratureAnalyzer initialized, caching={'enabled' if self.cache else 'disabled'}")

    def _load_prompt_template(self) -> str:
        """Load prompt template from prompts_config.json."""
        prompts_path = resource_path("prompts_config.json")
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
                return prompts.get("csv_analysis", {}).get("main_prompt", self._get_default_prompt())
        except Exception:
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Get default CSV analysis prompt."""
        return """Please analyze the relevance of the following paper to the research topic "{research_topic}":

Title: {title}
Abstract: {abstract}

Please provide the following information:
1. Relevance analysis (detailed explanation of the connection between the paper and the research topic)
2. A relevance score from 0-100, where 0 means completely unrelated and 100 means highly relevant
3. If this paper were to be included in a literature review on the research topic, how should it be cited and discussed? Please tell me directly how you would write it.

Please return in the following JSON format:
{{
    "relevance_score": <number>,
    "analysis": "<analysis text>",
    "literature_review_suggestion": "<literature review suggestion>"
}}"""

    def read_scopus_csv(self, file_path: str) -> pd.DataFrame:
        """Read Scopus exported CSV file"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')

            # Use unified column detection
            title_col = ColumnDetector.get_required_column(df, 'title')
            abstract_col = ColumnDetector.get_required_column(df, 'abstract')

            # Normalize column names
            if title_col != 'Title':
                df['Title'] = df[title_col]
            if abstract_col != 'Abstract':
                df['Abstract'] = df[abstract_col]

            # Add columns for analysis results
            if 'Relevance Score' not in df.columns:
                df['Relevance Score'] = None
            if 'Analysis Result' not in df.columns:
                df['Analysis Result'] = None
            if 'Literature Review Suggestion' not in df.columns:
                df['Literature Review Suggestion'] = None

            return df
        except FileNotFoundError as e:
            raise FileProcessingError(
                f"CSV文件未找到: {file_path}"
            ) from e
        except pd.errors.ParserError as e:
            raise FileProcessingError(
                f"CSV格式错误，请检查文件格式。错误详情: {str(e)}"
            ) from e
        except pd.errors.EmptyDataError as e:
            raise FileProcessingError(
                f"CSV文件为空: {file_path}"
            ) from e
        except Exception as e:
            logger.error(f"读取CSV时发生未预期错误: {e}", exc_info=True)
            raise FileProcessingError(
                f"无法读取CSV文件: {str(e)}"
            ) from e

    def analyze_paper(self, title: str, abstract: str) -> Dict:
        """Analyze the relevance of a single paper to the research topic"""
        # Try to get from cache first
        if self.cache:
            cache_key = self.research_topic  # Use research topic as part of cache key
            cached_result = self.cache.get(title, abstract, cache_key)
            if cached_result is not None:
                self.cache_hits += 1
                logger.debug(f"Cache hit for '{title[:50]}...'")
                return cached_result
            self.cache_misses += 1

        prompt = self.prompt_template.format(
            research_topic=self.research_topic,
            title=title,
            abstract=abstract
        )
        try:
            req_kwargs = {}
            if getattr(self.client, "supports_temperature", True):
                req_kwargs["temperature"] = self.config.get("TEMPERATURE", 0.3)
            response = self.client.request(messages=[{"role": "user", "content": prompt}], **req_kwargs)
            response_text = response["choices"][0]["message"]["content"].strip()

            # Use unified parser with relevance-specific fallback
            result = AIResponseParser.parse_relevance_response(response_text)

            # Cache the result
            if self.cache:
                cache_key = self.research_topic
                self.cache.set(title, abstract, result, cache_key)

            return result
        except KeyError as e:
            logger.error(f"AI响应格式错误: {e}", exc_info=True)
            raise APIError(
                f"AI响应格式错误，无法提取内容。请检查模型配置。"
            ) from e
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"AI请求网络错误: {e}", exc_info=True)
            raise APIError(
                f"AI请求失败：网络连接超时或中断。请检查网络连接。"
            ) from e
        except Exception as e:
            logger.error(f"分析文献时发生错误: {e}", exc_info=True)
            raise APIError(
                f"分析文献失败: {str(e)}"
            ) from e
    def batch_analyze(self, df: pd.DataFrame, original_file_path: str, progress_callback=None, use_checkpoint=True) -> List[Dict]:
        """Batch analyze multiple papers with thread-safe updates and progress checkpoints.

        Args:
            df: DataFrame to analyze
            original_file_path: Path to save results
            progress_callback: Optional callback(index, total, result) for progress updates
            use_checkpoint: Whether to use checkpoint system (default: True)

        Returns:
            List of analysis results
        """
        results = []
        total = len(df)

        # Set up progress manager for checkpointing
        progress_mgr = None
        if use_checkpoint:
            progress_mgr = create_progress_manager(original_file_path, suffix="_analyzed")

            # Check for existing checkpoint
            if progress_mgr.has_checkpoint():
                logger.info("\n" + "="*60)
                logger.info(progress_mgr.get_resume_prompt())
                logger.info("="*60)
                # For CLI, ask user; for GUI, this should be handled by caller
                # For now, auto-resume in CLI mode
                checkpoint_df = progress_mgr.load_dataframe()
                checkpoint_meta = progress_mgr.load_checkpoint()
                if checkpoint_df is not None and checkpoint_meta:
                    logger.info("Resuming from checkpoint...")
                    df = checkpoint_df
                    start_idx = checkpoint_meta.get('last_index', 0)
                    logger.info(f"Resuming from row {start_idx}")
                else:
                    start_idx = 0
            else:
                start_idx = 0
        else:
            start_idx = 0

        try:
            for i, (idx, row) in enumerate(df.iterrows(), start=1):
                # Skip already processed rows
                if idx < start_idx:
                    continue

                logger.info(f"\nAnalyzing paper {i}/{total}...")
                logger.info(f"Title: {row['Title']}")

                if pd.isna(row['Title']) or pd.isna(row['Abstract']):
                    logger.warning(f"Warning: The title or abstract of this paper is empty, skipped")
                    if progress_callback:
                        progress_callback(idx, total, None)
                    continue

                result = self.analyze_paper(row['Title'], row['Abstract'])
                result['title'] = row['Title']
                result['index'] = idx  # Store index for later update
                results.append(result)

                logger.info(f"Relevance Score: {result['relevance_score']}")
                logger.info(f"Analysis Result: {result['analysis'][:200]}...")

                # Apply result to DataFrame
                self.apply_result_to_dataframe(df, idx, result)

                # Notify progress callback
                if progress_callback:
                    progress_callback(idx, total, result)

                # Save checkpoint periodically
                if progress_mgr and i % CHECKPOINT_INTERVAL == 0:
                    progress_mgr.save_checkpoint(
                        df, idx,
                        metadata={
                            'research_topic': self.research_topic,
                            'progress_percent': (i / total) * 100
                        }
                    )

                time.sleep(1)

        except KeyboardInterrupt:
            logger.warning("\nProgram interrupted by user. Saving checkpoint...")
            if progress_mgr:
                progress_mgr.save_checkpoint(df, idx, metadata={'interrupted': True})
        except Exception as e:
            logger.error(f"\nError during analysis: {e}")
            if progress_mgr:
                progress_mgr.save_checkpoint(df, idx, metadata={'error': str(e)})
            raise
        finally:
            # Save final results
            if len(results) > 0:
                if progress_mgr:
                    progress_mgr.finalize_results(df)
                    logger.info(f"\nAnalysis complete! Results saved to: {progress_mgr.output_path}")
                else:
                    self.save_results(df, original_file_path)

            # Log cache statistics
            if self.cache:
                total_requests = self.cache_hits + self.cache_misses
                hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
                logger.info(f"Cache statistics: {self.cache_hits} hits, {self.cache_misses} misses ({hit_rate:.1f}% hit rate)")
                logger.info(f"\nCache performance: {self.cache_hits} hits, {self.cache_misses} misses ({hit_rate:.1f}% hit rate)")

        return results

    def apply_result_to_dataframe(self, df: pd.DataFrame, index: int, result: Dict) -> None:
        """Apply a single analysis result to DataFrame (thread-safe when called from main thread).

        Args:
            df: DataFrame to update
            index: Row index
            result: Analysis result dictionary
        """
        df.at[index, 'Relevance Score'] = result['relevance_score']
        df.at[index, 'Analysis Result'] = result['analysis']
        df.at[index, 'Literature Review Suggestion'] = result.get('literature_review_suggestion', '')

    def save_results(self, df: pd.DataFrame, original_file_path: str, is_interim=False):
        """Save analysis results to CSV file"""
        try:
            # Generate new file name
            file_dir = os.path.dirname(original_file_path)
            file_name = os.path.splitext(os.path.basename(original_file_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if is_interim:
                # Temporarily save for interim state, overwrite with fixed name
                new_file_path = os.path.join(file_dir, f"{file_name}_analyzed_interim.csv")
            else:
                # Final save, use timestamp
                new_file_path = os.path.join(file_dir, f"{file_name}_analyzed_{timestamp}.csv")

            # Save to new CSV file
            df.to_csv(new_file_path, index=False, encoding='utf-8-sig')

            if not is_interim:
                logger.info(f"\nAnalysis results saved to: {os.path.abspath(new_file_path)}")
        except PermissionError as e:
            logger.error(f"权限错误：无法写入文件: {e}", exc_info=True)
            raise FileProcessingError(
                f"无法保存结果文件，权限不足。\n"
                f"请确保：\n"
                f"1. 目标文件夹有写入权限\n"
                f"2. 文件未被其他程序占用"
            ) from e
        except OSError as e:
            logger.error(f"文件系统错误: {e}", exc_info=True)
            raise FileProcessingError(
                f"保存结果文件时发生错误: {str(e)}\n"
                f"可能是磁盘空间不足或路径无效。"
            ) from e
        except Exception as e:
            logger.error(f"保存结果时发生未知错误: {e}", exc_info=True)
            raise FileProcessingError(
                f"保存结果失败: {str(e)}"
            ) from e


def get_user_input():
    """Get user input configuration information"""
    logger.info("Welcome to the Literature Relevance Analysis Tool!\n")

    config = DEFAULT_CONFIG.copy()

    while True:
        api_type = input("Please select the API type to use (1: OpenAI, 2: Gemini): ").strip()
        if api_type == "1":
            config["AI_SERVICE"] = "openai"
            config["MODEL_NAME"] = config.get("MODEL_NAME", "gpt-4o-mini")
            break
        elif api_type == "2":
            config["AI_SERVICE"] = "gemini"
            config["MODEL_NAME"] = "gemini-2.0-flash"
            break
        logger.warning("Invalid choice, please enter 1 or 2")

    # Get research topic
    research_topic = input("\nPlease enter your research topic: ").strip()
    while not research_topic:
        research_topic = input("Research topic cannot be empty, please re-enter: ").strip()

    # Get CSV file path
    while True:
        file_path = input("\nPlease enter the path to the Scopus exported CSV file (you can drag the file here): ").strip()

        # Handle user input path
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]  # Remove quotes

        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            break
        else:
            logger.error(f"File not found: {abs_path}")
            logger.info("Please ensure:")
            logger.info("1. The file path is correct")
            logger.info("2. The file actually exists")
            logger.info("3. If the path contains spaces, enclose it in quotes")
            logger.info("Tip: You can drag the file directly into the terminal window\n")

    config["INPUT_FILE_PATH"] = abs_path
    return research_topic, abs_path, config


def main():
    try:
        config, questions = load_config()
        research_topic, file_path, user_cfg = get_user_input()
        config.update(user_cfg)

        logger.info("\nInitializing analyzer...")
        analyzer = LiteratureAnalyzer(config, research_topic, questions)

        logger.info("Reading literature data...")
        df = analyzer.read_scopus_csv(file_path)

        logger.info(f"\nFound {len(df)} papers, starting analysis...\n")
        results = analyzer.batch_analyze(df, file_path)  # Pass the actual file path instead of a string constant

        # Print summary statistics
        relevance_scores = [r['relevance_score'] for r in results]
        logger.info("\nAnalysis complete!")
        logger.info(f"Total number of papers: {len(results)}")
        if relevance_scores:
            logger.info(f"Average relevance score: {sum(relevance_scores) / len(relevance_scores):.2f}")
            logger.info(f"Number of highly relevant papers (score >= 80): {len([s for s in relevance_scores if s >= 80])}")

    except Exception as e:
        logger.error(f"\nProgram error: {str(e)}")
        import traceback
        logger.error("\nDetailed error information:")
        logger.error(traceback.format_exc())

    input("\nPress Enter to exit the program...")
