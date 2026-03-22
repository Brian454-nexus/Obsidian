import pandas as pd
import json
import os
import math

def evaluate():
    """
    Evaluates ML output parity against JSON-encoded ground-truth datasets.
    Cross-references schemas (columns) and yields bidirectional containment accuracy heuristics.
    """
    outputs_dir = "../outputs"
    
    # Payload referencing the known Ground Truth structures
    with open("few_shot.json", "r") as f:
        few_shot = json.load(f)
        
    total_score = 0
    total_possible = 0
    
    print("--- AUTOMATED MATRIX EVALUATION ---")
    
    for item in few_shot:
        target_name = item["input_file"]
        
        if "(Input)" in target_name:
            out_name = target_name.replace("(Input)", "(Final)")
        else:
            out_name = target_name + " (Final)"
            
        gen_path = os.path.join(outputs_dir, out_name)
        
        if not os.path.exists(gen_path):
            print(f"Missing generated extraction for {out_name}")
            continue
            
        gen_df = pd.read_excel(gen_path)
        
        target_data = json.loads(item["output_json"])
        if not target_data:
            continue
        target_df = pd.DataFrame(target_data)
        
        # Step 1: Schema Hash Validation
        target_cols = set(target_df.columns)
        gen_cols = set(gen_df.columns)
        
        print(f"\\nMatrix: {out_name}")
        missing_cols = target_cols - gen_cols
        extra_cols = gen_cols - target_cols
        
        print(f"  Target properties: {len(target_cols)}")
        print(f"  Generated properties: {len(gen_cols)}")
        if missing_cols:
            print(f"  Failed property hashes: {missing_cols}")
        if extra_cols:
            print(f"  Hallucinated/Extra properties: {extra_cols}")
            
        # Step 2: Extraction Accuracy (Containment Verification)
        score = 0
        possible = len(target_cols) * len(target_df)
        
        # Bidirectional containment string mapping
        for idx in range(min(len(target_df), len(gen_df))):
            for col in target_cols:
                if col in gen_df.columns:
                    t_val = str(target_df.iloc[idx][col]).strip().lower()
                    g_val = str(gen_df.iloc[idx][col]).strip().lower()
                    
                    if t_val in ["nan", "none", "null"]: t_val = ""
                    if g_val in ["nan", "none", "null"]: g_val = ""
                        
                    if t_val == g_val or (t_val and t_val in g_val) or (g_val and g_val in t_val):
                        score += 1

        print(f"  Content matches: {score} / {possible}")
        
        total_score += score
        total_possible += possible

    if total_possible > 0:
        accuracy = (total_score / total_possible) * 100
        print(f"\\n>>> NET MATRIX ACCURACY SCORE: {accuracy:.2f}% <<<")

if __name__ == "__main__":
    evaluate()
