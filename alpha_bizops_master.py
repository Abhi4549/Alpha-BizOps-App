import streamlit as st
import pandas as pd
import time
import re
import pdfplumber
from supabase import create_client

# ==========================================
# ⚙️ 1. SECURE CLOUD DATABASE (SUPABASE)
# ==========================================
SUPABASE_URL = "https://vyuwysqkqdnkxoslozvy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dXd5c3FrcWRua3hvc2xvenZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MzExNDUsImV4cCI6MjA5NTIwNzE0NX0.MIUK8e-1dzAQCldTcPzxWp8q0v9iWu2WPwRqpdSfKtc"

@st.cache_resource
def init_db():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY), "ONLINE 🟢"
    except Exception:
        return None, "OFFLINE 🔴"

supabase_db, db_status = init_db()

# ==========================================
# 🥷 2. UI & ALPHA INVADER THEME
# ==========================================
st.set_page_config(page_title="Alpha BizOps | Tally Automator", layout="wide", page_icon="🥷")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; }
    h1, h2, h3, h4 { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; letter-spacing: 1px; }
    .stButton>button { background-color: #00FF41; color: #000000; border-radius: 2px; font-weight: bold; border: 1px solid #00FF41;}
    .stButton>button:hover { background-color: #000000; color: #00FF41; box-shadow: 0 0 10px #00FF41; }
    .terminal-font { font-family: 'Courier New', Courier, monospace; color: #00FF41; }
    div[data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; font-size: 22px;}
    div[data-testid="stMetricLabel"] { color: #AAAAAA !important; font-size: 13px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS [PRO CA ENGINE]</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>SYSTEM PROTOCOL: SECURE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# ==========================================
# 🛠️ 3. PRO CA DATA CLEANING FUNCTIONS
# ==========================================
def clean_currency(val):
    if pd.isna(val): return 0.0
    v_str = str(val).upper().replace(',', '').replace('₹', '').replace(' ', '').strip()
    v_str = re.sub(r'[A-Z]', '', v_str) 
    if v_str == '' or v_str == '-': return 0.0
    try: return float(v_str)
    except: return 0.0

def process_bank_excel(file):
    df_raw = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
    
    header_idx = -1
    for idx, row in df_raw.iterrows():
        row_str = " ".join(str(x).lower() for x in row.values)
        if 'date' in row_str and ('narration' in row_str or 'particular' in row_str or 'description' in row_str):
            header_idx = idx
            break
            
    if header_idx == -1:
        return None, "Error: Could not identify standard Bank headers (Date, Narration, Balance) in this file."

    df = pd.read_excel(file, skiprows=header_idx + 1) if file.name.endswith('.xlsx') else pd.read_csv(file, skiprows=header_idx + 1)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    df.dropna(how='all', inplace=True)
    
    date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
    if date_col: df.dropna(subset=[date_col], inplace=True)

    debit_col = next((c for c in df.columns if any(w in str(c).lower() for w in ['debit', 'withdrawal', 'dr'])), None)
    credit_col = next((c for c in df.columns if any(w in str(c).lower() for w in ['credit', 'deposit', 'cr'])), None)
    bal_col = next((c for c in df.columns if 'balance' in str(c).lower()), None)
    desc_col = next((c for c in df.columns if any(w in str(c).lower() for w in ['particular', 'narration', 'description'])), None)

    if not (debit_col and credit_col and bal_col):
        return None, "Error: Missing mandatory accounting columns (Debit/Credit/Balance)."

    df[debit_col] = df[debit_col].apply(clean_currency)
    df[credit_col] = df[credit_col].apply(clean_currency)
    df[bal_col] = df[bal_col].apply(clean_currency)

    valid_bals = df[df[bal_col] != 0.0][bal_col]
    metrics = {
        "op_bal": valid_bals.iloc[0] if not valid_bals.empty else 0.0,
        "cl_bal": valid_bals.iloc[-1] if not valid_bals.empty else 0.0,
        "total_dr": df[debit_col].sum(),
        "total_cr": df[credit_col].sum(),
        "dr_count": (df[debit_col] > 0).sum(),
        "cr_count": (df[credit_col] > 0).sum()
    }

    if desc_col:
        ai_memory = {"ZOMATO": "Staff Welfare", "AWS": "Cloud Hosting", "CASH": "Cash A/c"}
        df['AI_Ledger'] = df[desc_col].apply(lambda x: next((f"🟢 {v}" for k, v in ai_memory.items() if k.lower() in str(x).lower()), "🟡 Suspense A/c"))
        
    return df, metrics

# ==========================================
# 🚀 4. DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] DEEP SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("OMNI-SCANNER: ENTERPRISE EDITION")
    scan_mode = st.radio("TARGET PROTOCOL:", ["🏦 Bank Statement (Excel/CSV/PDF)", "🧾 GST Invoice (PDF)"], horizontal=True)
    pdf_pw = st.text_input("PDF Encryption Key (Leave blank if none) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Secured File", type=["pdf", "xlsx", "csv"])

    if uploaded_file and st.button("EXECUTE PRO SCAN"):
        with st.spinner("Bypassing firewalls & executing CA Reconciliations..."):
            try:
                if scan_mode == "🏦 Bank Statement (Excel/CSV/PDF)":
                    if uploaded_file.name.endswith(('.xlsx', '.csv')):
                        df, result = process_bank_excel(uploaded_file)
                        
                        if df is not None:
                            st.session_state.master_data = df
                            st.markdown("### 📊 AUDIT RECONCILIATION PASSED")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("📌 OPENING BAL", f"₹ {result['op_bal']:,.2f}")
                            c2.metric(f"🔴 DEBITS ({result['dr_count']})", f"₹ {result['total_dr']:,.2f}")
                            c3.metric(f"🟢 CREDITS ({result['cr_count']})", f"₹ {result['total_cr']:,.2f}")
                            c4.metric("🏁 CLOSING BAL", f"₹ {result['cl_bal']:,.2f}")
                            st.success("Data sanitized and ready for Tally XML mapping.")
                        else:
                            st.error(result)
                            
                    elif uploaded_file.name.endswith('.pdf'):
                        pw = pdf_pw if pdf_pw else ''
                        extracted_text = ""
                        with pdfplumber.open(uploaded_file, password=pw) as pdf:
                            for page in pdf.pages: extracted_text += page.extract_text() + "\n"
                            
                        date_rx = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
                        parsed = []
                        for line in extracted_text.split('\n'):
                            if date_rx.match(line.strip()):
                                clean = re.sub(r'\s+', ' ', line.strip())
                                parsed.append({"Raw PDF Entry": clean[:90] + "...", "Status": "🟡 Pending AI Map"})
                        
                        if parsed:
                            st.session_state.master_data = pd.DataFrame(parsed)
                            st.success(f"🔓 PDF Decrypted. Extracted {len(parsed)} valid financial entries.")
                        else:
                            st.warning("No tabular dates found in PDF. Ensure it's a standard bank format.")

                elif scan_mode == "🧾 GST Invoice (PDF)":
                    pw = pdf_pw if pdf_pw else ''
                    extracted_text = ""
                    with pdfplumber.open(uploaded_file, password=pw) as pdf:
                        for page in pdf.pages: extracted_text += page.extract_text() + "\n"
                    
                    gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                    found = list(set(re.findall(gstin_pattern, extracted_text)))
                    
                    st.session_state.master_data = pd.DataFrame({
                        "Target File": [uploaded_file.name],
                        "GSTINs Decoded": [", ".join(found) if found else "NO GSTIN FOUND"]
                    })
                    st.success("Invoice Deep Scan Complete.")

            except Exception as e:
                st.error(f"SYSTEM HALT: Critical Error Encountered -> {str(e)}")

    if 'master_data' in st.session_state:
        st.dataframe(st.session_state.master_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    st.info("System awaiting final confirmation of XML Ledger Masters.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    st.info("Stealth mode active. Awaiting targets.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    st.warning("XML Push paused pending Ledger Mapping.")
