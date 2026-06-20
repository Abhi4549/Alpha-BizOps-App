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
    file.seek(0)
    
    unlocked_pdf_stream = None
    matched_pwd = None
    
    # ⚡ ENGINE 1: PyPDF2 SECURITY BYPASS
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
            
            # 🔥 THE FIX: Removed PdfWriter. Just pass original bytes!
            unlocked_pdf_stream = io.BytesIO(pdf_bytes)
        else:
