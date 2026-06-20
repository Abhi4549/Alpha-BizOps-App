import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

# ==========================================
# 1. MEMORY & UI CONFIGURATION
# ==========================================
if 'raw_extracted_data' not in st.session_state:
    st.session_state['raw_extracted_data'] = None
if 'cleaned_data' not in st.session_state:
    st.session_state['cleaned_data'] = None

st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK STATEMENT TO TALLY EXCEL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Smart Auto-Unlock | Universal Format</div>', unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS (To Prevent Syntax Errors)
# ==========================================
def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: passwords.append(custom_pwd.strip())
    if dob:
        d_str, m_str = dob.strftime("%d"), dob.strftime("%m")
        y_full, y_short = dob.strftime("%Y"), dob.strftime("%y")
        passwords.extend([f"{d_str}{m_str}{y_full}", f"{d_str}{m_str}{y_short}"])
        if name:
            name_clean = re.sub(r'[^a-zA-Z]', '', name)
            if len(name_clean) >= 4:
                f4l, f4u = name_clean[:4].lower(), name_clean[:4].upper()
                passwords.extend([f"{f4l}{d_str}{m_str}", f"{f4u}{d_str}{m_str}", f"{f4l}{d_str}{m_str}{y_full}"])
    if pan: passwords.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(passwords))

def extract_pdf_data_safely(pdf_stream, matched_pwd):
    raw_transactions = []
    date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')
    ignore_kws = ['opening balance', 'closing balance', 'brought forward', 'carried forward', 'total debits', 'total credits', 'statement period', 'generated on', 'page total', 'grand total', 'summary of', 'closing bal', 'opening bal']
    
    with pdfplumber.open(pdf_stream, password=matched_pwd) as pdf:
        current_txn = None
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text: text = page.extract_text()
            if not text: continue
            
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                
                match = date_pattern.search(line)
                if match:
                    if current_txn: raw_transactions.append(current_txn)
                    
                    date_str = re.sub(r'/+', '/', re.sub(r'[\s\.\-]', '/', match.group(1)))
                    parts = line[len(match.group(0)):].strip().split()
                    
                    nums, narr = [], []
                    for part in reversed(parts):
                        cp = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                        if re.match(r'^\d+(\.\d+)?$', cp) and len(nums) < 3:
                            if cp.startswith('0') and '.' not in cp and len(cp) >= 4: narr.insert(0, part)
                            else: nums.insert(0, float(cp))
                        else: narr.insert(0, part)
                    
                    if len(nums) >= 1 and not any(kw in line.lower() for kw in ignore_kws):
                        current_txn = {
                            "Date": date_str, "Narration": " ".join(narr), 
                            "Amount": nums[-2] if len(nums) >= 2 else 0.0, 
                            "Balance": nums[-1], "Debit": 0.0, "Credit": 0.0
                        }
                else:
                    if current_txn and len(line) > 2:
                        if not any(ig in line.lower() for ig in ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing']):
                            cps = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                            if cps: current_txn["Narration"] += " " + " ".join(cps)
                            
        if current_txn: raw_transactions.append(current_txn)
    return raw_transactions

# ==========================================
# 3. BACKEND: MAIN PARSERS
# ==========================================
def process_mathematical_parser(file, password_list):
    file.seek(0)
    pdf_bytes = file.read()
    matched_password = '' 
    
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if pwd:
                    try:
                        if pdf_reader.decrypt(pwd): 
                            unlocked, matched_password = True, pwd
                            break
                    except Exception: pass
            if not unlocked: return None, "PDF is locked. Auto-Unlock failed."
    except Exception as e: return None, f"Decryption Engine Error: {str(e)}"

    try:
        raw_transactions = extract_pdf_data_safely(io.BytesIO(pdf_bytes), matched_password)
        if not raw_transactions: return None, "Document unlocked, but no transactions found."

        cleaned_final_ledger = []
        seen_entries = set()
        txn_kws = ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]

        for curr in raw_transactions:
            fingerprint = f"{curr['Date']}_{curr['Balance']}_{curr['Amount']}_{curr['Narration'][:20]}"
            if fingerprint in seen_entries: continue
            seen_entries.add(fingerprint)

            if len(cleaned_final_ledger) > 0:
                diff = round(curr["Balance"] - cleaned_final_ledger[-1]["Balance"], 2)
                if diff > 0: curr["Credit"], curr["Debit"] = (curr["Amount"] if curr["Amount"] > 0 else abs(diff)), 0.0
                elif diff < 0: curr["Debit"], curr["Credit"] = (curr["Amount"] if curr["Amount"] > 0 else abs(diff)), 0.0
                else: curr["Credit"], curr["Debit"] = (curr["Amount"] if curr["Amount"] > 0 else 0.0), 0.0
            else:
                if any(kw in curr["Narration"].upper() for kw in txn_kws): curr["Debit"], curr["Credit"] = curr["Amount"], 0.0
                else: curr["Credit"], curr["Debit"] = curr["Amount"], 0.0
                    
            cleaned_final_ledger.append(curr)
        return cleaned_final_ledger, "Success"
    except Exception as e: return None, f"Parsing Error: {str(e)}"

def process_excel_parser(file):
    try:
        df = pd.read_csv(file, skip_blank_lines=True) if file.name.endswith('.csv') else pd.read_excel(file)
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        header_idx = -1
        for i in range(min(20, len(df))):
            rstr = ' '.join(str(x).lower() for x in df.iloc[i].values)
            if 'date' in rstr and ('narration' in rstr or 'particulars' in rstr or 'description' in rstr):
                header_idx = i
                break
                
        if header_idx != -1:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        cols = df.columns
        d_col = next((c for c in cols if 'date' in c), None)
        n_col = next((c for c in cols if any(x in c for x in ['narration', 'particulars', 'description'])), None)
        dr_col = next((c for c in cols if any(x in c for x in ['debit', 'withdrawal', 'dr'])), None)
        cr_col = next((c for c in cols if any(x in c for x in ['credit', 'deposit', 'cr'])), None)
        bal_col = next((c for c in cols if 'balance' in c), None)
        
        if not d_col or not n_col: return None, "Format error: Date/Narration not found."
            
        raw_txns = []
        for _, row in df.iterrows():
            rd = row[d_col]
            if pd.isna(rd) or str(rd).strip().lower() == 'nan': continue
            
            d_val = rd.strftime('%d/%m/%Y') if isinstance(rd, pd.Timestamp) else str(rd).split(' ')[0]
            n_val = str(row[n_col]).strip()
            if n_val.lower() == 'nan': n_val = ""
            if any(kw in n_val.lower() for kw in ['total', 'opening balance', 'closing balance', 'brought forward']): continue
            
            def cln(v):
                try: return float(str(v).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip())
                except: return 0.0
                    
            dr_v = cln(row[dr_col]) if dr_col else 0.0
            cr_v = cln(row[cr_col]) if cr_col else 0.0
            bal_v = cln(row[bal_col]) if bal_col else 0.0
                
            if dr_v > 0 or cr_v > 0 or bal_v > 0:
                raw_txns.append({"Date": d_val, "Narration": n_val, "Debit": dr_v, "Credit": cr_v, "Balance": bal_v})
        return raw_txns, "Success"
    except Exception as e: return None, f"Excel Error: {str(e)}"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 4. UI: DATA EXTRACTION BLOCK
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])

if uploaded_file:
    st.markdown("### 🔐 Smart Auto-Unlock (For
