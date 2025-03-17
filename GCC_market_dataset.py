import os
import re
import json
import glob
import time
import argparse
from tqdm import tqdm
import pandas as pd
from openai import OpenAI
import PyPDF2

def collect_gcc_company_pdfs(directory_path):
    """
    Collect all PDF files from the specified directory for GCC companies,
    organized by country subdirectories.
    """
    print(f"Looking for PDFs in: {directory_path}")

    if not os.path.exists(directory_path):
        print(f"ERROR: Directory {directory_path} does not exist!")
        return {}

    # Get all country directories
    country_dirs = [d for d in os.listdir(directory_path)
                   if os.path.isdir(os.path.join(directory_path, d))
                   and not d.startswith('.')]

    print(f"Found country directories: {country_dirs}")

    company_pdfs = {}
    total_pdfs = 0

    # Process each country directory
    for country in country_dirs:
        country_path = os.path.join(directory_path, country)
        pdf_files = glob.glob(os.path.join(country_path, "*.pdf"))

        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)

            # Extract company name from filename
            company_code_match = re.match(r'^([A-Za-z]{2,4})[-_]', filename)
            if company_code_match:
                company_code = company_code_match.group(1).upper()

                # Map company codes to full names
                company_name_map = {
                    'BBK': 'Bank of Bahrain and Kuwait',
                    'NBB': 'National Bank of Bahrain',
                    'SIB': 'Sohar International Bank',
                    'ABK': 'Al Ahli Bank of Kuwait',
                    'NBK': 'National Bank of Kuwait',
                    'BM': 'Bank Muscat',
                    'EDO': 'Energy Development Oman',
                    'ADIB': 'Abu Dhabi Islamic Bank',
                    'FAB': 'First Abu Dhabi Bank',
                    'ENBD': 'Emirates NBD',
                    'DIB': 'Dubai Islamic Bank',
                    'CBD': 'Commercial Bank of Dubai',
                    'TAB': 'Tabreed'
                }

                company_name = company_name_map.get(company_code, f"{company_code} {country}")
            else:
                # If no clear code, use first part of filename
                company_name = filename.split('_')[0].replace('-', ' ').title()

            if company_name not in company_pdfs:
                company_pdfs[company_name] = []

            company_pdfs[company_name].append({
                'path': pdf_path,
                'country': country,
                'filename': filename
            })
            total_pdfs += 1

    print(f"Found {total_pdfs} PDFs from {len(company_pdfs)} companies across {len(country_dirs)} countries")
    return company_pdfs

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyPDF2.
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def create_chunks_from_text(text, pdf_info, chunk_size=1500, chunk_overlap=200):
    """
    Create chunks from text for processing.
    """
    chunks = []
    company_name = pdf_info['company']
    pdf_path = pdf_info['path']
    country = pdf_info['country']
    filename = pdf_info['filename']

    # Extract year from filename
    year_match = re.search(r'20\d{2}', filename)
    report_year = year_match.group(0) if year_match else "2024"  # Default to 2024 if not found

    if not text:
        print(f"Warning: No text content to create chunks from")
        return chunks

    # Create chunks with overlap
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunk_text = text[i:i + chunk_size]
        if len(chunk_text) < 100:  # Skip very small chunks
            continue

        chunk_id = len(chunks) + 1
        chunks.append({
            "text": chunk_text,
            "chunk_id": str(chunk_id),
            "source_file": filename,
            "company": company_name,
            "country": country,
            "report_year": report_year
        })

    print(f"Created {len(chunks)} chunks from text")
    return chunks

def generate_company_code(company_name):
    """
    Generate a company code from company name (e.g., "First Abu Dhabi Bank" -> "FAB")
    """
    if not company_name:
        return "UNK"  # Unknown

    # Special case for common abbreviations
    company_abbrev = {
        "First Abu Dhabi Bank": "FAB",
        "Emirates NBD": "ENBD",
        "Abu Dhabi Commercial Bank": "ADCB",
        "Dubai Islamic Bank": "DIB",
        "Emirates Islamic Bank": "EIB",
        "Commercial Bank of Dubai": "CBD",
        "Abu Dhabi Islamic Bank": "ADIB",
        "Tabreed": "TAB",
        "Sohar International Bank": "SIB",
        "EDO": "EDO",
        "Commercial Bank": "CBQ",
        "Bank of Bahrain and Kuwait": "BBK",
        "National Bank of Bahrain": "NBB",
        "Al Ahli Bank of Kuwait": "ABK",
        "National Bank of Kuwait": "NBK",
        "Bank Muscat": "BM"
    }

    if company_name in company_abbrev:
        return company_abbrev[company_name]

    # Generate abbreviation from first letters of each word
    words = company_name.split()
    if len(words) >= 3:
        code = ''.join(word[0] for word in words[:3])
    else:
        code = ''.join(word[:2] for word in words)[:4]

    return code.upper()

