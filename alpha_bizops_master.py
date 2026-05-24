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
    div[data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; font-size: 24px; font-weight: bold;}
    div[data-testid="stMetricLabel"] { color: #AAAAAA !important; font-size: 14px; font-weight: bold;}
    .summary-box { border: 2px solid #00FF41; border-radius: 8px; padding: 15px; background-color: #111111; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS [SUPREME CA ENGINE]</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>SYSTEM PROTOCOL: SECURE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# ==========================================
# 🛠️ 3. SURGICAL DATA CLEANING & TALLY MAPPER
# ==========================================
def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).upper().replace(',', '')
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

def map_tally_ledger(narration):
    narration_lower = str(narration).lower()
    tally_masters = {
        "zomato": "Office Welfare", "swiggy": "Office Welfare",
        "amazon": "Computer Accessories", "aws": "Software Subscriptions",
        "airtel": "Telephone Expenses", "jio": "Telephone Expenses",
        "hdfc": "Bank Charges", "icici": "Bank Charges", "sbi": "Bank Charges",
        "salary": "Staff Salary A/c", "rent": "Office Rent A/c", "gst": "GST Payable"
    }
    for key, ledger in tally_masters.items():
        if key in narration_lower:
            return f"🟢 {ledger}"
    return "🟡 Suspense A/c"

def process_bank_excel(file):
    df_raw = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
    
    header_idx = -1
    for idx, row in df_raw.iterrows():
        row_str = " ".join(str(x).lower() for x in row.values)
        if ('date' in row_str or 'txn date' in row_str or 'value date' in row_str) and \
           ('narration' in row_str or 'particular' in row_str or 'description' in row_str or 'remarks' in row_str):
            header_idx = idx
            break
            
    if header_idx == -1:
        return None, "Error: Could not identify standard Bank headers (Date, Particulars/Narration). Ensure it's a valid statement."

    df = pd.read_excel(file, skiprows=header_idx + 1) if file.name.endswith('.xlsx') else pd.read_csv(file, skiprows=header_idx + 1)
    df.columns = [str(c).lower().replace('\n', ' ').strip() for c in df.columns]
    
    date_c, desc_c, debit_c, credit_c, bal_c = None, None, None, None, None
    for c in df.columns:
        if any(w in c for w in ['date', 'txn']) and not date_c: date_c = c
        elif any(w in c for w in ['narration', 'particular', 'description', 'remarks']) and not desc_c: desc_c = c
        elif any(w in c for w in ['debit', 'withdrawal', 'dr', 'payout']) and not debit_c: debit_c = c
        elif any(w in c for w in ['credit', 'deposit', 'cr', 'payin']) and not credit_c: credit_c = c
        elif any(w in c for w in ['balance', 'bal']) and not bal_c: bal_c = c

    if not (debit_c and credit_c and bal_c and date_c and desc_c):
        return None, f"Error: Could not cleanly separate Date, Narration, Debit, and Credit. Found columns: {list(df.columns)}"

    df.dropna(subset=[date_c], inplace=True)
    
    df[debit_c] = df[debit_c].apply(extract_pure_number)
    df[credit_c] = df[credit_c].apply(extract_pure_number)
    df[bal_c] = df[bal_c].apply(extract_pure_number)

    valid_bals = df[df[bal_c] != 0.0][bal_c]
    metrics = {
        "op_bal": valid_bals.iloc[0] if not valid_bals.empty else 0.0,
        "cl_bal": valid_bals.iloc[-1] if not valid_bals.empty else 0.0,
        "dr_count": int((df[debit_c] > 0).sum()),
        "cr_count": int((df[credit_c] > 0).sum())
    }

    df_clean = pd.DataFrame()
    df_clean["Date"] = df[date_c]
    df_clean["Narration"] = df[desc_c].astype(str).str.replace('\n', ' ').str.strip()
    df_clean["Debit"] = df[debit_c]
    df_clean["Credit"] = df[credit_c]
    df_clean["Tally Ledger"] = df_clean["Narration"].apply(map_tally_ledger)
        
    return df_clean, metrics

# ==========================================
# 🚀 4. DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] DEEP SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("OMNI-SCANNER: ENTERPRISE EDITION")
    scan_mode = st.radio("TARGET PROTOCOL:", ["🏦 Bank Statement (Excel/CSV/PDF)", "🧾 GST Invoice (PDF/Excel/CSV)"], horizontal=True)
    pdf_pw = st.text_input("PDF Encryption Key (Leave blank if none) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Secured File", type=["pdf", "xlsx", "csv"])

    if uploaded_file and st.button("EXECUTE PRO SCAN"):
        with st.spinner("Executing Cognitive Extraction & Tally Mapping..."):
            try:
                # ---------------- BANK STATEMENT LOGIC ----------------
                if scan_mode == "🏦 Bank Statement (Excel/CSV/PDF)":
                    if uploaded_file.name.endswith(('.xlsx', '.csv')):
                        df, result = process_bank_excel(uploaded_file)
                        
                        if df is not None:
                            st.session_state.master_data = df
                            
                            st.markdown("<div class='summary-box'><h3 style='text-align:center; color:#00FF41; margin-top:0;'>📊 SUPREME CA AUDIT SUMMARY</h3>", unsafe_allow_html=True)
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("📌 OPENING BALANCE", f"₹ {result['op_bal']:,.2f}")
                            c2.metric(f"🔴 NO. OF DEBITS", f"{result['dr_count']} Entries")
                            c3.metric(f"🟢 NO. OF CREDITS", f"{result['cr_count']} Entries")
                            c4.metric("🏁 CLOSING BALANCE", f"₹ {result['cl_bal']:,.2f}")
                            st.markdown("</div>", unsafe_allow_html=True)
                            
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
                                parsed.append({"Date & Narration": clean[:90] + "...", "Tally Ledger": map_tally_ledger(clean)})
                        
                        if parsed:
                            st.session_state.master_data = pd.DataFrame(parsed)
                            st.success(f"🔓 PDF Decrypted. Extracted {len(parsed)} valid financial entries.")
                        else:
                            st.warning("No tabular dates found in PDF. Ensure it's a standard bank format.")

                # ---------------- GST INVOICE LOGIC ----------------
                elif scan_mode == "🧾 GST Invoice (PDF/Excel/CSV)":
                    gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                    
                    if uploaded_file.name.endswith('.pdf'):
                        pw = pdf_pw if pdf_pw else ''
                        extracted_text = ""
                        with pdfplumber.open(uploaded_file, password=pw) as pdf:
                            for page in pdf.pages: extracted_text += page.extract_text() + "\n"
                        
                        found = list(set(re.findall(gstin_pattern, extracted_text)))
                        st.session_state.master_data = pd.DataFrame({
                            "Target File": [uploaded_file.name],
                            "GSTINs Decoded": [", ".join(found) if found else "NO GSTIN FOUND"]
                        })
                        st.success("PDF Invoice Deep Scan Complete.")
                        
                    elif uploaded_file.name.endswith(('.xlsx', '.csv')):
                        df_bill = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                        df_bill.dropna(how='all', inplace=True)
                        df_bill.dropna(axis=1, how='all', inplace=True)
                        
                        full_text = df_bill.to_string()
                        found = list(set(re.findall(gstin_pattern, full_text)))
                        
                        st.session_state.master_data = df_bill
                        st.success(f"✅ EXCEL INVOICE LOADED. GSTINs Detected: {', '.join(found) if found else 'NONE'}")

            except Exception as e:
                st.error(f"SYSTEM HALT: Critical Error Encountered -> {str(e)}")

    if 'master_data' in st.session_state:
        st.markdown("### 🗃️ SEPARATED TALLY DATA (DATE | NARRATION | DEBIT | CREDIT | LEDGER)")
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
