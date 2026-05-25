import pandas as pd
import re
import pdfplumber

def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).upper().replace(',', '').replace('₹', '').replace('CR', '').replace('DR', '').strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

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
            
            # Hunting for exact Date patterns in PDF lines
            date_rx = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
            parsed = []
            for line in extracted_text.split('\n'):
                line = line.strip()
                if date_rx.match(line):
                    parts = line.split()
                    date_val = parts[0]
                    # Extracting narration cleanly
                    narration = " ".join(parts[1:])[:90] + "..."
                    parsed.append({
                        "Date": date_val,
                        "Narration": narration,
                        "Debit": 0.0,
                        "Credit": 0.0,
                        "Tally Ledger": "🟡 Suspense A/c"
                    })
            
            if not parsed: return None, "Error: PDF se tabular dates nahi mili. Format check karein."
            
            df_clean = pd.DataFrame(parsed)
            metrics = {"op_bal": 0.0, "cl_bal": 0.0, "dr_count": 0, "cr_count": 0}
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
        
        # Searching for the exact header row to skip bank address/junk
        header_idx = -1
        for idx, row in df_raw.iterrows():
            row_str = " ".join(str(x).lower() for x in row.values if pd.notna(x))
            if ('date' in row_str or 'txn' in row_str) and ('bal' in row_str or 'credit' in row_str or 'debit' in row_str):
                header_idx = idx
                break
                
        if header_idx == -1: return None, "Error: Header row nahi mili. Ensure valid Bank Statement."

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

        # Fetching precise Opening and Closing balances before filtering
        df[bal_c] = df[bal_c].apply(extract_pure_number)
        valid_balances = df[df[bal_c] != 0.0][bal_c]
        metrics = {
            "op_bal": valid_balances.iloc[0] if not valid_balances.empty else 0.0,
            "cl_bal": valid_balances.iloc[-1] if not valid_balances.empty else 0.0,
        }

        # Filtering out empty transactions
        df[debit_c] = df[debit_c].apply(extract_pure_number)
        df[credit_c] = df[credit_c].apply(extract_pure_number)
        df = df[(df[debit_c] > 0) | (df[credit_c] > 0)]
        df.dropna(subset=[date_c], inplace=True)

        # Formatting for Tally Push
        df_clean = pd.DataFrame()
        df_clean["Date"] = df[date_c].astype(str).str.replace('00:00:00', '').str.strip()
        df_clean["Narration"] = df[desc_c].astype(str).str.replace('\n', ' ').str.replace('  ', ' ').str.strip()
        df_clean["Debit"] = df[debit_c]
        df_clean["Credit"] = df[credit_c]
        df_clean["Tally Ledger"] = "🟡 Suspense A/c"

        metrics["dr_count"] = int((df_clean["Debit"] > 0).sum())
        metrics["cr_count"] = int((df_clean["Credit"] > 0).sum())
            
        return df_clean, metrics
