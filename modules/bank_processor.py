import pandas as pd
import re
import pdfplumber
import warnings
warnings.filterwarnings('ignore')

def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).upper().replace(',', '').replace('₹', '').strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

def process_bank_statement(file, pdf_pw=""):
    df_raw = pd.DataFrame()
    
    # ==============================
    # 📄 1. PDF & EXCEL TABLE EXTRACTION
    # ==============================
    if file.name.endswith('.pdf'):
        try:
            tables = []
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_tables()
                    for t in extracted: tables.extend(t)
            
            if not tables:
                return None, "Error: PDF format is strictly image-based or protected. Tabular data nahi mila."
            
            df_raw = pd.DataFrame(tables)
        except Exception as e:
            return None, f"PDF Error: {str(e)}"
    else:
        try:
            df_raw = pd.read_excel(file, header=None) if file.name.endswith('.xlsx') else pd.read_csv(file, header=None)
        except Exception as e:
            return None, f"Excel Error: {str(e)}"

    # ==============================
    # 📊 2. COLUMN HUNTING & MAPPING
    # ==============================
    header_idx = -1
    for idx, row in df_raw.iterrows():
        row_str = " ".join(str(x).lower() for x in row.values if pd.notna(x))
        if ('date' in row_str or 'txn' in row_str) and ('bal' in row_str or 'credit' in row_str or 'debit' in row_str or 'amount' in row_str):
            header_idx = idx
            break
            
    if header_idx == -1: return None, "Error: Bank table header (Date, Debit, Credit) nahi mila."

    # Set exact header
    df_raw.columns = df_raw.iloc[header_idx].astype(str).str.strip()
    df = df_raw.iloc[header_idx+1:].copy()
    
    date_c, desc_c, debit_c, credit_c, bal_c, amt_c = None, None, None, None, None, None
    for col in df.columns:
        c = str(col).lower().replace('\n', ' ').strip()
        if not date_c and any(w in c for w in ['date', 'value dt', 'txn dt']): date_c = col
        elif not desc_c and any(w in c for w in ['narration', 'particular', 'description', 'remarks']): desc_c = col
        elif not debit_c and any(w in c for w in ['debit', 'withdrawal', 'dr', 'paid out']): debit_c = col
        elif not credit_c and any(w in c for w in ['credit', 'deposit', 'cr', 'paid in']): credit_c = col
        elif not bal_c and any(w in c for w in ['balance', 'bal', 'closing']): bal_c = col
        elif not amt_c and 'amount' in c: amt_c = col

    if not date_c or not desc_c:
        return None, "Error: Standard Date/Narration columns missing."

    # Debit/Credit Intelligence Logic
    df['Debit_Clean'] = 0.0
    df['Credit_Clean'] = 0.0

    if debit_c and credit_c:
        df['Debit_Clean'] = df[debit_c].apply(extract_pure_number)
        df['Credit_Clean'] = df[credit_c].apply(extract_pure_number)
    elif amt_c:
        # Handles statements with single "Amount" column
        def split_amt(val):
            s = str(val).strip().upper()
            num = extract_pure_number(s)
            if 'CR' in s or '+' in s: return 0.0, num
            elif 'DR' in s or '-' in s: return num, 0.0
            else: return num, 0.0 # Default fallback to debit if ambiguous
        df[['Debit_Clean', 'Credit_Clean']] = df[amt_c].apply(lambda x: pd.Series(split_amt(x)))
    else:
        return None, "Error: Debit/Credit ya Amount ka column nahi mila."

    # Clean the entries
    df.dropna(subset=[date_c], inplace=True)
    df = df[(df['Debit_Clean'] > 0) | (df['Credit_Clean'] > 0)]
    
    if df.empty: return None, "Error: Data safai ke baad koi amount nahi bachi."

    # ==============================
    # 🧼 3. FINAL CA CLEANING
    # ==============================
    df_clean = pd.DataFrame()
    df_clean["Date"] = df[date_c].astype(str).str.replace('\n', ' ').str.strip()
    
    # Strip any stray dates/amounts leaking into Narration
    date_rx = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    df_clean["Narration"] = df[desc_c].astype(str).str.replace('\n', ' ').str.strip()
    df_clean["Narration"] = df_clean["Narration"].apply(lambda x: re.sub(date_rx, '', x).strip())
    
    df_clean["Debit"] = df['Debit_Clean']
    df_clean["Credit"] = df['Credit_Clean']
    df_clean["Tally Ledger"] = "🟡 Suspense A/c"

    # Auditing Metrics
    op_bal = extract_pure_number(df[bal_c].iloc[0]) if bal_c and not df[bal_c].empty else 0.0
    cl_bal = extract_pure_number(df[bal_c].iloc[-1]) if bal_c and not df[bal_c].empty else 0.0

    metrics = {
        "op_bal": op_bal,
        "cl_bal": cl_bal,
        "dr_count": int((df_clean["Debit"] > 0).sum()),
        "cr_count": int((df_clean["Credit"] > 0).sum()),
        "total_dr_amt": float(df_clean["Debit"].sum()),
        "total_cr_amt": float(df_clean["Credit"].sum())
    }
        
    return df_clean, metrics
