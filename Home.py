import streamlit as st
import pandas as pd
import pdfplumber
import pikepdf
import io
import re
import datetime

# ==========================================
# 1. UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")

# ==========================================
# 2. ENHANCED PASSWORD ENGINE
# ==========================================
def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: passwords.append(custom_pwd.strip())
    
    if dob:
        d, m, y, y_short = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y"), dob.strftime("%y")
        passwords.extend([f"{d}{m}{y}", f"{d}{m}{y_short}"])
        
        if name:
            name_clean = re.sub(r'[^a-zA-Z]', '', name)
            if len(name_clean) >= 4:
                n4 = name_clean[:4].lower()
                n4u = name_clean[:4].upper()
                passwords.extend([f"{n4}{d}{m}", f"{n4u}{d}{m}", f"{n4}{d}{m}{y}", f"{n4}{d}{m}{y_short}"])
    
    if pan:
        passwords.extend([pan.lower().strip(), pan.upper().strip()])
        
    return list(set(passwords))

# ==========================================
# 3. ROBUST PDF PARSER (PIKEPDF ENGINE)
# ==========================================
def process_pdf(file, password_list):
    file.seek(0)
    pdf_bytes = file.read()
    
    # Try unlocking with pikepdf
    unlocked_pdf = None
    for pwd in password_list:
        try:
            unlocked_pdf = pikepdf.open(io.BytesIO(pdf_bytes), password=pwd)
            break
        except:
            continue
            
    if not unlocked_pdf:
        return None, "Auto-Unlock failed. Verify Password/PAN/DOB."

    # Extract text using pdfplumber on the unlocked stream
    raw_transactions = []
    try:
        with pdfplumber.open(unlocked_pdf) as pdf:
            date_pattern = re.compile(r'(\d{1,2}[\s/\-]\d{1,2}[\s/\-]\d{2,4})')
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split('\n'):
                    match = date_pattern.search(line)
                    if match:
                        # Logic to split date, narration, and balance
                        parts = line.split()
                        # Simplified extraction for demo; replace with your specific bank regex
                        raw_transactions.append({"Date": parts[0], "Narration": " ".join(parts[1:-2]), "Amount": 0.0, "Balance": float(parts[-1].replace(',',''))})
    except Exception as e:
        return None, str(e)
    
    return raw_transactions, "Success"

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
st.title("🏦 Alpha BizOps Hub: Professional Parser")

uploaded_file = st.file_uploader("Upload Statement", type=['pdf'])
col1, col2, col3 = st.columns(3)
name = col1.text_input("Name")
dob = col2.date_input("DOB", None)
pan = col3.text_input("PAN")

if st.button("Extract Data"):
    if uploaded_file:
        pwds = generate_bank_passwords(name, dob, pan, "")
        data, status = process_pdf(uploaded_file, pwds)
        if data:
            st.success("Extracted!")
            st.dataframe(pd.DataFrame(data))
        else:
            st.error(status)
