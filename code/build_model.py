import os

# MODEL_TEMPLATE: String literal containing the production extraction logic.
# Injected with JSON few-shot examples during the build phase to eliminate runtime I/O dependencies.
MODEL_TEMPLATE = '''import os
import json
import time
import pandas as pd
import pdfplumber
import anthropic

# 1. Environment Initialization
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

INPUT_DIR = "input/" if os.path.exists("input/") else "../inputs/"
OUTPUT_DIR = "output/" if os.path.exists("output/") else "../outputs/"

# 2. Few-Shot Data Payload
# Extracted dynamically from few_shot.json during build.
FEW_SHOT_JSON = r"""{few_shot_data}"""

# 3. Data Ingestion & Formatting Parsers
def excel_to_text(path):
    """Parses an Excel file via pandas and serializes it to a raw CSV format string."""
    try:
        df = pd.read_excel(path, header=None)
        return df.to_csv(index=False, header=False)
    except Exception as e:
        return str(e)

def docx_to_text(path):
    """Extracts raw string aggregates from Word document structures."""
    try:
        import docx
        doc = docx.Document(path)
        return "\\n".join([para.text for para in doc.paragraphs])
    except ImportError:
        print("  -> Dependency error: python-docx not installed. Operating blindly.")
        return ""
    except Exception as e:
        print(f"  -> Word parsing error: {e}")
        return str(e)

def pdf_to_text(path):
    """
    Parses a logical text layer from a PDF document using pdfplumber.
    Falls back to Tesseract OCR if the extracted text payload is < 50 chars (indicating scanned image).
    """
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\\n"
    except Exception as e:
        print(f"PDF error: {e}")
        
    if len(text.strip()) < 50:
        print("  -> Insufficient text layer detected. Attempting OCR Fallback...")
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
            print("  -> OCR dependencies (pytesseract, pdf2image) not found. Operating blindly.")
        except Exception as e:
            print(f"  -> OCR Error: {e}")
            
    return text

def extract_text(path):
    """Dispatcher for text extraction based on file extension."""
    if path.lower().endswith(".pdf"):
        return pdf_to_text(path)
    elif path.lower().endswith((".xlsx", ".xls")):
        return excel_to_text(path)
    elif path.lower().endswith((".doc", ".docx")):
        return docx_to_text(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

def extract_json_from_response(text):
    """
    Strips Chain-of-Thought <thinking> tags and markdown ticks to isolate the raw JSON array.
    """
    text = text.strip()
    if "<thinking>" in text and "</thinking>" in text:
        text = text.split("</thinking>")[-1].strip()
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# 4. Core LLM Orchestration Pipeline
def process_file(file_path, output_path):
    """
    Core extraction orchestrator. Handles file IO, context truncation, CoT prompting, 
    exponential backoff against anthropic API, and an agentic self-validation loop.
    """
    print(f"Processing: {file_path}")
    raw_text = extract_text(file_path)
    
    max_chars = 200000
    if len(raw_text) > max_chars:
        print(f"Warning: Text payload truncated from {len(raw_text)} to {max_chars} chars to fit context window.")
        raw_text = raw_text[:max_chars]
        
    # Few-Shot Chain-of-Thought Prompt Configuration
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
    
    # Agentic Recovery Loop (max 3 retries for schema/json formatting violations)
    max_agent_retries = 3
    for attempt in range(max_agent_retries):
        print(f"  -> Sending payload to Claude API (Agentic Attempt {attempt+1}/{max_agent_retries})...")
        
        # Exponential Backoff for resilient API interactions (Status 429)
        api_retries = 5
        response = None
        for api_attempt in range(api_retries):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=8192,
                    temperature=0.0,
                    messages=messages
                )
                break
            except anthropic.RateLimitError:
                sleep_time = 2 ** api_attempt
                print(f"  -> Status 429: Rate limit hit. Backoff waiting {sleep_time}s...")
                time.sleep(sleep_time)
            except anthropic.APIError as e:
                print(f"  -> Status 500/API Error: {e}. Retrying in 5s...")
                time.sleep(5)
        
        if not response:
            print(f"  -> Fatal: Failed to reach Anthropic API after {api_retries} attempts.")
            return

        reply_text = response.content[0].text
        json_str = extract_json_from_response(reply_text)
        
        try:
            # Parse and validate schema heuristic
            data = json.loads(json_str)
            if not isinstance(data, list):
                raise ValueError("Payload root is not a list of objects.")
            if len(data) == 0:
                raise ValueError("JSON array successfully parsed but is completely empty.")
                
            df = pd.DataFrame(data)
            
            if df.empty:
                raise ValueError("DataFrame instantiation failed or frame is empty.")
                
            # Serialization
            df.to_excel(output_path, index=False)
            print(f"  -> Data serialized successfully to {output_path}")
            return
            
        except json.JSONDecodeError as e:
            error_msg = f"JSONDecodeError: {str(e)}. Make sure you output perfectly valid JSON."
        except Exception as e:
            error_msg = f"Validation Error: {str(e)}"
            
        # Agentic Recovery: Push stack trace back to LLM context to prompt self-correction
        print(f"  -> Agentic Validation trap triggered: {error_msg}. Prompting CoT correction...")
        messages.append({"role": "assistant", "content": reply_text})
        messages.append({
            "role": "user", "content": f"Your previous output triggered an exception: {error_msg}\\nPlease self-correct. Output reasoning in <thinking>, followed strictly by the corrected JSON array."
        })
        
    print(f"  -> Exhausted agentic retries. Processing failed for {file_path}.")

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Input path {INPUT_DIR} not found.")
        return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    for file_name in os.listdir(INPUT_DIR):
        if not (file_name.lower().endswith(".xlsx") or file_name.lower().endswith(".xls") or file_name.lower().endswith(".pdf") or file_name.lower().endswith(".docx") or file_name.lower().endswith(".doc")):
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
    """
    Template compiler: Injects serialized JSON configurations into the ML pipeline string,
    outputting a standalone `model.py` executable with 0 disk I/O dependencies for few-shot data.
    """
    try:
        with open("few_shot.json", "r") as f:
            few_shot_data = f.read()
            
        # Escape string literal delimiters to prevent python syntax errors in the injected template
        few_shot_data = few_shot_data.replace('"""', '\\"\\"\\"')
        
        final_code = MODEL_TEMPLATE.replace("{few_shot_data}", few_shot_data)
        
        with open("model.py", "w", encoding="utf-8") as f:
            f.write(final_code)
            
        print("Successfully built model.py with Agentic Self-Correction, Exponential Backoff, OCR Fallback, and CoT!")
    except Exception as e:
        print(f"Compiler configuration error: {e}")

if __name__ == "__main__":
    build()
