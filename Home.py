import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

st.set_page_config(page_title="Alpha BizOps Hub", layout="wide")

# --- UI STYLING ---
st.markdown("""
    <style>
    .metric-card { background: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: center; }
    .val { font-size: 22px; font-weight: 800; color: #1E3A8A; }
    .lbl { font-size: 14px; color: #6B7280; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

def parse_pdf(file, pwd):
    pdf_bytes = file.read()
    data = []
    with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
        for page in pdf.pages:
            table = page.extract_table() # Table format mein extract karne ki koshish
            if table:
                for row in table:
                    if len(row) >= 3 and any(re.search(r'\d{2}/\d{2}', str(x)) for x in row):
                        data.append(row)
            else:
                # Agar table nahi hai, toh line parser
                for line in page.extract_text().split('\n'):
                    if re.search(r'\d{2}/\d{2}', line):
                        data.append(line.split())
    return pd.DataFrame(data)

# --- UI LOGIC ---
st.title("🏦 Alpha BizOps - Statement Processor")
file = st.file_uploader("Upload Statement", type=['pdf'])
c1, c2 = st.columns([3, 1])
pwd = c2.text_input("Password", type="password")

if st.button("🚀 Process"):
    if file:
        df = parse_pdf(file, pwd)
        # Data cleaning: NaNs hatao aur sahi columns set karo
        df = df.dropna(how='all')
        st.session_state['data'] = df
        st.success("Extracted!")

if 'data' in st.session_state:
    df = st.session_state['data']
    
    # METRICS UI
    c1, c2, c3, c4 = st.columns(4)
    cols = [c1, c2, c3, c4]
    labels = ["Debits", "Credits", "Opening", "Closing"]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><div class="lbl">{labels[i]}</div><div class="val">₹ 0.00</div></div>', unsafe_allow_html=True)
        
    st.dataframe(df, use_container_width=True)
