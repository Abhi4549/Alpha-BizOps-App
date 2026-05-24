import streamlit as st
import pandas as pd
import time
import re
import pdfplumber
import numpy as np
from supabase import create_client, Client

# ==========================================
# ⚙️ 1. CLOUD DATABASE CONNECTION (SUPABASE)
# ==========================================
SUPABASE_URL = "https://vyuwysqkqdnkxoslozvy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dXd5c3FrcWRua3hvc2xvenZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MzExNDUsImV4cCI6MjA5NTIwNzE0NX0.MIUK8e-1dzAQCldTcPzxWp8q0v9iWu2WPwRqpdSfKtc"

try:
    supabase_db = create_client(SUPABASE_URL, SUPABASE_KEY)
    db_status = "ONLINE 🟢"
except:
    db_status = "OFFLINE 🔴 (Check Keys)"

# ==========================================
# 🥷 2. UI & BRANDING: ALPHA INVADER THEME
# ==========================================
st.set_page_config(page_title="Alpha BizOps | Tally Automator", layout="wide", page_icon="🥷")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; }
    .css-1d391kg { background-color: #111111; }
    h1, h2, h3, h4 { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; letter-spacing: 1.5px; }
    .stButton>button { background-color: #00FF41; color: #000000; border-radius: 2px; font-weight: bold; border: 1px solid #00FF41;}
    .stButton>button:hover { background-color: #000000; color: #00FF41; box-shadow: 0 0 10px #00FF41; }
    .terminal-font { font-family: 'Courier New', Courier, monospace; color: #00FF41; }
    div[data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; }
    div[data-testid="stMetricLabel"] { color: #AAAAAA !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>STATUS: SECURE | PROTOCOL: ACTIVE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# Helper Function: Clean Numbers
def clean_amount(val):
    if pd.isna(val) or val == "" or val == "-": return 0.0
    val_str = str(val).replace(',', '').replace('₹', '').replace(' ', '').strip()
    try: return float(val_str)
    except: return 0.0

# ==========================================
# 🚀 3. MAIN DASHBOARD & TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] OCR SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR STEALTH BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("INITIATE OMNI-SCANNER (PRO RECONCILIATION)")
    
    scan_mode = st.radio("SELECT SCAN TARGET PROTOCOL:", ["🧾 GST Bill / Invoice", "🏦 Bank Statement"], horizontal=True)
    pdf_password = st.text_input("Enter PDF Password (If Protected, else leave blank) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Target File (PDF, XLSX, CSV)", type=["pdf", "xlsx", "csv"])
    
    if uploaded_file and st.button("RUN PRO CA SCAN"):
        with st.spinner("Executing Extraction & Validation Protocol..."):
            try:
                extracted_df = pd.DataFrame()
                
                # ==========================================
                # 🛠️ EXCEL/CSV PROCESSOR
                # ==========================================
                if uploaded_file.name.endswith(('.xlsx', '.csv')) and scan_mode == "🏦 Bank Statement":
                    temp_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    
                    header_row_index = 0
                    for i, row in temp_df.iterrows():
                        row_str = ' '.join(str(x).lower() for x in row.values)
                        if 'date' in row_str and ('particular' in row_str or 'narration' in row_str or 'description' in row_str):
                            header_row_index = i + 1
                            break
                    
                    if uploaded_file.name.endswith('.xlsx'):
                        df_clean = pd.read_excel(uploaded_file, skiprows=header_row_index)
                    else:
                        df_clean = pd.read_csv(uploaded_file, skiprows=header_row_index)
                    
                    df_clean.dropna(how='all', inplace=True)
                    date_col = [col for col in df_clean.columns if 'date' in str(col).lower()]
                    if date_col:
                        df_clean.dropna(subset=[date_col[0]], inplace=True)

                    debit_c = next((c for c in df_clean.columns if any(w in str(c).lower() for w in ['debit', 'withdrawal', 'dr'])), None)
                    credit_c = next((c for c in df_clean.columns if any(w in str(c).lower() for w in ['credit', 'deposit', 'cr'])), None)
                    bal_c = next((c for c in df_clean.columns if 'balance' in str(c).lower()), None)
                    
                    if debit_c and credit_c and bal_c:
                        df_clean[debit_c] = df_clean[debit_c].apply(clean_amount)
                        df_clean[credit_c] = df_clean[credit_c].apply(clean_amount)
                        df_clean[bal_c] = df_clean[bal_c].apply(clean_amount)
                        
                        op_bal = df_clean[bal_c].iloc[0] if not df_clean.empty else 0.0
                        cl_bal = df_clean[bal_c].iloc[-1] if not df_clean.empty else 0.0
                        total_debits_amt = df_clean[debit_c].sum()
                        total_credits_amt = df
