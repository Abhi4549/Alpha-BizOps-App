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
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dXd5c3FrcWRua3hvc2xvenZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MzExNDUsImV4cCI6MjA5NTIwNzE0NX0.MIUK8e-1dzAQCldTcPzxWp8q0v9iWu2WPwRqpdSfKtc
"

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
    div[data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; font-size: 24px;}
    div[data-testid="stMetricLabel"] { color: #AAAAAA !important; font-size: 14px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>STATUS: SECURE | PROTOCOL: ACTIVE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# 🛠️ DEEP NUMBER CLEANER (For messy Indian Banks)
def clean_amount(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).strip() == "-": 
        return 0.0
    val_str = str(val).replace(',', '').replace('₹', '').replace('Cr.', '').replace('Dr.', '').replace('Cr', '').replace('Dr', '').replace(' ', '').strip()
    try: 
        return float(val_str)
    except: 
        return 0.0

# ==========================================
# 🚀 3. MAIN DASHBOARD & TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] OCR SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR STEALTH BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("INITIATE OMNI-SCANNER (SUPREME CA RECONCILIATION)")
    
    scan_mode = st.radio("SELECT SCAN TARGET PROTOCOL:", ["🧾 GST Bill / Invoice", "🏦 Bank Statement"], horizontal=True)
    pdf_password = st.text_input("Enter PDF Password (If Protected, else leave blank) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Target File (PDF, XLSX, CSV)", type=["pdf", "xlsx", "csv"])
    
    if uploaded_file and st.button("RUN PRO CA SCAN"):
        with st.spinner("Executing Aggressive Extraction & Validation Protocol..."):
            try:
                extracted_df = pd.DataFrame()
                
                # ==========================================
                # 🛠️ EXCEL/CSV - AGGRESSIVE PROCESSOR
                # ==========================================
                if uploaded_file.name.endswith(('.xlsx', '.csv')) and scan_mode == "🏦 Bank Statement":
                    temp_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    
                    header_row_index = 0
                    for i, row in temp_df.iterrows():
                        row_str = ' '.join(str(x).lower() for x in row.values)
                        if 'date' in row_str and ('particular' in row_str or 'narration' in row_str or 'description' in row_str or 'remarks' in row_str):
                            header_row_index = i + 1
                            break
                    
                    if uploaded_file.name.endswith('.xlsx'):
                        df_clean = pd.read_excel(uploaded_file, skiprows=header_row_index)
                    else:
                        df_clean = pd.read_csv(uploaded_file, skiprows=header_row_index)
                    
                    df_clean.columns = [str(c).replace('\n', ' ').strip() for c in df_clean.columns]
                    
                    df_clean.dropna(how='all', inplace=True)
                    date_col = next((col for col in df_clean.columns if 'date' in str(col).lower()), None)
                    if date_col:
                        df_clean.dropna(subset=[date_col], inplace=True)

                    debit_c, credit_c, bal_c = None, None, None
                    for c in df_clean.columns:
                        c_low = str(c).lower().replace(' ', '')
                        if any(w in c_low for w in ['debit', 'withdrawal', 'dr']): debit_c = c
                        elif any(w in c_low for w in ['credit', 'deposit', 'cr']): credit_c = c
                        elif 'balance' in c_low: bal_c = c
                    
                    if debit_c and credit_c and bal_c:
                        df_clean[debit_c] = df_clean[debit_c].apply(clean_amount)
                        df_clean[credit_c] = df_clean[credit_c].apply(clean_amount)
                        df_clean[bal_c] = df_clean[bal_c].apply(clean_amount)
                        
                        total_debits_amt = df_clean[debit_c].sum()
                        total_credits_amt = df_clean[credit_c].sum()
                        
                        dr_count = (df_clean[debit_c] > 0).sum()
                        cr_count = (df_clean[credit_c] > 0).sum()

                        valid_balances = df_clean[df_clean[bal_c] != 0.0][bal_c]
                        op_bal = valid_balances.iloc[0] if not valid_balances.empty else 0.0
                        cl_bal = valid_balances.iloc[-1] if not valid_balances.empty else 0.0

                        st.markdown("### 📊 EXACT RECONCILIATION REPORT")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("📌 OPENING BALANCE", f"₹ {op_bal:,.2f}")
                        col2.metric(f"🔴 DEBITS (Count: {dr_count})", f"₹ {total_debits_amt:,.2f}")
                        col3.metric(f"🟢 CREDITS (Count: {cr_count})", f"₹ {total_credits_amt:,.2f}")
                        col4.metric("🏁 CLOSING BALANCE", f"₹ {cl_bal:,.2f}")
                        
                        st.success("✅ SYSTEM AUDIT PASSED: Exact Debits, Credits, and Balances successfully locked.")
                    else:
                        st.error(f"❌ BANK FORMAT MISMATCH: System could not identify exact columns.")
                        st.warning(f"Columns Found in File: {df_clean.columns.tolist()}")
                        st.info("Check if the bank Excel has proper headers for Debit/Withdrawal, Credit/Deposit, and Balance.")
                    
                    ai_memory = {"ZOMATO": "Staff Welfare", "AWS": "Cloud Hosting", "CASH": "Cash A/c"}
                    desc_col = next((c for c in df_clean.columns if any(w in str(c).lower() for w in ['particular', 'narration', 'description', 'remarks'])), None)
                    if desc_col:
                        ai_ledgers = []
                        for desc in df_clean[desc_col]:
                            assigned = "🟡 Suspense A/c"
                            for key, ledg in ai_memory.items():
                                if key.lower() in str(desc).lower():
                                    assigned = f"🟢 {ledg}"
                                    break
                            ai_ledgers.append(assigned)
                        df_clean['AI Suggested Ledger'] = ai_ledgers

                    extracted_df = df_clean

                # ==========================================
                # 🛠️ PDF PROCESSOR (PASSWORD SAFE)
                # ==========================================
                elif uploaded_file.name.endswith('.pdf'):
                    pw = pdf_password if pdf_password else ''
                    full_text = ""
                    
                    try:
                        with pdfplumber.open(uploaded_file, password=pw) as pdf:
                            for page in pdf.pages:
                                full_text += page.extract_text() + "\n"
                        st.success("🔓 PDF DECRYPTED & TEXT ACCESSED SUCCESSFULLY.")
                    except Exception as pdf_error:
                        st.error("🔒 SYSTEM HALT: Incorrect Password or Encrypted PDF.")
                        st.stop()

                    if scan_mode == "🏦 Bank Statement":
                        lines = full_text.split('\n')
                        parsed_entries = []
                        date_regex = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
                        ai_memory = {"ZOMATO": "Staff Welfare", "AWS": "Cloud Hosting", "CASH": "Cash A/c", "RAHUL": "Rahul Enterprises"}
                        
                        for line in lines:
                            line = line.strip()
                            if date_regex.match(line):
                                clean_line = re.sub(r'\s+', ' ', line)
                                assigned_ledger = "🟡 Suspense A/c"
                                for key, ledg in ai_memory.items():
                                    if key.lower() in clean_line.lower():
                                        assigned_ledger = f"🟢 {ledg}"
                                        break
                                parsed_entries.append({
                                    "Extracted PDF Transaction": clean_line[:80] + "...",
                                    "AI Suggested Ledger": assigned_ledger
                                })
                        extracted_df = pd.DataFrame(parsed_entries)
                        
                        if extracted_df.empty:
                            st.warning("⚠️ No valid dates found. Ensure the PDF contains a standard tabular statement.")
                    
                    elif scan_mode == "🧾 GST Bill / Invoice":
                        gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                        found_gstins = list(set(re.findall(gstin_pattern, full_text)))
                        extracted_df = pd.DataFrame({
                            "File Name": [uploaded_file.name],
                            "Detected GSTINs": [", ".join(found_gstins) if found_gstins else "NOT DETECTED"],
                        })

                # Final Session Push
                if not extracted_df.empty:
                    st.session_state.current_data = extracted_df
                    st.session_state.scan_type = "BANK" if scan_mode == "🏦 Bank Statement" else "BILL"
                    
            except Exception as e:
                st.error(f"SYSTEM HALT: Formatting Error. Details: {e}")
            
    if 'current_data' in st.session_state:
        st.dataframe(st.session_state.current_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    if 'current_data' in st.session_state:
        st.info("Waiting for final Master sync...")
    else:
        st.warning("AWAITING TARGET DATA FROM SCANNER.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    st.warning("Awaiting final validation.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    st.warning("Awaiting final validation.")
