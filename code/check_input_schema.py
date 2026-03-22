import pandas as pd
import os

# Heuristic validation utility for unstructured input blobs.
INPUT_DIR = "../inputs"

def check_inputs():
    """Attempts to auto-detect schema configurations using pandas binary parsing on the raw inputs."""
    for f in os.listdir(INPUT_DIR):
        if f.endswith(".xlsx"):
            path = os.path.join(INPUT_DIR, f)
            print(f"--- Ingress File: {f} ---")
            try:
                # Pandas schema detection (may fault on malformed binaries without explicit headers)
                df = pd.read_excel(path)
                
                print("Detected Schema Fields:", list(df.columns))
                print("Dimensionality Envelope:", df.shape)
            except Exception as e:
                print("Data Frame Initialization Trap:", e)
            print()

if __name__ == "__main__":
    check_inputs()
