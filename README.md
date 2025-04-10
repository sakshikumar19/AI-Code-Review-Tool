# AI Code Review Tool

A modular AI-powered code review system that learns coding patterns from existing repositories and provides contextual, actionable feedback on new code. It supports both interactive and automated usage through a Streamlit app, CLI, and GitHub/GitLab bot integrations.

---

## 🚀 Features

- Learns patterns from your existing repositories to tailor reviews.
- Reviews code and highlights issues, style inconsistencies, and structural improvements.
- Offers both summary and line-level suggestions.
- Can be run as a web app, CLI, or integrated directly with GitHub/GitLab.
- Supports `.py`, `.js`, `.java`, `.go` files (extensible).

---

## 📁 Project Structure

```
.
├── .env / .gitignore
├── code_review_cli.py             # CLI interface
├── config.json                    # Bot configuration
├── github_bot.py                  # GitHub/GitLab integration
├── streamlit_script.py           # Streamlit app
├── requirements.txt / LICENSE
├── review_engine/                # Core review engine
│   ├── AI_code_review.py         # Main engine orchestrator
│   ├── config.py
│   ├── difference_analyzer.py
│   ├── pattern_extractor.py
│   ├── rag_engine.py
│   ├── recommendation_generator.py
│   ├── repository_indexer.py
│   └── __init__.py
├── custom_model/
│   ├── source.txt
│   ├── target.txt
│   └── t5_fine_tune.py           # T5 fine-tuning script
```

---

## 🧠 How It Works

1. **Learning Phase**  
   The tool learns code patterns from a given GitHub repository, indexing best practices, structure, and style.

2. **Review Phase**  
   New code is compared against learned patterns. The engine uses a combination of custom heuristics and a Groq-hosted LLM to identify:

   - Logical inconsistencies
   - Style and formatting issues
   - Best practice violations
   - Maintainability concerns

3. **Feedback Phase**  
   Results include:
   - Summary of major and minor issues
   - Inline suggestions (optional)
   - Praises for well-written sections
   - Exportable JSON reports

---

## 🖥️ 1. Using the Streamlit App

Launch the tool locally:

```bash
python -m streamlit run streamlit_script.py
```

**Or use the hosted app here:** [Deployed App URL](https://code-review-tool.streamlit.app/)

### Streamlit UI Flow:

- **Tab 1:** Clone and learn from a GitHub repository
- **Tab 2:** Upload or paste code for review
- Get categorized feedback and download review results as JSON

---

## 🧰 2. Using the CLI Tool

### Learn from a GitHub repo:

```bash
python code_review_cli.py learn <github_repo_url> --groq-api-key YOUR_API_KEY
```

### Review a local code file:

```bash
python code_review_cli.py review <path_to_code_file> --groq-api-key YOUR_API_KEY
```

---

## 🤖 3. Using the GitHub/GitLab Bot

### Run the bot on a Pull/Merge Request:

```bash
python github_bot.py --config config.json --pr <pr_number>
```

### Sample `config.json`:

```json
{
  "platform": "github",
  "token": "your-github-token",
  "owner": "repo-owner",
  "repo": "repo-name",
  "groq_api_key": "your-groq-api-key",
  "vector_db_path": "./vector_db",
  "extensions": [".py", ".js", ".java", ".go"],
  "comment_on_lines": true,
  "comment_on_low_severity": true,
  "learn_repo": true,
  "log_level": "INFO"
}
```

📌 Ensure the bot has necessary comment/write permissions on the repository. If not, results are printed in the terminal instead.

---

Here's a README-style writeup based on the details from the image, optimized for clarity and completeness:

---

## 🔬 On-Premise T5 Model – Proof of Concept

This project explores the viability of deploying a fine-tuned T5 model on-premise to generate basic code comments, offering a privacy-preserving alternative to cloud-based LLMs.

### 🛠 Training Details

- **Dataset**: 15,102 code-comment pairs, primarily focused on Python. The data was scraped from StackOverflow and includes code snippets with obvious blunders.
- **Use Case**: The model is designed to generate single-line explanatory comments for short, error-prone code segments.
- **Training Procedure**:
  - Evaluates model performance every 500 steps using **ROUGE**, **BLEU**, and **exact match** metrics.
  - Training was conducted for **one epoch** (~1.5 hours) due to time constraints.
- **Model Potential**: With extended training, this T5-based model could serve as a lightweight, on-premise alternative to currently deployed models like **Groq LLaMA**.

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/ai-code-review-tool.git
cd ai-code-review-tool
pip install -r requirements.txt
```

---

## 📌 Requirements

- Python ≥ 3.8
- Access to Groq LLM API (for full functionality)
- GitHub/GitLab token (for bot integration)

---

## 🧪 Testing

To be added in future versions:

- Unit tests for engine modules
- Integration tests for CLI and GitHub/GitLab flows
