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


load_env_file()

DEFAULT_CONFIG = {
    **BASE_CONFIG,
    "MODEL_NAME": "gpt-4o-mini",
    "TEMPERATURE": 0.3,
}


def load_config(path: Optional[str] = None, questions_path: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load module configuration and question templates."""

    default_cfg = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    config = base_load_config(str(path or default_cfg), DEFAULT_CONFIG)

    q_path = questions_path or Path(__file__).resolve().parent.parent / "configs" / "questions" / "csv.yaml"
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

    def _load_prompt_template(self) -> str:
        """Load prompt template from prompts_config.json."""
        prompts_path = Path(__file__).resolve().parent.parent / "prompts_config.json"
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
            # Ensure necessary columns exist
            required_columns = ['Title', 'Abstract']
            column_mappings = {
                'Title': ['Title', '文献标题'],
                'Abstract': ['Abstract', '摘要']
            }
            
            for col in required_columns:
                if col not in df.columns:
                    # Try to find possible alternative column names
                    for alt_col in column_mappings.get(col, []):
                        if alt_col in df.columns:
                            df[col] = df[alt_col]
                            break
                    else:
                        raise ValueError(f"Missing necessary column in CSV file: {col}")
            
            # Add columns for analysis results
            if 'Relevance Score' not in df.columns:
                df['Relevance Score'] = None
            if 'Analysis Result' not in df.columns:
                df['Analysis Result'] = None
            if 'Literature Review Suggestion' not in df.columns:
                df['Literature Review Suggestion'] = None
        
            return df
        except Exception as e:
            raise Exception(f"Failed to read CSV file: {str(e)}")

    def analyze_paper(self, title: str, abstract: str) -> Dict:
        """Analyze the relevance of a single paper to the research topic"""
        prompt = self.prompt_template.format(
            research_topic=self.research_topic,
            title=title,
            abstract=abstract
        )
        try:
            response = self.client.request(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.get("TEMPERATURE", 0.3),
            )
            response_text = response["choices"][0]["message"]["content"].strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                import re
                relevance_score_match = re.search(r'"relevance_score"\s*:\s*(\d+)', response_text)
                relevance_score = int(relevance_score_match.group(1)) if relevance_score_match else 0
                analysis_match = re.search(r'"analysis"\s*:\s*"([^"]*)"', response_text)
                analysis = analysis_match.group(1) if analysis_match else "Unable to extract analysis result from response"
                lit_review_match = re.search(r'"literature_review_suggestion"\s*:\s*"([^"]*)"', response_text)
                lit_review = lit_review_match.group(1) if lit_review_match else ""
                return {
                    "relevance_score": relevance_score,
                    "analysis": analysis,
                    "literature_review_suggestion": lit_review,
                }
        except Exception as e:
            raise Exception(f"Failed to analyze paper: {str(e)}")
    def batch_analyze(self, df: pd.DataFrame, original_file_path: str) -> List[Dict]:
        """Batch analyze multiple papers"""
        results = []
        total = len(df)

        try:
            for i, (idx, row) in enumerate(df.iterrows(), start=1):
                print(f"\nAnalyzing paper {i}/{total}...")
                print(f"Title: {row['Title']}")

                if pd.isna(row['Title']) or pd.isna(row['Abstract']):
                    print(f"Warning: The title or abstract of this paper is empty, skipped")
                    continue

                result = self.analyze_paper(row['Title'], row['Abstract'])
                result['title'] = row['Title']
                results.append(result)

                print(f"Relevance Score: {result['relevance_score']}")
                print(f"Analysis Result: {result['analysis'][:200]}...")

                # Update the original CSV file in real-time
                df.at[idx, 'Relevance Score'] = result['relevance_score']
                df.at[idx, 'Analysis Result'] = result['analysis']
                df.at[idx, 'Literature Review Suggestion'] = result.get('literature_review_suggestion', '')

                # Save the state after each analysis
                self.save_results(df, original_file_path, is_interim=True)
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nProgram interrupted by user. Saving completed analysis results...")
        finally:
            if len(results) > 0:
                self.save_results(df, original_file_path)  # Use the provided file path

        return results

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
                print(f"\nAnalysis results saved to: {os.path.abspath(new_file_path)}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")


def get_user_input():
    """Get user input configuration information"""
    print("Welcome to the Literature Relevance Analysis Tool!\n")

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
        print("Invalid choice, please enter 1 or 2")

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
            print(f"File not found: {abs_path}")
            print("Please ensure:")
            print("1. The file path is correct")
            print("2. The file actually exists")
            print("3. If the path contains spaces, enclose it in quotes")
            print("Tip: You can drag the file directly into the terminal window\n")

    config["INPUT_FILE_PATH"] = abs_path
    return research_topic, abs_path, config


def main():
    try:
        config, questions = load_config()
        research_topic, file_path, user_cfg = get_user_input()
        config.update(user_cfg)

        print("\nInitializing analyzer...")
        analyzer = LiteratureAnalyzer(config, research_topic, questions)

        print("Reading literature data...")
        df = analyzer.read_scopus_csv(file_path)

        print(f"\nFound {len(df)} papers, starting analysis...\n")
        results = analyzer.batch_analyze(df, file_path)  # Pass the actual file path instead of a string constant

        # Print summary statistics
        relevance_scores = [r['relevance_score'] for r in results]
        print("\nAnalysis complete!")
        print(f"Total number of papers: {len(results)}")
        if relevance_scores:
            print(f"Average relevance score: {sum(relevance_scores) / len(relevance_scores):.2f}")
            print(f"Number of highly relevant papers (score >= 80): {len([s for s in relevance_scores if s >= 80])}")

    except Exception as e:
        print(f"\nProgram error: {str(e)}")
        import traceback
        print("\nDetailed error information:")
        print(traceback.format_exc())

    input("\nPress Enter to exit the program...")
