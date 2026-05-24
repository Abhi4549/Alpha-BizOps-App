import streamlit as st
import pandas as pd
import time
import re
import pdfplumber
from supabase import create_client, Client

# ==========================================
# ⚙️ 1. CLOUD DATABASE CONNECTION (SUPABASE)
# ==========================================
SUPABASE_URL = "https://vyuwysqkqdnkxoslozvy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dXd5c3FrcWRua3hvc2xvenZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MzExNDUsImV4cCI6MjA5NTIwNzE0NX0.MIUK8e-1dzAQCldTcPzxWp8q0v9iWu2WPwRqpdSfKtc"

# Connection Initialize (Try block to avoid crashes if keys are empty)
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
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>STATUS: SECURE | PROTOCOL: ACTIVE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# ⚙️ 3. SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
st.sidebar.markdown("---")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# ==========================================
# 🚀 4. MAIN DASHBOARD & TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] OCR SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR STEALTH BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("INITIATE OMNI-SCANNER (PDF/EXCEL/CSV)")
    
    # 🎯 MODE SWITCH
    scan_mode = st.radio("SELECT SCAN TARGET PROTOCOL:", ["🧾 GST Bill / Invoice", "🏦 Bank Statement"], horizontal=True)
    
    # Password Box & File Uploader
    pdf_password = st.text_input("Enter PDF Password (If Protected) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Target File (PDF, XLSX, CSV)", type=["pdf", "xlsx", "csv"])
    
    if uploaded_file and st.button("RUN SUPREME CA SCAN"):
        with st.spinner("Initiating 40-Year CA Cleaning Protocol..."):
            try:
                extracted_df = pd.DataFrame()
                full_text = ""

                # ==========================================
                # 🛠️ 1. EXTRACTION ENGINE (EXCEL / PDF)
                # ==========================================
                if uploaded_file.name.endswith(('.xlsx', '.csv')):
                    if uploaded_file.name.endswith('.xlsx'):
                        extracted_df = pd.read_excel(uploaded_file)
                    else:
                        extracted_df = pd.read_csv(uploaded_file)
                    
                    # SUPREME CA CLEANING: Remove empty rows, fill blanks
                    extracted_df.dropna(how='all', inplace=True)
                    extracted_df.fillna("N/A", inplace=True)
                    st.success("EXCEL/CSV DECODED & SANITIZED.")

                elif uploaded_file.name.endswith('.pdf'):
                    # Password Protected PDF Logic
                    with pdfplumber.open(uploaded_file, password=pdf_password if pdf_password else None) as pdf:
                        for page in pdf.pages:
                            full_text += page.extract_text() + "\n"
                    st.success("PDF DECRYPTED & TEXT EXTRACTED.")
                
                # ==========================================
                # 🧾 LOGIC: GST BILL / INVOICE
                # ==========================================
                if scan_mode == "🧾 GST Bill / Invoice" and full_text:
                    gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                    found_gstins = list(set(re.findall(gstin_pattern, full_text)))
                    
                    raw_data = {
                        "File Name": [uploaded_file.name],
                        "Detected GSTINs": [", ".join(found_gstins) if found_gstins else "GSTIN NOT DETECTED"],
                        "Status": ["Cleaned & Ready"]
                    }
                    extracted_df = pd.DataFrame(raw_data)
                
                # ==========================================
                # 🏦 LOGIC: BANK STATEMENT (TEXT FALLBACK)
                # ==========================================
                elif scan_mode == "🏦 Bank Statement" and full_text:
                    # AI Memory Dictionary (Simulating Database Rules)
                    ai_memory = {"ZOMATO": "Staff Welfare", "AWS": "Cloud Hosting", "UPI": "Suspense A/c"}
                    lines = full_text.split('\n')
                    parsed_entries = []
                    
                    # SUPREME CA CLEANING: Ignore junk lines, format narration
                    for line in lines:
                        if len(line) > 10 and any(char.isdigit() for char in line):
                            clean_line = line.strip().replace("  ", " ") # Removing extra spaces
                            assigned_ledger = "🟡 Suspense A/c"
                            
                            for keyword, ledger in ai_memory.items():
                                if keyword.lower() in clean_line.lower():
                                    assigned_ledger = f"🟢 {ledger}"
                                    break
                                    
                            parsed_entries.append({
                                "Cleaned Narration": clean_line[:60] + "...", 
                                "AI Ledger": assigned_ledger
                            })
                    extracted_df = pd.DataFrame(parsed_entries)

                # Final Display
                if not extracted_df.empty:
                    st.session_state.current_data = extracted_df
                    st.session_state.scan_type = "BANK" if scan_mode == "🏦 Bank Statement" else "BILL"
                    
                with st.expander("VIEW RAW EXTRACTED DATA (Alpha View)"):
                    if full_text:
                        st.text(full_text)
                    else:
                        st.dataframe(extracted_df)

            except Exception as e:
                st.error(f"SYSTEM HALT: Authentication Failed or Corrupted File. Error Details: {e}")
            
    if 'current_data' in st.session_state:
        st.dataframe(st.session_state.current_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    if 'current_data' in st.session_state:
        if st.session_state.scan_type == "BANK":
            st.info("🏦 BANK MODE: Routing 'Suspense A/c' entries for manual mapping. 'Ready' entries queued for Bulk Push.")
        else:
            st.info("🧾 BILL MODE: Checking Masters for Auto-Creation...")
    else:
        st.warning("AWAITING TARGET DATA FROM SCANNER.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    if 'current_data' in st.session_state:
        st.info("Targets acquired. GSTR Bot awaits final GSTIN validation.")
    else:
        st.warning("Upload and Scan a document first.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    st.warning("Awaiting final validation.")
