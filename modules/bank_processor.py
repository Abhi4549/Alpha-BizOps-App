import pandas as pd
import tabula
import io

def process_bank_statement(file):
    try:
        if file.name.endswith('.pdf'):
            # Lattice=True tabular data uthane ke liye
            dfs = tabula.read_pdf(file, pages='all', lattice=True)
            df = pd.concat(dfs)
        else:
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, encoding='latin1')
        
        df.columns = [str(c).lower().strip() for c in df.columns]
        return df, "Success"
    except Exception as e:
        return None, str(e)
