import pandas as pd
import os

# This script is a quick utility to inspect the shape and columns of our raw INPUT files.

INPUT_DIR = "../inputs"

def check_inputs():
    # Loop over all Excel files in the inputs directory
    for f in os.listdir(INPUT_DIR):
        if f.endswith(".xlsx"):
            path = os.path.join(INPUT_DIR, f)
            print(f"--- File: {f} ---")
            try:
                # Some files might not have clear column headers on row 0, 
                # but we'll load it to see what pandas auto-detects.
                df = pd.read_excel(path)
                
                # Print the column headers that were detected
                print("Columns:", list(df.columns))
                # Print the number of rows x number of columns it thinks exist
                print("Shape:", df.shape)
            except Exception as e:
                # If pandas crashes trying to read an extremely messed up Excel file, print the error
                print("Error reading:", e)
            print()

if __name__ == "__main__":
    check_inputs()
