import pandas as pd
import os

def evaluate():
    """
    Evaluates extraction model accuracy by computing schema parity and cell-wise containment mapping
    between generated DataFrame records and ground-truth target outputs.
    """
    outputs_dir = "../outputs"
    generated_dir = "output"
    
    total_score = 0
    total_possible = 0
    
    for i in range(1, 4):
        # Path resolution
        target_file = [f for f in os.listdir(outputs_dir) if f.startswith(f"{i}.")] [0]
        gen_file = [f for f in os.listdir(generated_dir) if f.startswith(f"{i}.")] [0]
        
        target_path = os.path.join(outputs_dir, target_file)
        gen_path = os.path.join(generated_dir, gen_file)
        
        # Load matrices unconditionally
        target_df = pd.read_excel(target_path)
        gen_df = pd.read_excel(gen_path)
        
        print(f"--- Evaluating Matrix {i} ---")
        
        # Verify Structural Parity (Schema Hash)
        target_cols = set(target_df.columns)
        gen_cols = set(gen_df.columns)
        
        missing_cols = target_cols - gen_cols
        extra_cols = gen_cols - target_cols
        
        print(f"Missing schema attributes: {missing_cols}")
        print(f"Superfluous properties: {extra_cols}")
        
        score = 0
        possible = len(target_cols) * len(target_df)
        
        # Cell-wise containment analysis
        for idx in range(min(len(target_df), len(gen_df))):
            for col in target_cols:
                if col in gen_df.columns:
                    t_val = str(target_df.iloc[idx][col]).strip().lower()
                    g_val = str(gen_df.iloc[idx][col]).strip().lower()
                    
                    if t_val in ["nan", "none"]: t_val = ""
                    if g_val in ["nan", "none"]: g_val = ""
                        
                    # Loose matching algorithm: bidirectional containment parsing
                    if t_val == g_val or (t_val in g_val) or (g_val in t_val):
                        score += 1
        
        print(f"Parity Match Rate: {score} / {possible}")
        
        total_score += score
        total_possible += possible

    if total_possible > 0:
        print(f"\\nAggregate Accuracy Matrix: {total_score / total_possible * 100:.2f}%")

if __name__ == "__main__":
    evaluate()
