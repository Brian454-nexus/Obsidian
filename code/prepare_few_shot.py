import pandas as pd
import json
import os
import pdfplumber

# Converts an Excel file into a simple comma-separated string
def excel_to_text(path):
    try:
        # read_excel loads the file, header=None means we treat the first row as data
        df = pd.read_excel(path, header=None)
        # Convert to a simple CSV string without index
        return df.to_csv(index=False, header=False)
    except Exception as e:
        return str(e)

# Converts an Excel file into a JSON string list format
def excel_to_json(path):
    try:
        df = pd.read_excel(path)
        # orient="records" creates a clean list of dictionaries (objects)
        return df.to_json(orient="records")
    except Exception as e:
        return "[]"

# Extracts raw text from all pages of a PDF document
def pdf_to_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print("PDF error:", e)
    return text

# The main goal of this script is to package our manual "good examples"
# into a single `few_shot.json` file so we can teach the AI later.
def main():
    inputs_dir = "../inputs"
    outputs_dir = "../outputs"
    
    examples = []
    
    # We are looping through files starting with 1, 2, and 3
    # These act as our 3 "Few-Shot" training examples.
    for i in range(1, 4):
        # Find input file starting with our current number 'i'
        in_file = [f for f in os.listdir(inputs_dir) if f.startswith(f"{i}.")] [0]
        # Find the matching expert-completed output file
        out_file = [f for f in os.listdir(outputs_dir) if f.startswith(f"{i}.")] [0]
        
        in_path = os.path.join(inputs_dir, in_file)
        out_path = os.path.join(outputs_dir, out_file)
        
        # Read the raw text from the input file
        in_text = excel_to_text(in_path)
        # Read the finished structured JSON from the output file
        out_json = excel_to_json(out_path)
        
        # Package the raw text and the target output together into one "example"
        examples.append({
            "input_file": in_file,
            # We truncate the input text to 2000 characters to keep our AI prompt from getting too massive
            "input_text": in_text[:2000] + ("..." if len(in_text) > 2000 else ""),
            "output_json": out_json
        })
        
    # Save the organized examples into a single JSON file
    with open("few_shot.json", "w") as f:
        json.dump(examples, f, indent=2)
    print("few_shot.json generated.")

if __name__ == "__main__":
    main()
