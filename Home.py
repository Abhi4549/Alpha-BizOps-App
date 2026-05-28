import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. MEMORY & UI CONFIGURATION (THE BRIDGE)
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
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Custom Date Filter | Auto-Sync to Ledger Mapper</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: PDF & EXCEL PARSERS
# ==========================================
def process_mathematical_parser(file, password=""):
    raw_transactions = []
    try:
        with pdfplumber.open(file, password=password) as pdf:
            date_pattern = re.compile(r'^(\d{1,2}[/\-\s][a-zA-Z]{3}[/\-\s]\d{2,4}|\d{1,2}[/\-\s]\d{1,2}[/\-\s]\d{2,4})')
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: continue
                lines = text.split('\n')
                current_txn = None
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    match = date_pattern.search(line)
                    if match:
                        if current_txn: raw_transactions.append(current_txn)
                        date_str = match.group(1)
                        rem = line[len(date_str):].strip()
                        parts = rem.split()
                        amount_list = []
                        narration_parts = []
                        for i in range(len(parts)-1, -1, -1):
                            part = parts[i]
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part): amount_list.insert(0, float(cl_part))
                            else:
                                narration_parts = parts[:i+1]
                                break
                        narration = " ".join(narration_parts)
                        balance = 0.0
                        txn_amount = 0.0
                        if len(amount_list) > 0: balance = amount_list[-1]
                        if len(amount_list) > 1: txn_amount = amount_list[-2] 
                        current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}
                    else:
                        if current_txn and len(line) > 2:
                            ignore = ['page', 'balance', 'total', 'statement', 'branch']
                            if not any(ig in line.lower() for ig in ignore):
                                clean_line_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_line_parts: current_txn["Narration"] += " " + " ".join(clean_line_parts)
                if current_txn: raw_transactions.append(current_txn)

        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            amt = curr["Amount"]
            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                if round(prev_bal + amt, 2) == round(curr_bal, 2): curr["Credit"] = amt
                elif round(prev_bal - amt, 2) == round(curr_bal, 2): curr["Debit"] = amt
                else:
                    diff = round(curr_bal - prev_bal, 2)
                    if diff > 0: curr["Credit"] = amt
                    elif diff < 0: curr["Debit"] = amt
            else:
                if "RTGS" in curr["Narration"].upper() or "NEFT" in curr["Narration"].upper(): curr["Debit"] = amt 
                else: curr["Credit"] = amt 
                    
        return raw_transactions, "Success"
    except Exception as e: return None, f"PDF Error: {str(e)}"

def process_excel_parser(file, password=""):
    raw_transactions = []
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, skip_blank_lines=True)
        else:
            if password:
                import msoffcrypto
                decrypted_file = io.BytesIO()
                office_file = msoffcrypto.OfficeFile(file)
                office_file.load_key(password=password)
                office_file.decrypt(decrypted_file)
                decrypted_file.seek(0)
                df = pd.read_excel(decrypted_file)
            else:
                df = pd.read_excel(file)
            
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df = df.reset_index(drop=True)
        
        header_idx = -1
        for i in range(min(20, len(df))):
            row_str = ' '.join(str(x).lower() for x in df.iloc[i].values)
            if 'date' in row_str and ('narration' in row_str or 'particulars' in row_str or 'description' in row_str):
                header_idx = i
                break
                
        if header_idx != -1:
            df.columns = df.iloc[header_idx]
            df = df.iloc
