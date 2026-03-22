import pandas as pd
import json
import os
import pdfplumber

def excel_to_text(path):
    """Reads an Excel file and converts it into a comma-separated text string without headers or indices."""
    try:
        df = pd.read_excel(path, header=None)
        return df.to_csv(index=False, header=False)
    except Exception as e:
        return str(e)

def excel_to_json(path):
    """Reads an Excel file and serializes the data into a JSON string format of record objects."""
    try:
        df = pd.read_excel(path)
        return df.to_json(orient="records")
    except Exception as e:
        return "[]"

def pdf_to_text(path):
    """Extracts and concatenates the raw text from all pages of a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\\n"
    except Exception as e:
        print("PDF IO exception:", e)
    return text

def main():
    """
    Compiles input and expected output pairs from the ground truth data into a JSON file (`few_shot.json`).
    This JSON is used as a few-shot examples mapping for the LLM extraction pipeline. 
    Long input texts are truncated to prevent exceeding the LLM's context window.
    """
    inputs_dir = "../inputs"
    outputs_dir = "../outputs"
    
    examples = []
    
    # Iterate over the ground truth dataset files which are sequentially named with prefixes 1, 2, and 3
    for i in range(1, 4):
        in_file = [f for f in os.listdir(inputs_dir) if f.startswith(f"{i}.")] [0]
        out_file = [f for f in os.listdir(outputs_dir) if f.startswith(f"{i}.")] [0]
        
        in_path = os.path.join(inputs_dir, in_file)
        out_path = os.path.join(outputs_dir, out_file)
        
        in_text = excel_to_text(in_path)
        out_json = excel_to_json(out_path)
        
        examples.append({
            "input_file": in_file,
            "input_text": in_text[:2000] + ("..." if len(in_text) > 2000 else ""),
            "output_json": out_json
        })
        
    with open("few_shot.json", "w") as f:
        json.dump(examples, f, indent=2)
    print("few_shot.json compiled successfully.")

if __name__ == "__main__":
    main()
