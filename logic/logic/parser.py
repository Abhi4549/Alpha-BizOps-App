import pandas as pd
import tabula
import pdfplumber

def extract_data(file, pw=""):
    # PDF Parsing
    if file.name.endswith('.pdf'):
        # Lattice mode: Table ko grid ki tarah uthane ke liye
        dfs = tabula.read_pdf(file, password=pw, pages='all', lattice=True)
        df = pd.concat(dfs)
    # Excel/CSV Parsing
    else:
        df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
    
    # Standardize columns (Date, Narration, Amount)
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df
