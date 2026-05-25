import pandas as pd
import tabula
import io

def process_bank_statement(file):
    try:
        # PDF ke liye Tabula (Table Reader)
        if file.name.endswith('.pdf'):
            # Tabula exact grid uthata hai, narration mix nahi hoga
            dfs = tabula.read_pdf(file, pages='all', multiple_tables=True)
            df = pd.concat(dfs)
        else:
            # Excel/CSV ke liye direct clean read
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            
        # Column mapping (Strict mode)
        # 1. Headers ko lowercase
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # 2. Amount columns ko filter out karke numeric mein convert
        def to_float(x):
            try: return float(str(x).replace(',', '').replace('₹', ''))
            except: return 0.0

        # DataFrame cleaning
        # Hamein Date, Narration, Debit, Credit chahiye
        # Logic: Agar column mein 'withdraw' ya 'dr' hai = Debit, 'deposit' ya 'cr' = Credit
        
        return df, "Success"
    except Exception as e:
        return None, str(e)
