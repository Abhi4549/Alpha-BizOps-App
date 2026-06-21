import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# --- ENTERPRISE SaaS UI CONFIG ---
st.set_page_config(page_title="Alpha BizOps SaaS", layout="wide", initial_sidebar_state="expanded")

# CUSTOM CSS FOR REPOTIC-LOOK
st.markdown("""
    <style>
    .card { background: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .metric-val { font-size: 24px; font-weight: 700; color: #1a1a1a; }
    .metric-lbl { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
    .stDataFrame { border: 1px solid #e0e0e0; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- CORE PARSING MODULE ---
def compute_ledger_logic(df):
    """ Tally-Ready Ledger Calculation """
    df = df.sort_values(by='Date')
    df['Debit'] = df['Amount'].apply(lambda x: abs(x) if x < 0 else 0.0)
    df['Credit'] = df['Amount'].apply(lambda x: x if x > 0 else 0.0)
    # Cumulative balance logic
    df['Running_Balance'] = df['Amount'].cumsum()
    return df

def extract_engine(file, pwd):
    data = []
    with pdfplumber.open(io.BytesIO(file.read()), password=pwd) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # Regex for standard bank statement rows
                match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})', line)
                if match:
                    data.append({
                        "Date": match.group(1),
                        "Narration": match.group(2),
                        "Amount": float(match.group(3).replace(',', ''))
                    })
    return pd.DataFrame(data)

# --- SIDEBAR: PRODUCT CONTROL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3062/3062634.png", width=50)
    st.title("Alpha BizOps v1.0")
    uploaded = st.file_uploader("Upload Statement", type=['pdf'])
    pwd = st.text_input("Security Key", type="password")
    if st.button("Initialize Engine"):
        if uploaded:
            df = extract_pdf_data(uploaded, pwd) # Implement extraction
            st.session_state['data'] = compute_ledger_logic(df)
            st.success("Ledger Sync Complete!")

# --- MAIN DASHBOARD: REPORTING ---
if 'data' in st.session_state:
    df = st.session_state['data']
    
    # Header
    st.header("Executive Financial Report")
    
    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="card"><div class="metric-lbl">Opening</div><div class="metric-val">₹{df.iloc[0]["Running_Balance"]:,.2f}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="card"><div class="metric-lbl">Debits</div><div class="metric-val">₹{df["Debit"].sum():,.2f}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="card"><div class="metric-lbl">Credits</div><div class="metric-val">₹{df["Credit"].sum():,.2f}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="card"><div class="metric-lbl">Closing</div><div class="metric-val">₹{df.iloc[-1]["Running_Balance"]:,.2f}</div></div>', unsafe_allow_html=True)
    
    # Detailed Table
    st.write("### Transaction Ledger")
    st.dataframe(df, use_container_width=True)
    
    # Export
    st.download_button("Export to Tally XML/CSV", df.to_csv(index=False), "Ledger_Export.csv")
