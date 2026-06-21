import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

# --- UI CONFIG ---
st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏦 Alpha BizOps Hub</h1>", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state['raw_data'] = None

# --- ENGINE: PASSWORD GENERATOR ---
def generate_passwords(name, dob, pan, custom):
    pwds = [custom] if custom else []
    if dob:
        d, m, y, ys = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y"), dob.strftime("%y")
        pwds.extend([f"{d}{m}{y}", f"{d}{m}{ys}"])
        if name:
            n = re.sub(r'[^a-zA-Z]', '', name)[:4].lower()
            pwds.extend([f"{n}{d}{m}", f"{n.upper()}{d}{m}", f"{n}{d}{m}{y}"])
    if pan: pwds.extend([pan.lower(), pan.upper()])
    return list(set(filter(None, pwds)))

# --- ENGINE: PDF PARSER ---
def process_pdf(file, pwd_list):
    pdf_bytes = file.read()
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    pwd = None
    if reader.is_encrypted:
        for p in pwd_list:
            if reader.decrypt(p): 
                pwd = p; break
    
    data = []
    with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
        date_pat = re.compile(r'^(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})')
        for page in pdf.pages:
            for line in page.extract_text().split('\n'):
                line = line.strip()
                match = date_pat.search(line)
                if match:
                    parts = line.split()
                    nums = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                    data.append({
                        "Date": match.group(1),
                        "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]),
                        "Balance": nums[-1] if nums else 0.0
                    })
    
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df['Debit'], df['Credit'] = 0.0, 0.0
    
    # Calculate Dr/Cr logic
    for i in range(1, len(df)):
        diff = round(df.loc[i, 'Balance'] - df.loc[i-1, 'Balance'], 2)
        if diff < 0: df.loc[i, 'Debit'] = abs(diff)
        elif diff > 0: df.loc[i, 'Credit'] = diff
    return df

# --- UI: INPUTS ---
uploaded = st.file_uploader("Upload Statement", type=['pdf'])
c1, c2, c3, c4 = st.columns(4)
name, dob, pan, custom = c1.text_input("Name"), c2.date_input("DOB", None), c3.text_input("PAN"), c4.text_input("Custom Pwd", type="password")

if st.button("🚀 Process"):
    with st.spinner("Extracting..."):
        df = process_pdf(uploaded, generate_passwords(name, dob, pan, custom))
        st.session_state['raw_data'] = df
        st.success("Extracted!")

# --- UI: DASHBOARD & FILTER ---
if st.session_state['raw_data'] is not None:
    df = st.session_state['raw_data']
    st.write("---")
    f_date, t_date = st.columns(2)
    start = f_date.date_input("Start", df['Date'].min())
    end = t_date.date_input("End", df['Date'].max())
    
    filtered = df[(df['Date'].dt.date >= start) & (df['Date'].dt.date <= end)]
    
    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Debits", f"₹{filtered['Debit'].sum():,.2f}", f"{len(filtered[filtered['Debit']>0])} Txns")
    m2.metric("Credits", f"₹{filtered['Credit'].sum():,.2f}", f"{len(filtered[filtered['Credit']>0])} Txns")
    m3.metric("Opening", f"₹{filtered.iloc[0]['Balance'] - (filtered.iloc[0]['Credit'] - filtered.iloc[0]['Debit']):,.2f}")
    m4.metric("Closing", f"₹{filtered.iloc[-1]['Balance']:,.2f}")
    
    st.dataframe(filtered, use_container_width=True)
    st.download_button("Download CSV", filtered.to_csv(index=False), "data.csv")
