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
# 2. SMART PASSWORD ENGINE (INDIAN BANKS)
# ==========================================
def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: passwords.append(custom_pwd.strip())
    
    if dob:
        d_str = dob.strftime("%d")
        m_str = dob.strftime("%m")
        y_full = dob.strftime("%Y")
        y_short = dob.strftime("%y")
        passwords.extend([f"{d_str}{m_str}{y_full}", f"{d_str}{m_str}{y_short}"])
        
        if name:
            name_clean = re.sub(r'[^a-zA-Z]', '', name)
            if len(name_clean) >= 4:
                first_4_lower = name_clean[:4].lower()
                first_4_upper = name_clean[:4].upper()
                passwords.extend([
                    f"{first_4_lower}{d_str}{m_str}",
                    f"{first_4_upper}{d_str}{m_str}",
                    f"{first_4_lower}{d_str}{m_str}{y_full}"
                ])
                
    if pan:
        passwords.extend([pan.lower().strip(), pan.upper().strip()])
        
    return list(set(passwords))

# ==========================================
# 3. BACKEND: PDF PARSER WITH PyPDF2 BYPASS
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    
    matched_pwd = None
    
    # ⚡ ENGINE 1: PyPDF2 SECURITY BYPASS (No Else block needed)
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if not pwd: 
                    continue
                try:
                    if pdf_reader.decrypt(pwd): 
                        unlocked = True
                        matched_pwd = pwd
                        break
                except Exception:
                    continue
            
            if not unlocked:
                return None, "PDF is locked. Auto-Unlock failed. Please provide exact Password/PAN/DOB."
                
    except Exception as e:
        return None, f"Decryption Engine Error: {str(e)}"

    # ⚡ ENGINE 2: PDFPLUMBER EXTRACTION WITH YOUR EXACT LOGIC
    try:
        original_pdf_stream = io.BytesIO(pdf_bytes)
        with pdfplumber.open(original_pdf_stream, password=matched_pwd) as pdf:
            date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')

            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: 
                    text = page.extract_text()
                if not text: 
                    continue
                
                lines = text.split('\n')

                current_txn = None
                for line in lines:
                    line = line.strip()
                    if not line: 
                        continue

                    match = date_pattern.search(line)
                    if match:
                        if current_txn: 
                            raw_transactions.append(current_txn)

                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        date_str = re.sub(r'/+', '/', date_str)
                        
                        rem = line[len(match.group(0)):].strip()

                        parts = rem.split()
                        numbers = []
                        narration_words = []

                        for part in parts:
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part):
                                if cl_part.startswith('0') and '.' not in cl_part and len(cl_part) >= 4:
                                    narration_words.append(part)
                                else:
                                    numbers.append(float(cl_part))
                            else:
                                narration_words.append(part)

                        narration = " ".join(narration_words)

                        balance = 0.0
                        txn_amount = 0.0
                        if len(numbers) >= 1: balance = numbers[-1] 
                        if len(numbers) >= 2: txn_amount = numbers[-2] 

                        current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}

                    else:
                        if current_txn and len(line) > 2:
                            ignore_words = ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing', 'brought forward']
                            if not any(ig in line.lower() for ig in ignore_words):
                                clean_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_parts: 
                                    current_txn["Narration"] += " " + " ".join(clean_parts)

                if current_txn: 
                    raw_transactions.append(current_txn)

        if not raw_transactions:
            return None, "Document unlocked, but no transactions found. Bank format might be unsupported or it's a scanned photo."

        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                diff = round(curr_bal - prev_bal, 2)

                if diff > 0:
                    curr["Credit"] = diff
                    curr["Debit"] = 0.0
                elif diff < 0:
                    curr["Debit"] = abs(diff)
                    curr["Credit"] = 0.0
                else:
                    curr["Credit"] = curr["Amount"] if curr["Amount"] > 0 else 0.0
            else:
                narration_upper = curr["Narration"].upper()
                if any(kw in narration_upper for kw in ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]):
                    curr["Debit"] = curr["Amount"]
                else:
                    curr["Credit"] = curr["Amount"]

        return raw_transactions, "Success"
    except Exception as e: 
        return None, f"Parsing Error: {str(e)}"

# ==========================================
# 4. EXCEL CSV PARSER
# ==========================================
def process_excel_parser(file):
    raw_transactions = []
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, skip_
