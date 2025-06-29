# 🌟 GCC Market Dataset Generator  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  

A tool for generating multiple-choice questions from financial reports of GCC companies using OpenAI's GPT models.  

## 📋 Overview  

This project processes PDF financial reports from Gulf Cooperation Council (GCC) companies, extracts text, and generates high-quality multiple-choice questions. The questions cover financial performance, market position, business strategy, and key personnel information.  

## ✨ Features  

✅ Processes PDF files organized by country directories  
✅ Extracts text from PDFs using PyPDF2  
✅ Generates questions using OpenAI's GPT models  
✅ Covers multiple question categories (financial, operational, strategic, personnel)  
✅ Supports all GCC countries (KSA, UAE, Qatar, Kuwait, Bahrain, Oman)  
✅ Produces JSONL output compatible with quiz applications  
✅ Provides a detailed processing summary  

## 🔧 Requirements  

- Python 3.8+  
- OpenAI API key  

## 🚀 Installation  

```bash
# Clone the repository
git clone https://github.com/AbduljalilHassan/GCC-Market-Dataset-Generator.git
cd GCC-Market-Dataset-Generator

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here
```

## 📂 Directory Structure  

Organize your PDF files as follows:  

```
files/
├── KSA/
├── UAE/
├── Qatar/
├── Kuwait/
├── Bahrain/
└── Oman/
```

## 💻 Usage  

### Basic Usage  

```bash
python GCC_market_dataset.py
```

### Advanced Options  

```bash
python GCC_market_dataset.py --input_dir=files --output_dir=output --questions_per_company=50
```

| Argument              | Description                     | Default          |
|----------------------|--------------------------------|------------------|
| `--input_dir`       | Directory with PDF files       | `files`          |
| `--output_dir`      | Output directory               | `output`         |
| `--openai_api_key`  | OpenAI API key                 | Environment variable |
| `--questions_per_company` | Number of questions per company | `50`             |

## 📊 Output Format  

Each question is formatted as a JSON object:  

```json
{
  "id": "FAB1001",
  "question": "What was First Abu Dhabi Bank's net profit in 2023?",
  "options": {
    "A": "AED 13.4 billion",
    "B": "AED 15.2 billion",
    "C": "AED 11.9 billion",
    "D": "AED 17.8 billion"
  },
  "answer": "A",
  "metadata": {
    "difficulty": "medium",
    "company": "First Abu Dhabi Bank",
    "report_year": "2023",
    "source_file": "FAB_2023.pdf",
    "source_chunk_id": "1",
    "source_type": "financial_data",
    "category": "Financial Performance"
  }
}
```

## 🔍 Example Commands  

```bash
# Generate questions for all companies
python generate_questions.py

# Generate questions for specific countries
python generate_questions.py --input_dir=files/UAE --output_dir=output/UAE
```

## ⚙️ Processing Flow  

1️⃣ **PDF Collection**: Scans directories for PDF files  
2️⃣ **Text Extraction**: Extracts text from PDFs  
3️⃣ **Chunking**: Splits text into manageable chunks  
4️⃣ **Question Generation**: Creates questions using OpenAI  
5️⃣ **Output**: Saves questions in JSONL format  


## 📄 License  

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  

## 🙏 Acknowledgments  

- **OpenAI** for providing the GPT models  
- **PyPDF2** for PDF text extraction capabilities  
