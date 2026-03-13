import pandas as pd
import json
import os
import math

# The evaluate function calculates how well our AI model performed 
# by comparing its generated answers against the expected target answers.
def evaluate():
    outputs_dir = "../outputs"
    
    # We load our 'few_shot.json' because it contains the names of the source files 
    # we know the correct answers for (the ground truth).
    with open("few_shot.json", "r") as f:
        few_shot = json.load(f)
        
    total_score = 0
    total_possible = 0
    
    print("--- AUTOMATED GRADING EVALUATION ---")
    
    # Loop over each example file in our ground truth dataset
    for item in few_shot:
        target_name = item["input_file"] # For instance: "1. ACME Risk Register (Input).xlsx"
        
        # We find the name of the file outputted by the AI model. 
        # The AI renames "(Input)" to "(Final)"
        if "(Input)" in target_name:
            out_name = target_name.replace("(Input)", "(Final)")
        else:
            out_name = target_name + " (Final)"
            
        gen_path = os.path.join(outputs_dir, out_name)
        
        # If the model didn't generate a file for this input, we skip it
        if not os.path.exists(gen_path):
            print(f"Missing generation for {out_name}")
            continue
            
        # Load the generated file as a table (DataFrame)
        gen_df = pd.read_excel(gen_path)
        
        # Load the target 'ground truth' JSON data as a table as well
        target_data = json.loads(item["output_json"])
        if not target_data:
            continue
        target_df = pd.DataFrame(target_data)
        
        #--- Step 1: Check Columns ---
        # Get the set of columns from both tables to check if the AI missed any
        target_cols = set(target_df.columns)
        gen_cols = set(gen_df.columns)
        
        print(f"\\nFile: {out_name}")
        missing_cols = target_cols - gen_cols   # Columns expected but not generated
        extra_cols = gen_cols - target_cols     # Columns generated but not expected
        
        print(f"  Target columns: {len(target_cols)}")
        print(f"  Generated columns: {len(gen_cols)}")
        if missing_cols:
            print(f"  Missing mandatory fields: {missing_cols}")
        if extra_cols:
            print(f"  Extra fields: {extra_cols}")
            
        #--- Step 2: Check Content Match ---    
        score = 0
        possible = len(target_cols) * len(target_df)
        
        # Compare row by row, column by column
        for idx in range(min(len(target_df), len(gen_df))):
            for col in target_cols:
                if col in gen_df.columns:
                    # Clean up the text: convert to strings, lower-case, and strip whitespace
                    t_val = str(target_df.iloc[idx][col]).strip().lower()
                    g_val = str(gen_df.iloc[idx][col]).strip().lower()
                    
                    # Convert 'empty' strings to true empty strings
                    if t_val in ["nan", "none", "null"]: t_val = ""
                    if g_val in ["nan", "none", "null"]: g_val = ""
                        
                    # We give a point if:
                    # 1. The values match exactly
                    # -OR-
                    # 2. One value is contained completely inside the other (e.g. 'high' is in 'very high')
                    if t_val == g_val or (t_val and t_val in g_val) or (g_val and g_val in t_val):
                        score += 1

        print(f"  Content matches: {score} / {possible}")
        
        # Accumulate the total score across all files
        total_score += score
        total_possible += possible

    #--- Step 3: Final Score ---
    # Calculate the total accuracy ratio
    if total_possible > 0:
        accuracy = (total_score / total_possible) * 100
        print(f"\\n>>> TOTAL ESTIMATED ALGORITHM SCORE (Strict Column+Content match): {accuracy:.2f}% <<<")

if __name__ == "__main__":
    evaluate()
