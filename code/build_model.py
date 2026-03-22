import os

# MODEL_TEMPLATE contains the python code that will be written into `model.py`.
# We use this template approach to inject our "Few-Shot" examples directly into the final script.
# "Few-Shot" means giving an AI model a few examples of how to do a task so it understands the pattern.
MODEL_TEMPLATE = '''import os
import json
import time
import pandas as pd
import pdfplumber
import anthropic

# 1. Environment Setup
# Try to load environment variables from a .env file (like API keys)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

INPUT_DIR = "input/" if os.path.exists("input/") else "../inputs/"
OUTPUT_DIR = "output/" if os.path.exists("output/") else "../outputs/"

# 2. Few-Shot Examples (Learning Materials)
FEW_SHOT_JSON = r"""{few_shot_data}"""

# 3. Data Extraction Functions
def excel_to_text(path):
    try:
        df = pd.read_excel(path, header=None)
        return df.to_csv(index=False, header=False)
    except Exception as e:
        return str(e)

# UPGRADE 4: Advanced PDF Parsing with OCR Fallback
def pdf_to_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\\n"
    except Exception as e:
        print(f"PDF error: {e}")
        
    # If the text is suspiciously short (e.g. Scanned image), attempt OCR Fallback
    if len(text.strip()) < 50:
        print("  -> Very little text found. Attempting OCR Fallback...")
        try:
            import pytesseract
            from pdf2image import convert_from_path
            images = convert_from_path(path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\\n"
            if ocr_text.strip():
                print("  -> OCR Success!")
                return ocr_text
        except ImportError:
            print("  -> OCR failed: pytesseract or pdf2image not installed. Operating blindly.")
        except Exception as e:
            print(f"  -> OCR Error: {e}")
            
    return text

def extract_text(path):
    if path.lower().endswith(".pdf"):
        return pdf_to_text(path)
    elif path.lower().endswith((".xlsx", ".xls")):
        return excel_to_text(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

# Helper to cleanly extract JSON even if there is conversational text
def extract_json_from_response(text):
    text = text.strip()
    # UPGRADE 2: Strip Chain of Thought thinking block if it exists
    if "<thinking>" in text and "</thinking>" in text:
        text = text.split("</thinking>")[-1].strip()
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# 5. Pipeline Logic
def process_file(file_path, output_path):
    print(f"Processing: {file_path}")
    raw_text = extract_text(file_path)
    
    max_chars = 200000
    if len(raw_text) > max_chars:
        print(f"Warning: Text truncated from {len(raw_text)} to {max_chars} characters.")
        raw_text = raw_text[:max_chars]
        
    # UPGRADE 2: Chain of Thought Strategy
    prompt = (
        "You are an expert Data Engineer tasked with transforming raw, unstructured risk registers "
        "into clean, standardized machine-readable JSON formats.\\n"
        "Your task is to extract all the risk items and format them as a JSON list of objects.\\n\\n"
        "Here are examples showing the transformation from 'input_text' to the exact desired 'output_json' format. "
        "If the input closely resembles one of these examples, you MUST use the exact same column/key structure. "
        "retaining all critical information such as Dates, Risk IDs, Descriptions, Likelihood, Impact, Priorities, Owners, and Mitigations.\\n\\n"
        "EXAMPLES:\\n" + FEW_SHOT_JSON + "\\n\\n"
        "---\\n"
        "CRITICAL INSTRUCTION 1: You MUST extract and output EVERY SINGLE RISK ROW present. Process exhaustively.\\n"
        "CRITICAL INSTRUCTION 2: First, analyze the columns and write your step-by-step reasoning inside <thinking>...</thinking> tags. "
        "After the </thinking> tag, output ONLY a valid JSON list of objects. Do not wrap the JSON in markdown blocks.\\n\\n"
        "NEW INPUT TEXT:\\n" + raw_text
    )
    
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": prompt}]
    
    # UPGRADE 1 & 3: Agentic Self-Correction Loop & Exponential Backoff
    max_agent_retries = 3
    for attempt in range(max_agent_retries):
        print(f"  -> Contacting Claude API (Attempt {attempt+1}/{max_agent_retries})...")
        
        # Exponential backoff for rate limits
        api_retries = 5
        response = None
        for api_attempt in range(api_retries):
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8192,
                    temperature=0.0,
                    messages=messages
                )
                break # Success
            except anthropic.RateLimitError:
                sleep_time = 2 ** api_attempt
                print(f"  -> Rate limit hit. Waiting {sleep_time}s...")
                time.sleep(sleep_time)
            except anthropic.APIError as e:
                print(f"  -> API Error: {e}. Retrying in 5s...")
                time.sleep(5)
        
        if not response:
            print(f"  -> Failed to reach API after {api_retries} attempts.")
            return

        reply_text = response.content[0].text
        json_str = extract_json_from_response(reply_text)
        
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                raise ValueError("JSON is not a list of objects.")
            if len(data) == 0:
                raise ValueError("Extracted JSON array is empty.")
                
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Simple Schema heuristic check: ensure DataFrame is valid
            if df.empty:
                raise ValueError("Parsed DataFrame is empty.")
                
            # If we succeed without errors, break the agentic loop and save
            df.to_excel(output_path, index=False)
            print(f"  -> Saved successfully to {output_path}")
            return
            
        except json.JSONDecodeError as e:
            error_msg = f"JSONDecodeError: {str(e)}. Make sure you output perfectly valid JSON."
        except Exception as e:
            error_msg = f"Validation Error: {str(e)}"
            
        # Agentic Correction: Feed the error back to Claude if it failed
        print(f"  -> Output validation failed: {error_msg}. Asking Claude to Self-Correct...")
        messages.append({"role": "assistant", "content": reply_text})
        messages.append({
            "role": "user", "content": f"Your previous output failed validation with this error: {error_msg}\\nPlease try again. Output your reasoning in <thinking> tags, followed by the corrected JSON array."
        })
        
    print(f"  -> Gave up processing {file_path} after max agentic retries.")

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory {INPUT_DIR} not found.")
        return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    for file_name in os.listdir(INPUT_DIR):
        if not (file_name.endswith(".xlsx") or file_name.endswith(".pdf")):
            continue
            
        input_path = os.path.join(INPUT_DIR, file_name)
        
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

def build():
    try:
        with open("few_shot.json", "r") as f:
            few_shot_data = f.read()
            
        # Escape any triple quotes inside the JSON so it doesn't break our Python string format
        few_shot_data = few_shot_data.replace('"""', '\\"\\"\\"')
        
        final_code = MODEL_TEMPLATE.replace("{few_shot_data}", few_shot_data)
        
        with open("model.py", "w", encoding="utf-8") as f:
            f.write(final_code)
            
        print("Successfully built model.py with Agentic Self-Correction, Exponential Backoff, OCR Fallback, and CoT!")
    except Exception as e:
        print(f"Error building model.py: {e}")

if __name__ == "__main__":
    build()
