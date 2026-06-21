import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

# --- UI SETTINGS ---
st.set_page_config(layout="wide")
st.markdown("""<style>
    .metric-value { font-size: 18px !important; font-weight: bold; }
    .metric-label { font-size: 12px !important; color: #6B7280; }
</style>""", unsafe_allow_html=True)

# --- ENGINE ---
def process_data(file, pwd_list):
    try:
        # PDF logic
        pdf_bytes = file.read()
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pwd = None
        if reader.is_encrypted:
            for p in pwd_list:
                try:
                    if reader.decrypt(p): pwd = p; break
                except: continue
        
        data = []
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
            for page in pdf.pages:
                for line in page.extract_text().split('\n'):
                    # Regex for Date (matches DD/MM/YYYY, DD-MM-YY, DD.MM.YYYY)
                    if re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', line):
                        parts = line.split()
                        nums = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                        if len(nums) >= 1:
                            data.append({
                                "Date": re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', line).group(0),
                                "Narration": line,
                                "Balance": nums[-1]
                            })
        
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # Calculate Dr/Cr
        df['Debit'], df['Credit'] = 0.0, 0.0
        for i in range(1, len(df)):
            diff = round(df.loc[i, 'Balance'] - df.loc[i-1, 'Balance'], 2)
            if diff < 0: df.loc[i, 'Debit'] = abs(diff)
            elif diff > 0: df.loc[i, 'Credit'] = diff
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- UI ---
uploaded = st.file_uploader("Upload PDF", type=['pdf'])
name, dob, pan, custom = st.columns(4)[0].text_input("Name"), st.columns(4)[1].date_input("DOB", None), st.columns(4)[2].text_input("PAN"), st.columns(4)[3].text_input("Password", type="password")

if st.button("🚀 Process"):
    if uploaded:
        # Generate Pwd list logic...
        df = process_data(uploaded, [custom] if custom else []) # simplified for testing
        if df is not None:
            st.session_state['data'] = df
            st.success("Extracted!")

if 'data' in st.session_state:
    df = st.session_state['data']
    filt = df # Add your date filter logic here
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="metric-label">Debits ({len(filt[filt["Debit"]>0])})</div><div class="metric-value">₹{filt["Debit"].sum():,.2f}</div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-label">Credits ({len(filt[filt["Credit"]>0])})</div><div class="metric-value">₹{filt["Credit"].sum():,.2f}</div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-label">Opening Bal</div><div class="metric-value">₹{filt.iloc[0]["Balance"]-(filt.iloc[0]["Credit"]-filt.iloc[0]["Debit"]):,.2f}</div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-label">Closing Bal</div><div class="metric-value">₹{filt.iloc[-1]["Balance"]:,.2f}</div>', unsafe_allow_html=True)
    st.dataframe(filt, use_container_width=True)