def generate_questions(data, openai_client, company_code, id_counter, num_questions=5):
    """
    Generate multiple-choice questions from a chunk of text that includes both financial data and key personnel information.
    """
    # Determine if this is a text chunk or personnel data
    is_chunk = isinstance(data, dict) and 'text' in data

    if is_chunk:
        # Data is a text chunk
        company_name = data['company']
        country = data['country']
        report_year = data['report_year']
        source_file = data['source_file']
        chunk_id = data['chunk_id']
        text = data['text']

        prompt_context = f"the following text from a {country} company financial report"
    else:
        # Assume it's for personnel questions
        company_name = data
        country = "GCC"  # Default
        report_year = "2024"  # Default
        source_file = f"{company_name.replace(' ', '_')}_Report_2024.pdf"
        chunk_id = "0"

        # Create a prompt about key personnel
        text = f"Information about key executives and board members at {company_name}, a company from {country}."
        prompt_context = f"key personnel at {company_name} (a company from {country})"

    prompt = f"""
    You are an expert in creating multiple-choice questions for financial reports.

    Generate {num_questions} challenging multiple-choice questions based on {prompt_context}.

    Text: {text}

    For each question:
    1. Create a clear, specific question about the content provided, which may include financial data, market position, risk factors, business strategy, or key personnel.
    2. Provide 4 options (A, B, C, D) - include the letter prefix in each option
    3. Indicate the correct answer (just the letter A, B, C, or D)
    4. Assign a difficulty level (easy, medium, hard)
    5. Categorize the question (Financial Performance, Market Position, Risk Factors, Corporate Governance, Business Strategy, Operational Metrics, Sustainability, Key Personnel)

    Format your response as a JSON array of objects with these fields:
    - question: the question text
    - options: array of 4 options (including "A. ", "B. ", etc. prefixes)
    - answer: the correct option letter (A, B, C, or D)
    - difficulty: difficulty level
    - category: the category of the question

    IMPORTANT: Return ONLY the JSON array without any markdown formatting, code blocks, or additional text.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        result = response.choices[0].message.content.strip()

        # Clean up the response if it contains markdown code blocks
        if result.startswith("```") and "```" in result:
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result)
            if match:
                result = match.group(1).strip()

        # Try to parse the JSON response
        try:
            questions = json.loads(result)

            # Format questions to match the JSONL format
            formatted_questions = []

            for question in questions:
                id_counter += 1

                category = question.get("category", "Miscellaneous")

                # Map category to source_type
                source_type_mapping = {
                    "Financial Performance": "financial_data",
                    "Market Position": "market_data",
                    "Risk Factors": "risk_data",
                    "Corporate Governance": "governance_data",
                    "Business Strategy": "business_strategy",
                    "Operational Metrics": "operational_data",
                    "Sustainability": "sustainability",
                    "Key Personnel": "personnel_data"
                }

                source_type = source_type_mapping.get(category, "miscellaneous")

                # If not a chunk and category is not personnel, force it to be personnel
                if not is_chunk and category != "Key Personnel":
                    category = "Key Personnel"
                    source_type = "personnel_data"

                formatted_question = {
                    "id": f"{company_code}{id_counter}",
                    "question": question["question"],
                    "options": question["options"],
                    "answer": question["answer"],
                    "metadata": {
                        "difficulty": question.get("difficulty", "medium"),
                        "company": company_name,
                        "report_year": report_year,
                        "source_file": source_file,
                        "source_chunk_id": chunk_id,
                        "source_type": source_type,
                        "category": category
                    }
                }
                formatted_questions.append(formatted_question)

            return formatted_questions, id_counter
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON response: {result}")
            print(f"JSON error: {e}")
            return [], id_counter

    except Exception as e:
        print(f"Error generating questions: {e}")
        return [], id_counter

def process_company_documents(company_name, pdf_infos, output_dir, openai_client, questions_per_company=50):
    """
    Process all documents for a company and generate questions.
    """
    print(f"\nProcessing documents for {company_name}...")

    all_questions = []
    company_code = generate_company_code(company_name)
    id_counter = 1000  # Start from 1000 for each company
    country = pdf_infos[0]['country']  # Assume all PDFs for a company are from the same country

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create country subdirectory
    country_dir = os.path.join(output_dir, country)
    os.makedirs(country_dir, exist_ok=True)

    # Process each PDF
    for pdf_info in pdf_infos:
        pdf_path = pdf_info['path']
        print(f"\nProcessing {pdf_path}...")

        # Extract text from PDF
        document_text = extract_text_from_pdf(pdf_path)

        if document_text:
            # Create chunks from document
            pdf_info['company'] = company_name
            chunks = create_chunks_from_text(document_text, pdf_info)
            print(f"Created {len(chunks)} chunks from document")

            # Generate questions from chunks
            questions_needed = questions_per_company - len(all_questions)
            if questions_needed <= 0:
                break

            # Use only a subset of chunks if we have many
            chunks_to_use = chunks[:min(5, len(chunks))]

            for chunk in tqdm(chunks_to_use, desc="Generating questions from chunks"):
                questions_to_generate = min(5, questions_needed)
                if questions_to_generate <= 0:
                    break

                questions, id_counter = generate_questions(
                    chunk, openai_client, company_code, id_counter, num_questions=questions_to_generate
                )
                all_questions.extend(questions)
                questions_needed -= len(questions)
                print(f"Generated {len(questions)} questions. Total: {len(all_questions)}/{questions_per_company}")

    # Generate personnel questions if we still need more
    if len(all_questions) < questions_per_company:
        questions_needed = questions_per_company - len(all_questions)
        print(f"Generating {questions_needed} personnel questions...")
        personnel_questions, id_counter = generate_questions(
            company_name, openai_client, company_code, id_counter, num_questions=questions_needed
        )
        all_questions.extend(personnel_questions)

    # Save questions to file in country subdirectory
    output_file = os.path.join(country_dir, f"{company_name.replace(' ', '_')}_questions.jsonl")
    with open(output_file, 'w') as f:
        for question in all_questions:
            f.write(json.dumps(question) + '\n')

    print(f"Saved {len(all_questions)} questions to {output_file}")
    return all_questions

def main():
    parser = argparse.ArgumentParser(description='Generate multiple-choice questions from GCC company PDFs')
    parser.add_argument('--input_dir', type=str, default='files', help='Directory containing PDF files organized by country')
    parser.add_argument('--output_dir', type=str, default='output', help='Directory to save generated questions')
    parser.add_argument('--openai_api_key', type=str, help='OpenAI API key')
    parser.add_argument('--questions_per_company', type=int, default=50, help='Number of questions to generate per company')
    args = parser.parse_args()

    # Initialize OpenAI client
    api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key is required. Provide it with --openai_api_key or set OPENAI_API_KEY environment variable.")
        return

    openai_client = OpenAI(api_key=api_key)

    # Collect PDFs
    company_pdfs = collect_gcc_company_pdfs(args.input_dir)

    if not company_pdfs:
        print("No PDF files found. Exiting.")
        return

    # Process each company's documents
    all_questions = []

    for company_name, pdf_infos in company_pdfs.items():
        company_questions = process_company_documents(
            company_name, pdf_infos, args.output_dir, openai_client, args.questions_per_company
        )
        all_questions.extend(company_questions)

    # Save all questions to a combined file
    combined_file = os.path.join(args.output_dir, "GCC_market_dataset.jsonl")
    with open(combined_file, 'w') as f:
        for question in all_questions:
            f.write(json.dumps(question) + '\n')

    print(f"\nProcessing complete! Generated {len(all_questions)} questions total.")
    print(f"Combined output saved to {combined_file}")

    # Create a summary DataFrame
    summary_data = []
    for company_name, pdf_infos in company_pdfs.items():
        company_code = generate_company_code(company_name)
        country = pdf_infos[0]['country']
        company_questions = [q for q in all_questions if q['metadata']['company'] == company_name]

        summary_data.append({
            'Company': company_name,
            'Code': company_code,
            'Country': country,
            'PDFs Processed': len(pdf_infos),
            'Questions Generated': len(company_questions),
            'Categories': ', '.join(sorted(set(q['metadata'].get('category', 'Unknown') for q in company_questions)))
        })

    summary_df = pd.DataFrame(summary_data)
    summary_file = os.path.join(args.output_dir, "processing_summary.csv")
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary saved to {summary_file}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds")