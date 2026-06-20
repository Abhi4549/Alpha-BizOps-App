import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

# ==========================================
# 1. PASSWORD & PARSING ENGINE
# ==========================================
def get_pwds(name, dob, pan, cust_pwd):
    pwds = [cust_pwd.strip()] if cust_pwd else []
    if dob:
        d, m, y = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y")
        pwds.extend([f"{d}{m}{y}", f"{d}{m}{y[2:]}"])
        if name:
            n = re.sub(r'[^a-zA-Z]', '', name)[:4]
            pwds.extend([f"{n.lower()}{d}{m}", f"{n.upper()}{d}{m}"])
    if pan: pwds.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(pwds))

def pro_pdf_parser(file, pwds):
    pdf_bytes = file.read()
    file.seek(0)
    matched_pwd = None
    
    # Tala kholne ki koshish (PyPDF2)
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    if reader.is_encrypted:
        for p in pwds:
            if reader.decrypt(p):
                matched_pwd = p
                break
        if not matched_pwd:
            return None, "🔒 Password galat hai ya file lock nahi khul rahi."

    # Native extraction (Accuracy ke liye)
    raw_txns = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=matched_pwd) as pdf:
            dt_pat = re.compile(r'(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: continue
                
                curr = None
                for line in text.split('\n'):
                    line = line.strip()
                    match = dt_pat.search(line)
                    if match:
                        if curr: raw_txns.append(curr)
                        rem = line[match.end():].strip()
                        parts = rem.split()
                        nums = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                        curr = {
                            "Date": match.group(1),
                            "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]),
                            "Balance": nums[-1] if nums else 0.0,
                            "Amount": nums[-2] if len(nums) >= 2 else 0.0
                        }
                    elif curr:
                        if not any(k in line.lower() for k in ['page', 'balance', 'total']):
                            curr["Narration"] += " " + line
                if curr: raw_txns.append(curr)
        
        df = pd.DataFrame(raw_txns)
        if df.empty: return None, "No transactions found."
        
        # Deduplication
        df = df.drop_duplicates(subset=['Date', 'Narration', 'Balance'])
        
        # Math Routing
        df['Debit'], df['Credit'] = 0.0, 0.0
        for i in range(len(df)):
            if i > 0:
                diff = round(df.iloc[i]['Balance'] - df.iloc[i-1]['Balance'], 2)
                df.at[i, 'Credit'] = df.iloc[i]['Amount'] if diff > 0 else 0.0
                df.at[i, 'Debit'] = df.iloc[i]['Amount'] if diff < 0 else abs(diff)
            else:
                df.at[i, 'Credit'] = df.iloc[i]['Amount']
        return df, "Success"
    except Exception as e: return None, str(e)

# ==========================================
# 2. UI
# ==========================================
uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
if uploaded_file:
    c1, c2, c3, c4 = st.columns(4)
    name, dob, pan, pwd = c1.text_input("Name"), c2.date_input("DOB", value=None), c3.text_input("PAN"), c4.text_input("Pwd", type="password")
    
    if st.button("🚀 Process"):
        df, stat = pro_pdf_parser(uploaded_file, get_pwds(name, dob, pan, pwd))
        if df is not None:
            # Metrics
            cols = st.columns(3)
            cols[0].metric("Total Debits", f"₹ {df['Debit'].sum():,.2f}")
            cols[1].metric("Total Credits", f"₹ {df['Credit'].sum():,.2f}")
            cols[2].metric("Txns", len(df))
            st.dataframe(df)
        else: st.error(stat)
