import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

st.set_page_config(layout="wide")
st.markdown("<style>.metric-value { font-size: 18px !important; font-weight: bold; } .metric-label { font-size: 12px !important; color: #6B7280; }</style>", unsafe_allow_html=True)

def generate_passwords(name, dob, pan, custom):
    pwds = [custom] if custom else []
    if dob:
        d, m, y, ys = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y"), dob.strftime("%y")
        pwds.extend([f"{d}{m}{y}", f"{d}{m}{ys}"])
        if name:
            n = re.sub(r'[^a-zA-Z]', '', name)[:4].lower()
            pwds.extend([f"{n}{d}{m}", f"{n.upper()}{d}{m}"])
    if pan: pwds.extend([pan.lower(), pan.upper()])
    return list(set(filter(None, pwds)))

def process_file(file, pwd_list):
    try:
        if file.name.endswith(('.xlsx', '.xls', '.csv')):
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            return df.fillna(0)

        # PDF Logic
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
            date_pat = re.compile(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})')
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split('\n'):
                    match = date_pat.search(line.strip())
                    if match:
                        parts = line.split()
                        nums = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                        data.append({
                            "Date": match.group(1),
                            "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]),
                            "Balance": nums[-1] if nums else 0.0
                        })
        
        df = pd.DataFrame(data)
        if df.empty: raise ValueError("No transaction data found.")
        
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df['Debit'], df['Credit'] = 0.0, 0.0
        for i in range(1, len(df)):
            diff = round(df.loc[i, 'Balance'] - df.loc[i-1, 'Balance'], 2)
            if diff < 0: df.loc[i, 'Debit'] = abs(diff)
            elif diff > 0: df.loc[i, 'Credit'] = diff
        return df
    except Exception as e:
        st.error(f"Processing Error: {e}")
        return None

# UI Execution
uploaded = st.file_uploader("Upload File", type=['pdf', 'xlsx', 'csv'])
c1, c2, c3, c4 = st.columns(4)
name, dob, pan, custom = c1.text_input("Name"), c2.date_input("DOB", None), c3.text_input("PAN"), c4.text_input("Custom Pwd", type="password")

if st.button("🚀 Process"):
    if uploaded:
        df = process_file(uploaded, generate_passwords(name, dob, pan, custom))
        if df is not None:
            st.session_state['raw_data'] = df
            st.success("Data Ready!")

if st.session_state.get('raw_data') is not None:
    df = st.session_state['raw_data']
    start = st.date_input("Start Date", df['Date'].min())
    end = st.date_input("End Date", df['Date'].max())
    
    filt = df[(df['Date'].dt.date >= start) & (df['Date'].dt.date <= end)]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="metric-label">Debits ({len(filt[filt["Debit"]>0])})</div><div class="metric-value">₹{filt["Debit"].sum():,.2f}</div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-label">Credits ({len(filt[filt["Credit"]>0])})</div><div class="metric-value">₹{filt["Credit"].sum():,.2f}</div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-label">Opening Bal</div><div class="metric-value">₹{filt.iloc[0]["Balance"]-(filt.iloc[0]["Credit"]-filt.iloc[0]["Debit"]):,.2f}</div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-label">Closing Bal</div><div class="metric-value">₹{filt.iloc[-1]["Balance"]:,.2f}</div>', unsafe_allow_html=True)
    
    st.dataframe(filt, use_container_width=True)
