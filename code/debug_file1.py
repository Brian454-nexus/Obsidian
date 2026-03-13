import pandas as pd

df = pd.read_excel("../outputs/1. IVC DOE R2 (Final).xlsx")
print("Shape:", df.shape)
print("Preview:")
print(df.head())
