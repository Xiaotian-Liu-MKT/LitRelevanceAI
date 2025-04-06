# Import modules in the order of standard libraries, third-party libraries, and local modules
import json
import os
import time
from datetime import datetime
from typing import Dict, List
from tqdm import tqdm

import pandas as pd
from openai import OpenAI

# Import Gemini API library
import google.generativeai as genai

# Set default configurations
DEFAULT_API_KEY = ""  # Replace with your API key, now supports OpenAI and Gemini
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"  # Or "gpt-4"; For unknown reasons, "gpt-4o" doesn't work here.
DEFAULT_MODEL_GEMINI = "gemini-2.0-flash"  # Set the default Gemini model
DEFAULT_TEMPERATURE = 0.3  # Set the default temperature value
DEFAULT_API_TYPE = "gemini" # Default API type set to gemini

class LiteratureAnalyzer:
    def __init__(self, api_key: str, research_topic: str, api_type: str = DEFAULT_API_TYPE):
        self.research_topic = research_topic
        self.api_type = api_type
        if api_type == "openai":
            self.client = OpenAI(api_key=api_key)
        elif api_type == "gemini":
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(DEFAULT_MODEL_GEMINI)
        else:
            raise ValueError("Unsupported API type, only 'openai' or 'gemini' are supported")

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
        prompt = f"""Please analyze the relevance of the following paper to the research topic "{self.research_topic}":

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

        try:
            if self.api_type == "openai":
                response = self.client.chat.completions.create(
                    model=DEFAULT_MODEL_OPENAI,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=DEFAULT_TEMPERATURE
                )
                return json.loads(response.choices[0].message.content)
            else:  # gemini
                # Add safety prompt to ensure JSON format output
                formatted_prompt = prompt + "\nPlease ensure to return valid JSON format without any extra text, code block markers, or explanations."
                
                # Set generation parameters, explicitly requiring structured output
                generation_config = {
                    "temperature": DEFAULT_TEMPERATURE,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 2048,
                }
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]
                
                # Create a model with specific configuration
                model = genai.GenerativeModel(
                    model_name=DEFAULT_MODEL_GEMINI,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                response = model.generate_content(formatted_prompt)
                
                # More robust response parsing
                response_text = ""
                try:
                    # Try to get text from response object
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'parts'):
                        response_text = response.parts[0].text
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        response_text = part.text
                                        break
                                if response_text:
                                    break
                    
                    # Clean response text, remove possible code block markers
                    response_text = response_text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    
                    response_text = response_text.strip()
                    
                    # Try to parse JSON
                    return json.loads(response_text)
                    
                except (json.JSONDecodeError, AttributeError, IndexError) as e:
                    print(f"Error parsing Gemini response: {str(e)}")
                    print(f"Original response received: {response}")
                    print(f"Extracted text: {response_text}")
                    
                    # If JSON parsing fails, try using regex to extract key information
                    import re
                    try:
                        relevance_score_match = re.search(r'"relevance_score"\s*:\s*(\d+)', response_text)
                        relevance_score = int(relevance_score_match.group(1)) if relevance_score_match else 0
                        
                        analysis_match = re.search(r'"analysis"\s*:\s*"([^"]*)"', response_text)
                        analysis = analysis_match.group(1) if analysis_match else "Unable to extract analysis result from response"
                        
                        lit_review_match = re.search(r'"literature_review_suggestion"\s*:\s*"([^"]*)"', response_text)
                        lit_review = lit_review_match.group(1) if lit_review_match else ""
                        
                        return {
                            "relevance_score": relevance_score,
                            "analysis": analysis,
                            "literature_review_suggestion": lit_review
                        }
                    except Exception:
                        # If all attempts fail, return a basic response
                        return {
                            "relevance_score": 0,
                            "analysis": f"Unable to parse Gemini response. Original response: {response_text[:200]}...",
                            "literature_review_suggestion": ""
                        }
        except Exception as e:
            print(f"API call error: {str(e)}")
            return {"relevance_score": 0, "analysis": f"Analysis error: {str(e)}", "literature_review_suggestion": ""}

    def batch_analyze(self, df: pd.DataFrame, original_file_path: str) -> List[Dict]:
        """Batch analyze multiple papers"""
        results = []
        total = len(df)

        try:
            for idx, row in tqdm(df.iterrows(), total=len(df), desc="Analyzing papers"):
                print(f"\nAnalyzing paper {idx + 1}/{total}...")
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

    # Choose API type
    while True:
        api_type = input("Please select the API type to use (1: OpenAI, 2: Gemini): ").strip()
        if api_type == "1":
            api_type = "openai"
            break
        elif api_type == "2":
            api_type = "gemini"
            break
        print("Invalid choice, please enter 1 or 2")

    # Use default API key
    print(f"Using default API key")
    api_key = DEFAULT_API_KEY

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

    return api_key, research_topic, abs_path, api_type


def main():
    try:
        # Get user input
        api_key, research_topic, file_path, api_type = get_user_input()

        print("\nInitializing analyzer...")
        analyzer = LiteratureAnalyzer(api_key, research_topic, api_type)

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


if __name__ == "__main__":
    main()
