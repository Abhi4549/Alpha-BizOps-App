import pandas as pd
import pdfplumber
import re

def clean_amount(val):
    """Amount ko sirf number mein convert karta hai"""
    if pd.isna(val): return 0.0
    val_str = re.sub(r'[^\d.]', '', str(val).replace(',', ''))
    try: return float(val_str)
    except: return 0.0

def process_bank_statement(file, pdf_pw=""):
    try:
        # --- PDF TABLE EXTRACTION ---
        if file.name.endswith('.pdf'):
            data = []
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        for row in table[1:]: # Skip header
                            # Row format: [Date, Narration, Debit, Credit, Balance]
                            if len(row) >= 4:
                                data.append({
                                    "Date": row[0],
                                    "Narration": row[1],
                                    "Debit": clean_amount(row[2]),
                                    "Credit": clean_amount(row[3])
                                })
            df = pd.DataFrame(data)

        # --- EXCEL/CSV EXTRACTION ---
        else:
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, encoding='latin1')
            df.columns = [c.lower() for c in df.columns]
            # Mapping columns dynamically
            date_c = next((c for c in df.columns if 'date' in c), df.columns[0])
            narr_c = next((c for c in df.columns if 'narr' in c or 'part' in c), df.columns[1])
            dr_c = next((c for c in df.columns if 'debit' in c), df.columns[2])
            cr_c = next((c for c in df.columns if 'credit' in c), df.columns[3])
            
            df = df[[date_c, narr_c, dr_c, cr_c]].copy()
            df.columns = ["Date", "Narration", "Debit", "Credit"]
            df["Debit"] = df["Debit"].apply(clean_amount)
            df["Credit"] = df["Credit"].apply(clean_amount)

        # Audit Summary Logic
        metrics = {
            "total_entries": len(df),
            "dr_count": int((df["Debit"] > 0).sum()),
            "cr_count": int((df["Credit"] > 0).sum()),
            "total_dr": df["Debit"].sum(),
            "total_cr": df["Credit"].sum()
        }
        
        return df, metrics

    except Exception as e:
        return None, str(e)
