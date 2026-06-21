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

st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK STATEMENT TO TALLY EXCEL</div>', unsafe_allow_html=True)

# ==========================================
# 2. SMART PASSWORD ENGINE
# ==========================================
def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: passwords.append(custom_pwd.strip())
    if dob:
        d, m, y_full, y_short = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y"), dob.strftime("%y")
        passwords.extend([f"{d}{m}{y_full}", f"{d}{m}{y_short}"])
        if name:
            n = re.sub(r'[^a-zA-Z]', '', name)[:4]
            passwords.extend([f"{n.lower()}{d}{m}", f"{n.upper()}{d}{m}", f"{n.lower()}{d}{m}{y_full}"])
    if pan: passwords.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(passwords))

# ==========================================
# 3. BACKEND: OPTIMIZED PDF PARSER
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    correct_password = None
    
    # Unlock Engine
    temp_stream = io.BytesIO(pdf_bytes)
    reader = PyPDF2.PdfReader(temp_stream)
    if reader.is_encrypted:
        for pwd in password_list:
            try:
                if reader.decrypt(pwd): 
                    correct_password = pwd
                    break
            except: continue
        if not correct_password: return None, "Password incorrect or PDF corrupted."

    # Extraction Engine
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=correct_password) as pdf:
            date_pattern = re.compile(r'^(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})')
            current_txn = None
            
            for page in pdf.pages:
                for line in page.extract_text().split('\n'):
                    line = line.strip()
                    match = date_pattern.search(line)
                    if match:
                        if current_txn: raw_transactions.append(current_txn)
                        parts = line.split()
                        nums = [float(p.replace(',','')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                        current_txn = {
                            "Date": match.group(1),
                            "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]),
                            "Amount": nums[-2] if len(nums) >= 2 else 0.0,
                            "Balance": nums[-1] if len(nums) >= 1 else 0.0,
                            "Debit": 0.0, "Credit": 0.0
                        }
                    elif current_txn:
                        current_txn["Narration"] += " " + line
            if current_txn: raw_transactions.append(current_txn)
            
        # Reverse Math Logic
        for i in range(len(raw_transactions)):
            if i > 0:
                diff = round(raw_transactions[i]["Balance"] - raw_transactions[i-1]["Balance"], 2)
                raw_transactions[i]["Credit"] = diff if diff > 0 else 0.0
                raw_transactions[i]["Debit"] = abs(diff) if diff < 0 else 0.0
                
        return raw_transactions, "Success"
    except Exception as e: return None, str(e)

# ==========================================
# 4. UI: EXECUTION BLOCK
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement", type=['pdf'])
if uploaded_file:
    name = st.text_input("Name")
    dob = st.date_input("DOB", None)
    pan = st.text_input("PAN")
    
    if st.button("🚀 Process Data"):
        with st.spinner("Processing..."):
            pwd_list = generate_bank_passwords(name, dob, pan, "")
            data, status = process_mathematical_parser(uploaded_file, pwd_list)
            if data:
                st.session_state['raw_extracted_data'] = pd.DataFrame(data)
                st.success("Extracted successfully!")
                st.dataframe(st.session_state['raw_extracted_data'])
            else:
                st.error(status)
