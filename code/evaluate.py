import pandas as pd
import os

def evaluate():
    # 1. Setup Folders
    # We look at the 'outputs' folder (expected targets/answers) and 'output' folder (what our model generated)
    outputs_dir = "../outputs"
    generated_dir = "output"
    
    total_score = 0
    total_possible = 0
    
    # For this testing script, we assume there are 3 main files to evaluate (1., 2., 3.)
    for i in range(1, 4):
        # 2. File Finding
        # Find files starting with "1.", "2.", "3." in the respective folders
        target_file = [f for f in os.listdir(outputs_dir) if f.startswith(f"{i}.")] [0]
        gen_file = [f for f in os.listdir(generated_dir) if f.startswith(f"{i}.")] [0]
        
        target_path = os.path.join(outputs_dir, target_file)
        gen_path = os.path.join(generated_dir, gen_file)
        
        # Load both the target answer and the generated answer into pandas DataFrames (tables)
        target_df = pd.read_excel(target_path)
        gen_df = pd.read_excel(gen_path)
        
        print(f"--- Evaluating File {i} ---")
        
        # 3. Check Structural Match (Columns)
        # We first check if our AI generated all the correct columns requested by the target answer.
        target_cols = set(target_df.columns)
        gen_cols = set(gen_df.columns)
        
        missing_cols = target_cols - gen_cols
        extra_cols = gen_cols - target_cols
        
        print(f"Missing columns: {missing_cols}")
        print(f"Extra columns: {extra_cols}")
        
        score = 0
        possible = len(target_cols) * len(target_df)
        
        # 4. Check Cell Content Match (Accuracy)
        # We loop through each cell. We compare the actual target value vs what our AI generated.
        # This is a rough match. We assume the LLM outputs rows in roughly the same order.
        # min() makes sure we don't crash if the AI generated too many or too few rows.
        for idx in range(min(len(target_df), len(gen_df))):
            for col in target_cols:
                if col in gen_df.columns: # Only check if the column actually exists in generation
                    # Convert to lowercase strings for a fairer comparison (case-insensitive)
                    t_val = str(target_df.iloc[idx][col]).strip().lower()
                    g_val = str(gen_df.iloc[idx][col]).strip().lower()
                    
                    # Ignore 'nan' or 'none' values which mean empty cells
                    if t_val == "nan" or t_val == "none":
                        t_val = ""
                    if g_val == "nan" or g_val == "none":
                        g_val = ""
                        
                    # If the cells match perfectly OR one value is contained within the other, we count it as a point!
                    if t_val == g_val or (t_val in g_val) or (g_val in t_val):
                        score += 1
        
        # file_max calculates the maximum possible score
        file_max = max(len(target_df), len(gen_df)) * len(target_cols)
        print(f"Matches: {score} / {possible}")
        
        # Add to the running total for all files
        total_score += score
        total_possible += possible

    # 5. Final Calculation
    # Calculate the total accuracy percentage across all assessed files
    if total_possible > 0:
        print(f"\\nTotal Estimated Accuracy: {total_score / total_possible * 100:.2f}%")

if __name__ == "__main__":
    evaluate()
