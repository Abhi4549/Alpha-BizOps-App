import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

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

def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: 
        passwords.append(custom_pwd.strip())
    if dob:
        d_str = dob.strftime("%d")
        m_str = dob.strftime("%m")
        y_full = dob.strftime("%Y")
        y_short = dob.strftime("%y")
        passwords.extend([f"{d_str}{m_str}{y_full}", f"{d_str}{m_str}{y_short}"])
        if name:
            name_clean = re.sub(r'[^a-zA-Z]', '', name)
            if len(name_clean) >= 4:
                f4l = name_clean[:4].lower()
                f4u = name_clean[:4].upper()
                passwords.extend([f"{f4l}{d_str}{m_str}", f"{f4u}{d_str}{m_str}", f"{f4l}{d_str}{m_str}{y_full}"])
    if pan: 
        passwords.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(passwords))

def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    file.seek(0)
    
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        
        is_encrypted = pdf_reader.is_encrypted
        matched_password = None
        
        if is_encrypted:
            for pwd in password_list:
                if pwd:
                    try:
                        if pdf_reader.decrypt(pwd):
                            matched_password = pwd
                            break
                    except Exception: 
                        pass
            if not matched_password: 
                return None, "PDF is locked. Auto-Unlock failed."
            
    except Exception as e: 
        return None, f"Decryption Engine Error: {str(e)}"

    try:
        pdf_file_object = io.BytesIO(pdf_bytes)
        
        with pdfplumber.open(pdf_file_object, password=matched_password) as pdf:
            date_pattern = re.compile(r'(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')
            
            ignore_kws = [
                'opening balance', 'closing balance', 'brought forward', 'carried forward', 
                'total debits', 'total credits', 'statement period', 'generated on', 
                'page total', 'grand total', 'summary of', 'authorized sign', 'stamp'
            ]
            
            current_txn = None
            
            for page_num
