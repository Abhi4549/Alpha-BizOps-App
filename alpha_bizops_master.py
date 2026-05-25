import pandas as pd
import tabula
import io

def process_bank_statement(file):
    try:
        # Tabula PDF read karega
        if file.name.endswith('.pdf'):
            # pages='all' se poori file read hogi
            dfs = tabula.read_pdf(file, pages='all', lattice=True)
            df = pd.concat(dfs)
        else:
            # Excel/CSV
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
        
        # Data Cleaning: Columns lowercase karo taaki 'date', 'debit' dhoondh sake
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        return df, "Success"
    except Exception as e:
        return None, f"Error: {str(e)}"
