import pandas as pd
import re
import pdfplumber
import warnings
warnings.filterwarnings('ignore')

def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).upper().replace(',', '').replace('₹', '').replace('CR', '').replace('DR', '').strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

def clean_narration(text):
    """Surgical tool to remove dates and junk from Narration"""
    if pd.isna(text): return ""
    text = str(text).replace('\n', ' ').strip()
    
    # Remove any dates hiding inside the narration (e.g., 12/04/2026, 12-04-26, 12-Apr-2026)
    text = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '', text)
    text = re.sub(r'\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b', '', text)
    
    # Remove extra spaces left after cutting dates
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def process_bank_statement(file, pdf_pw=""):
    # ==============================
    # 📄 1. PDF BANK STATEMENT LOGIC
    # ==============================
    if file.name.endswith('.pdf'):
        try:
            extracted_text = ""
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                for page in pdf.pages:
                    extracted_text += page.extract_text() + "\n"
            
            date_rx = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
            parsed = []
            for line in extracted_text.split('\n'):
                line = line.strip()
                if date_rx.match(line):
                    parts = line.split()
                    date_val = parts[0]
                    raw_narration = " ".join(parts[1:])[:120]
                    clean_narr = clean_narration(raw_narration) # Applied Surgical Cleaner
                    parsed.append({
                        "Date": date_val,
                        "Narration": clean_narr,
                        "Debit": 0.0,
                        "Credit": 0.0,
                        "Tally Ledger": "🟡 Suspense A/c"
                    })
            
            if not parsed: return None, "Error: PDF se dates nahi mili. Password check karein."
            
            df_clean = pd.DataFrame(parsed)
            metrics = {"op_bal": 0.0, "cl_bal": 0.0, "dr_count": 0, "cr_count": 0, "total_dr_amt": 0.0, "total_cr_amt": 0.0}
            return df_clean, metrics
            
        except Exception as e:
            return None, f"PDF Read Error: {e}"

    # ==============================
    # 📊 2. EXCEL/CSV BANK STATEMENT LOGIC
    # ==============================
    else:
        try:
            df_raw = pd.read_excel(file, header=None) if file.name.endswith('.xlsx') else pd.read_csv(file, header=None)
        except Exception as e:
            return None, f"Read Error: {e}"
        
        # Header Hunter
        header_idx = -1
        for idx, row in df_raw.iterrows():
            row_str = " ".join(str(x).lower() for x in row.values if pd.notna(x))
            if ('date' in row_str or 'txn' in row_str) and ('bal' in row_str or 'credit' in row_str or 'debit' in row_str):
                header_idx = idx
                break
                
        if header_idx == -1: return None, "Error: Bank Header row nahi mili. Format check karein."

        df = pd.read_excel(file, skiprows=header_idx) if file.name.endswith('.xlsx') else pd.read_csv(file, skiprows=header_idx)
        date_c, desc_c, debit_c, credit_c, bal_c = None, None, None, None, None
        
        for col in df.columns:
            c = str(col).lower().replace('\n', ' ').replace('.', '').strip()
            if not date_c and any(w in c for w in ['date', 'value dt', 'txn dt']): date_c = col
            elif not desc_c and any(w in c for w in ['narration', 'particular', 'description']): desc_c = col
            elif not debit_c and any(w in c for w in ['debit', 'withdrawal', 'dr', 'paid out']): debit_c = col
            elif not credit_c and any(w in c for w in ['credit', 'deposit', 'cr', 'paid in']): credit_c = col
            elif not bal_c and any(w in c for w in ['balance', 'bal', 'closing']): bal_c = col

        if not (debit_c and credit_c and bal_c and date_c and desc_c):
            return None, "Error: Standard Bank Columns nahi mile."

        # Extract Balances safely
        df[bal_c] = df[bal_c].apply(extract_pure_number)
        valid_balances = df[df[bal_c] != 0.0][bal_c]
        
        # Strict Extraction: Dr & Cr
        df[debit_c] = df[debit_c].apply(extract_pure_number)
        df[credit_c] = df[credit_c].apply(extract_pure_number)
        
        # Rule: Transaction must have a Date AND (Debit > 0 OR Credit > 0)
        df.dropna(subset=[date_c], inplace=True)
        df = df[(df[debit_c] > 0) | (df[credit_c] > 0)]

        if df.empty: return None, "Error: Safai ke baad koi valid bank entry nahi bachi."

        # Build Clean DataFrame
        df_clean = pd.DataFrame()
        df_clean["Date"] = df[date_c].astype(str).str.replace('00:00:00', '').str.strip()
        df_clean["Narration"] = df[desc_c].apply(clean_narration) # Cleaned Narration
        df_clean["Debit"] = df[debit_c]
        df_clean["Credit"] = df[credit_c]
        df_clean["Tally Ledger"] = "🟡 Suspense A/c"

        metrics = {
            "op_bal": valid_balances.iloc[0] if not valid_balances.empty else 0.0,
            "cl_bal": valid_balances.iloc[-1] if not valid_balances.empty else 0.0,
            "dr_count": int((df_clean["Debit"] > 0).sum()),
            "cr_count": int((df_clean["Credit"] > 0).sum()),
            "total_dr_amt": float(df_clean["Debit"].sum()),
            "total_cr_amt": float(df_clean["Credit"].sum())
        }
            
        return df_clean, metrics
