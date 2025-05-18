# 25.05.18 Updated
Based on Dr Muhammad Rashid Saeed's workshop on systematic literature analysis, the prompts and collected data have been reorganized. 

Now we can customize specific questions for filtering the literature (yes or no questions) or to set some very detailed specific questions (such as what the research question of the article is).

I have got time to do the translation yet. Will be updated later if requested.

# Usage suggestions
I personally feel that the most appropriate usage method is to use a relatively broad search strategy when searching in Scopus, but to provide as detailed a theoretical model description as possible when presenting research topics.

# LitRelevanceAI

An easy-to-use tool that automatically analyzes the relevance of academic papers to your research topic. LitRelevanceAI processes Scopus CSV exports using AI models to help you quickly identify which papers are most relevant to your research.

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)

## What This Tool Does

- **Automatically analyzes papers**: Tells you how relevant each paper is to your research
- **Gives each paper a score**: Rates papers from 0-100 based on relevance
- **Explains why papers are relevant**: Provides detailed explanations you can understand
- **Suggests how to use each paper**: Gives ideas for including papers in your literature review
- **Processes multiple papers at once**: Saves you hours of reading
- **Shows progress in real-time**: Lets you know how the analysis is progressing
- **Saves results for later**: Creates a new file with all your results

## Installation Guide (Step-by-Step)

### What You Need Before Starting

- **Python 3.7 or higher**: If you don't have Python installed, download it from [python.org](https://www.python.org/downloads/)
- **An AI API key**: The tool supports OpenAI (GPT) or Google (Gemini) - you'll need an API key from one of these services
  - For OpenAI: Sign up at [platform.openai.com](https://platform.openai.com/)
  - For Gemini: Sign up at [aistudio.google.com](https://aistudio.google.com/)

### Setting Up (Detailed Instructions)

0. **Make sure you have Python installed on your computer.**

1. **Download the code**:
   - Download `LitRelevance.py` to your computer

2. **Install required packages**:
   - Open your computer's Command Prompt or Terminal
   - Navigate to the folder where you saved the file (use `cd path/to/folder`)
   - Run this command to install all necessary packages (in case you haven't installed them):
   ```
   pip install pandas openai google-generativeai tqdm
   ```

3. **Add your API key**:
   - Open `LitRelevance.py` in any text editor (like Notepad, TextEdit, or VS Code)
   - Find this line near the top: `DEFAULT_API_KEY = ""` 
   - Put your API key between the quotes: `DEFAULT_API_KEY = "your-api-key-here"`
   - Save the file

## How to Use the Tool

1. **Prepare your paper data**:
   - In Scopus, search for papers on your topic
   - Select the papers you want to analyze
   - Click "Export" and choose CSV format (Remember to check the box to download the summary!)
   - Make sure to include titles and abstracts in the export

2. **Run the program**:
   - Open Command Prompt or Terminal
   - Navigate to the folder containing `LitRelevance.py`
   - Run the program:
   ```
   python LitRelevance.py
   ```

3. **Follow the on-screen prompts**:
   - Choose whether to use OpenAI (option 1) or Gemini (option 2)
   - Enter your research topic
   - Enter the path to your CSV file (or drag and drop the file)

4. **Wait for analysis to complete**:
   - The program will show progress as it analyzes each paper
   - Analysis may take several minutes depending on how many papers you're analyzing

5. **Review your results**:
   - When complete, a new CSV file will be created in the same folder as your original file
   - The file name will include the original name plus "analyzed" and a timestamp
   - Open this file in Excel or any spreadsheet program to see the results

## Customizing the Tool for Your Needs

You can easily modify the program to change how it works. Here are some common customizations:

### Change the AI Models Used

Open `LitRelevance.py` in a text editor and find these lines near the top:
```python
DEFAULT_MODEL_OPENAI = "gpt-4o"  # Set the default OpenAI model
DEFAULT_MODEL_GEMINI = "gemini-2.0-flash"  # Set the default Gemini model
```

You can change these to other available models:
- For OpenAI: "gpt-4o-mini", "gpt-3.5-turbo", etc.
- For Gemini: "gemini-1.5-pro", "gemini-1.0-pro", etc.

### Adjust How "Creative" the Analysis Is

Find this line:
```python
DEFAULT_TEMPERATURE = 0.3  # Set the default temperature value
```

Change the value (between 0 and 1):
- Lower values (closer to 0): More focused, consistent results
- Higher values (closer to 1): More creative, varied results

### Change What Information the Tool Asks For

To modify the prompt sent to the AI, find the `analyze_paper` method and update the `prompt` variable:

```python
prompt = f"""Please analyze the relevance of the following paper to the research topic "{self.research_topic}":

Title: {title}
Abstract: {abstract}

Please provide the following information:
# You can modify these instructions to get different types of analysis
1. Relevance analysis (detailed explanation of the connection between the paper and the research topic)
2. A relevance score from 0-100, where 0 means completely unrelated and 100 means highly relevant
3. If this paper were to be included in a literature review on the research topic, how should it be cited and discussed? Please tell me directly how you would write it.

Please return in the following JSON format:
{{
    "relevance_score": <number>,
    "analysis": "<analysis text>",
    "literature_review_suggestion": "<literature review suggestion>"
}}"""
```

## Troubleshooting Common Problems

### "File not found" Error
- Make sure you typed the file path correctly
- Try dragging and dropping the file into the terminal window
- Check if the file is in the location you expect

### API Key Issues
- Verify your API key is correct and has not expired
- Make sure you have billing set up on your API account
- Check that you have credits/quota available

### CSV Format Problems
- Make sure your CSV file includes "Title" and "Abstract" columns
- If using a CSV exported from somewhere other than Scopus, check column names
- For non-English CSV files, ensure column names are properly recognized

### Program Crashes During Analysis
- Make sure your API key is valid and has not run out of credits
- **Try running with fewer papers first to test**

## FAQ

**Q: Do I need to pay to use this tool?**  
A: The tool itself is free, but you need an API key from either OpenAI or Google, which may have associated costs based on usage. For now, the Gemini 2.0 Flash is free.

**Q: How many papers can I analyze at once?**  
A: There's no built-in limit, but analyzing many papers will take longer and may cost more in API usage.

**Q: Can I use this tool with papers not from Scopus?**  
A: Yes, but you'll need to format your CSV file to include at least "Title" and "Abstract" columns.

**Q: How accurate is the analysis?**  
A: The tool uses advanced AI models which provide good insights, but always review the results yourself before making academic decisions. The purpose of this tool is to help you identify the articles you should prioritize reading from a large body of literature.

**Q: Where is my data sent when using this tool?**  
A: Paper titles and abstracts are sent to either OpenAI or Google (depending on which API you choose) for analysis.

---

*LitRelevanceAI: Save time on literature reviews and focus on papers that truly matter to your research.*
