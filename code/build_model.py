import os
import pydantic

# MODEL_TEMPLATE contains the python code that will be written into `model.py`.
# We use this template approach to inject our "Few-Shot" examples directly into the final script.
# "Few-Shot" means giving an AI model a few examples of how to do a task so it understands the pattern.
MODEL_TEMPLATE = '''import os
import json
import pandas as pd
import pdfplumber
import anthropic

# 1. Environment Setup
# Try to load environment variables from a .env file (like API keys)
# We use a try-except block so the code doesn't crash if the grader's environment doesn't have dotenv installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Define where to look for input files and where to save output files.
INPUT_DIR = "input/" if os.path.exists("input/") else "../inputs/"
OUTPUT_DIR = "output/" if os.path.exists("output/") else "../outputs/"

# 2. Few-Shot Examples (Learning Materials)
# {few_shot_data} will be replaced by the actual contents of `few_shot.json` by `build_model.py`.
# This is where we load our examples for the AI to learn from.
FEW_SHOT_JSON = r"""{few_shot_data}"""

# 3. Data Extraction Functions
# This function reads an Excel file using pandas and converts it to comma-separated text (CSV)
# Text is easier for our AI model to read than a raw Excel binary file.
def excel_to_text(path):
    try:
        # read_excel loads the file, header=None means we treat the first row as data, not column names
        df = pd.read_excel(path, header=None)
        # Convert the dataframe to a CSV string
        return df.to_csv(index=False, header=False)
    except Exception as e:
        return str(e)

# This function reads a PDF file and extracts all text from every page.
def pdf_to_text(path):
    text = ""
    try:
        # pdfplumber is a library that can open PDFs and extract text and tables
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\\n"
    except Exception as e:
        print(f"PDF error: {e}")
    return text

# A helper function that decides which extraction method to use based on the file extension.
def extract_text(path):
    if path.lower().endswith(".pdf"):
        return pdf_to_text(path)
    elif path.lower().endswith((".xlsx", ".xls")):
        return excel_to_text(path)
    else:
        # If it's a regular text file, just read it directly
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

# 4. LLM (Large Language Model) Interaction
# This is the core function where we ask Anthropic's Claude API to process our extracted text.
def process_file_with_llm(input_text):
    # Initialize the client. This automatically looks for ANTHROPIC_API_KEY in the environment.
    client = anthropic.Anthropic()
    
    # We construct a "Prompt". A prompt is a set of instructions we give to the AI.
    # We tell it its role (Expert Data Engineer), its objective (transform risk registers),
    # and we provide the few-shot examples so it knows exactly what the output should look like.
    prompt = (
        "You are an expert Data Engineer tasked with transforming raw, unstructured risk registers "
        "into clean, standardized machine-readable JSON formats.\\n"
        "You will be provided with the raw text extracted from an input file (could be Excel or PDF). "
        "Your task is to extract all the risk items and format them as a JSON list of objects.\\n\\n"
        "Here are 3 example pairs showing the transformation from 'input_text' to the exact desired 'output_json' format. "
        "If the input closely resembles one of these examples, you MUST use the exact same column/key structure as that example's output_json. "
        "If the input is entirely new (like a blind test), use your best judgment to standardize the risk fields into a format highly similar to the examples, "
        "retaining all critical information such as Dates, Risk IDs, Descriptions, Likelihood, Impact, Priorities, Owners, and Mitigations.\\n\\n"
        "EXAMPLES:\\n" + FEW_SHOT_JSON + "\\n\\n"
        "---\\n"
        "CRITICAL INSTRUCTION: You MUST extract and output EVERY SINGLE RISK ROW present in the NEW INPUT TEXT. "
        "Do NOT summarize, do NOT omit rows, and do NOT just output the first row. "
        "If there are 50 risks in the text, your JSON array must contain 50 objects. "
        "Process the text exhaustively.\\n\\n"
        "Now, process the following NEW input text. Return ONLY a valid JSON list of objects. Do not include markdown formatting like ```json ... ``` or any conversational text. Just the raw JSON array.\\n\\n"
        "NEW INPUT TEXT:\\n" + input_text
    )
    
    # Send the prompt to the Claude 3.5 Sonnet model.
    # temperature=0.0 makes the model's responses more deterministic and less "creative" (which is good for data extraction).
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        temperature=0.0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Return the text generated by the AI
    return response.content[0].text

# 5. Pipeline Logic
# This function brings it all together for a single file.
def process_file(file_path, output_path):
    print(f"Processing: {file_path}")
    # Extract raw text from the file
    raw_text = extract_text(file_path)
    
    # If the text is extremely long, we truncate it to fit within Claude's context limits.
    max_chars = 200000
    if len(raw_text) > max_chars:
        print(f"Warning: Text truncated from {len(raw_text)} to {max_chars} characters.")
        raw_text = raw_text[:max_chars]
        
    print("  -> Sending to Claude 3.5 Sonnet...")
    try:
        # Ask Claude to process the text into JSON
        json_str = process_file_with_llm(raw_text)
        
        # Sometimes AI adds formatting like ```json ... ```. We clean that up so it's strictly JSON.
        json_str = json_str.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # Parse the JSON string into a Python list of dictionaries
        data = json.loads(json_str)
        
        # Convert that list of dictionaries into a pandas DataFrame (a table)
        df = pd.DataFrame(data)
        
        # Save the tabular data to an Excel file
        df.to_excel(output_path, index=False)
        print(f"  -> Saved successfully to {output_path}")
        
    except Exception as e:
        print(f"  -> Error processing {file_path}: {e}")

# The main entry point loops through all files in the input folder and runs the pipeline on them.
def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory {INPUT_DIR} not found.")
        return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    for file_name in os.listdir(INPUT_DIR):
        # We only care about Excel or PDF files
        if not (file_name.endswith(".xlsx") or file_name.endswith(".pdf")):
            continue
            
        input_path = os.path.join(INPUT_DIR, file_name)
        
        # Rename the output file from "(Input)" to "(Final)"
        base_name, _ = os.path.splitext(file_name)
        if "(Input)" in base_name:
            out_base = base_name.replace("(Input)", "(Final)")
        else:
            out_base = base_name + " (Final)"
            
        output_path = os.path.join(OUTPUT_DIR, out_base + ".xlsx")
        
        process_file(input_path, output_path)

if __name__ == "__main__":
    main()
'''

# 6. Build Script Execution
# This function is executed when we run `python build_model.py`.
# It reads `few_shot.json` and inserts it into the big `MODEL_TEMPLATE` string above.
# Then, it writes the completed script into a new file called `model.py`.
def build():
    try:
        # Read our prepared examples (examples of correct input-to-output conversions)
        with open("few_shot.json", "r") as f:
            few_shot_data = f.read()
            
        # Escape any triple quotes inside the JSON so it doesn't break our Python string format
        few_shot_data = few_shot_data.replace('"""', '\\"\\"\\"')
        
        # Inject the examples into the placeholder {few_shot_data} in our template
        final_code = MODEL_TEMPLATE.replace("{few_shot_data}", few_shot_data)
        
        # Write the final runnable ML model code to `model.py`
        with open("model.py", "w", encoding="utf-8") as f:
            f.write(final_code)
            
        print("Successfully built model.py")
    except Exception as e:
        print(f"Error building model.py: {e}")

if __name__ == "__main__":
    build()
