# LitRelevanceAI

An AI-powered tool that automatically analyzes the relevance of academic literature to your research topic. LitRelevanceAI processes Scopus CSV exports using GPT models to generate relevance scores, detailed analyses, and literature review integration suggestions for each paper.

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)

## 📚 Features

- **Automated Relevance Analysis**: Assess how closely papers align with your specific research topic
- **Scoring System**: Get quantitative relevance scores (0-100) for each paper
- **Detailed Analysis**: Receive in-depth explanations of each paper's relevance to your research
- **Literature Review Suggestions**: Get recommendations on how to incorporate papers into your literature review
- **Batch Processing**: Analyze multiple papers in a single run
- **Progress Tracking**: Monitor real-time analysis progress
- **Results Export**: Save all analyses to a timestamped CSV file with original metadata preserved

## 🔧 Installation

### Prerequisites

- Python 3.7 or higher
- OpenAI API key

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/Panda-Kill/LitRelevanceAI.git
   cd LitRelevanceAI
   ```

2. Install dependencies:
   ```
   pip install pandas openai
   ```

3. (Optional) Configure your OpenAI API key:
   - Edit the script to replace the default API key with your own, or
   - Set it as an environment variable

## 🚀 Usage

1. Export your literature data from Scopus as a CSV file
   - In Scopus, select the papers you want to analyze
   - Click "Export" and choose CSV format
   - Ensure the export includes title and abstract fields

2. Run the script:
   ```
   python 文献相关度.py
   ```

3. Follow the prompts:
   - Enter your research topic
   - Provide the path to your Scopus CSV file (you can drag and drop the file)

4. The analysis will begin automatically with progress updates displayed in the console

5. When complete, a new CSV file with analysis results will be saved in the same directory as your input file

## ⚙️ How It Works

1. **Data Import**: The tool reads your Scopus CSV export containing paper titles, abstracts, and other metadata
2. **AI Analysis**: Each paper is analyzed by the OpenAI GPT model using a specialized prompt
3. **Relevance Assessment**: The AI evaluates how closely each paper aligns with your research topic
4. **Scoring**: A relevance score from 0-100 is assigned to each paper
5. **Detailed Analysis**: The AI explains the relationship between each paper and your research topic
6. **Review Suggestions**: The AI provides recommendations on how to integrate each paper into a literature review
7. **Results Export**: All analyses are saved to a new CSV file, preserving the original metadata

## 📊 Example Output

For each paper, the tool generates:

- **Relevance Score**: A numerical assessment (0-100) of relevance
- **Analysis**: A detailed explanation of how the paper relates to your research topic
- **Literature Review Suggestion**: Specific advice on how to incorporate the paper into your review

## ❓ FAQ

**Q: How much does it cost to use this tool?**  
A: The tool uses OpenAI's API, which has associated costs based on usage. Check OpenAI's pricing for the GPT-4o-mini model.

**Q: Can I analyze papers from sources other than Scopus?**  
A: Currently, the tool is optimized for Scopus exports. You may need to reformat data from other sources to match the expected format.

**Q: How accurate is the relevance scoring?**  
A: The relevance scoring uses GPT models which can provide insightful analyses, but you should review the results critically as part of your academic process.

**Q: Is my research data secure?**  
A: The tool sends paper titles and abstracts to OpenAI's API. Please review OpenAI's privacy policy for details on how they handle data.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
---

*Save hours of manual literature screening and focus on the papers that truly matter to your research. Designed for academics, graduate students, and research professionals.*
