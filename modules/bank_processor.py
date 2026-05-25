import pandas as pd
import re
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
    # 1. READ FILE
    try:
        df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
    except Exception as e:
        return None, f"File Error: {e}"

    # 2. FIND COLUMNS AUTOMATICALLY (Regex Match)
    date_col = next((c for c in df.columns if 'date' in str(c).lower()), df.columns[0])
    narration_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['desc', 'narr', 'part', 'rem'])), df.columns[1])
    
    # 3. SMARTER AMOUNT DETECTION
    # Agar Debit/Credit alag hain, wo uthao. Agar sirf Amount hai, toh uska sign check karo.
    debit_col = next((c for c in df.columns if 'debit' in str(c).lower() or 'withdraw' in str(c).lower()), None)
    credit_col = next((c for c in df.columns if 'credit' in str(c).lower() or 'deposit' in str(c).lower()), None)
    amt_col = next((c for c in df.columns if 'amount' in str(c).lower()), None)

    df_clean = pd.DataFrame()
    df_clean['Date'] = df[date_col]
    df_clean['Narration'] = df[narration_col]

    if debit_col and credit_col:
        df_clean['Debit'] = df[debit_col].apply(extract_pure_number)
        df_clean['Credit'] = df[credit_col].apply(extract_pure_number)
    elif amt_col:
        # Single Amount Column Logic
        df['temp_amt'] = df[amt_col].apply(extract_pure_number)
        df_clean['Debit'] = df.apply(lambda row: row['temp_amt'] if ('dr' in str(row[amt_col]).lower() or row['temp_amt'] < 0) else 0.0, axis=1)
        df_clean['Credit'] = df.apply(lambda row: row['temp_amt'] if ('cr' in str(row[amt_col]).lower() or row['temp_amt'] > 0) else 0.0, axis=1)
    else:
        return None, "Error: Column Mapping Failed. Please check Excel headers."

    df_clean['Tally Ledger'] = "🟡 Suspense A/c"
    
    metrics = {
        "op_bal": 0.0, "cl_bal": 0.0,
        "dr_count": int((df_clean['Debit'] > 0).sum()),
        "cr_count": int((df_clean['Credit'] > 0).sum()),
        "total_dr_amt": float(df_clean['Debit'].sum()),
        "total_cr_amt": float(df_clean['Credit'].sum())
    }
    
    return df_clean, metrics
