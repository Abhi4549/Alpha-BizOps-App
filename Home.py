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
# 3. BACKEND: PDF PARSER
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    file.seek(0)
    
    # Simple check for encryption
    matched_pwd = None
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        if pdf_reader.is_encrypted:
            for pwd in password_list:
                if pwd and pdf_reader.decrypt(pwd):
                    matched_pwd = pwd
                    break
            if not matched_pwd:
                return None, "PDF is locked. Please provide correct Password/PAN/DOB."
    except Exception as e:
        return None, f"Decryption Error: {str(e)}"

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=matched_pwd) as pdf:
            date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')

            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line: continue

                    match = date_pattern.search(line)
                    if match:
                        if current_txn := locals().get('current_txn'): 
                            raw_transactions.append(current_txn)

                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        rem = line[len(match.group(0)):].strip()
                        parts = rem.split()
                        
                        numbers = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                        
                        narration = " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))])
                        
                        balance = numbers[-1] if numbers else 0.0
                        amount = numbers[-2] if len(numbers) >= 2 else 0.0
                        
                        current_txn = {"Date": date_str, "Narration": narration, "Amount": amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}
                    
                    elif current_txn := locals().get('current_txn'):
                        current_txn["Narration"] += " " + line

                if current_txn := locals().get('current_txn'): 
                    raw_transactions.append(current_txn)

        if not raw_transactions: return None, "No transactions found."
        
        # Math Logic
        for i, curr in enumerate(raw_transactions):
            if i > 0:
                diff = round(curr["Balance"] - raw_transactions[i-1]["Balance"], 2)
                if diff > 0: curr["Credit"] = curr["Amount"] if curr["Amount"] > 0 else diff
                else: curr["Debit"] = curr["Amount"] if curr["Amount"] > 0 else abs(diff)
            else:
                curr["Credit"] = curr["Amount"]
        return raw_transactions, "Success"
    except Exception as e:
        return None, f"Parsing Error: {str(e)}"

# ==========================================
# 4. EXCEL PARSER
# ==========================================
def process_excel_parser(file):
    try:
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        return df.to_dict('records'), "Success"
    except Exception as e:
        return None, str(e)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================================
# 5. UI
# ==========================================
uploaded_file = st.file_uploader("Upload Statement", type=['pdf', 'xlsx', 'csv'])
if uploaded_file:
    c1, c2, c3, c4 = st.columns(4)
    name = c1.text_input("Name")
    dob = c2.date_input("DOB", value=None)
    pan = c3.text_input("PAN")
    pwd = c4.text_input("Password", type="password")
    
    if st.button("Extract"):
        pwds = generate_bank_passwords(name, dob, pan, pwd)
        data, status = process_mathematical_parser(uploaded_file, pwds) if uploaded_file.name.endswith('.pdf') else process_excel_parser(uploaded_file)
        if data:
            st.session_state['raw_extracted_data'] = pd.DataFrame(data)
            st.success("Extracted!")
        else:
            st.error(status)
