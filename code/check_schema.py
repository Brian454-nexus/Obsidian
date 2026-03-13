import pandas as pd
import os

# This script is a quick utility to inspect our AI-generated output files 
# and make sure they have the basic structural 'schema' expected.

OUTPUT_DIR = "../outputs"

def check_outputs():
    # Look at every file within the outputs directory
    for f in os.listdir(OUTPUT_DIR):
        # We only care about Excel files (our final output format)
        if f.endswith(".xlsx"):
            path = os.path.join(OUTPUT_DIR, f)
            print(f"--- File: {f} ---")
            
            # Load the Excel file as a pandas Table
            df = pd.read_excel(path)
            
            # Print the table's column names
            print("Columns:", list(df.columns))
            # Print the table's dimensions (Rows x Columns)
            print("Shape:", df.shape)
            
            # Print the very first line of data to "eyeball" if it looks right
            if not df.empty:
                print("First row:", df.iloc[0].to_dict())
            print()

if __name__ == "__main__":
    check_outputs()
