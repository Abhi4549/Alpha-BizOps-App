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
# 2. SMART PASSWORD ENGINE
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
# 3. BACKEND: MEMORY EFFICIENT PDF PARSER
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    correct_password = ""
    
    # ⚡ ENGINE 1: FIND PASSWORD
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if not pwd: continue
                try:
                    if pdf_reader.decrypt(pwd): 
                        correct_password = pwd
                        unlocked = True
                        break
                except Exception: continue
            if not unlocked:
                return None, "PDF is locked. Auto-Unlock failed."
    except Exception as e:
        return None, f"Decryption Engine Error: {str(e)}"

    # ⚡ ENGINE 2: MEMORY EFFICIENT EXTRACTION
    try:
        original_stream = io.BytesIO(pdf_bytes)
        date_pattern = re.compile(r'^[^a-zA-Z0-9]*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')

        with pdfplumber.open(original_stream, password=correct_password if correct_password else None) as pdf:
            current_txn = None
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line: continue
                    match = date_pattern.search(line)
                    if match:
                        if current_txn: raw_transactions.append(current_txn)
                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        rem = line[len(match.group(0)):].strip()
                        parts = rem.split()
                        numbers = [float(p.replace(',', '').replace('Cr', '').replace('Dr', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', '').replace('Cr', '').replace('Dr', ''))]
                        
                        current_txn = {
                            "Date": date_str, 
                            "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', '').replace('Cr', '').replace('Dr', ''))]), 
                            "Amount": numbers[-2] if len(numbers) >= 2 else 0.0, 
                            "Balance": numbers[-1] if len(numbers) >= 1 else 0.0,
                            "Debit": 0.0, "Credit": 0.0
                        }
                    elif current_txn:
                        current_txn["Narration"] += " " + line
            
            if current_txn: raw_transactions.append(current_txn)

        # ⚡ ENGINE 3: REVERSE MATH
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            if i > 0:
                diff = round(curr["Balance"] - raw_transactions[i-1]["Balance"], 2)
                if diff > 0: curr["Credit"], curr["Debit"] = diff, 0.0
                elif diff < 0: curr["Debit"], curr["Credit"] = abs(diff), 0.0
        
        return raw_transactions, "Success"
    except Exception as e: 
        return None, f"Parsing Error: {str(e)}"

# ==========================================
# 4. EXCEL/CSV PARSER & UI (REMAINS SAME)
# ==========================================
def process_excel_parser(file):
    # (Reuse your existing excel logic here)
    return [], "Success"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 5. UI & DASHBOARD (REMAINS SAME)
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])
# ... (rest of your UI code remains same)
