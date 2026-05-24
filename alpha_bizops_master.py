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

st.sidebar.markdown("### ⚙️ SYSTEM CONFIG")
tally_port = st.sidebar.text_input("Tally Port", value="9000")
host_gstin = st.sidebar.text_input("Host GSTIN", value="07ALPHAXX1Z")
stealth_mode = st.sidebar.toggle("🛡️ STEALTH PROTOCOL", value=True)

# ==========================================
# 🚀 3. MAIN DASHBOARD & TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] OCR SCAN", "[ 2 ] AI LEDGER", "[ 3 ] GSTR STEALTH BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("INITIATE OMNI-SCANNER (SUPREME CA PROTOCOL)")
    
    scan_mode = st.radio("SELECT SCAN TARGET PROTOCOL:", ["🧾 GST Bill / Invoice", "🏦 Bank Statement"], horizontal=True)
    pdf_password = st.text_input("Enter PDF Password (If Protected) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Target File (PDF, XLSX, CSV)", type=["pdf", "xlsx", "csv"])
    
    if uploaded_file and st.button("RUN SUPREME CA SCAN"):
        with st.spinner("Initiating 40-Year CA Cleaning Protocol..."):
            try:
                extracted_df = pd.DataFrame()
                full_text = ""

                # ==========================================
                # 🛠️ 1. EXCEL/CSV - ADVANCED CA CLEANING
                # ==========================================
                if uploaded_file.name.endswith(('.xlsx', '.csv')):
                    # Pehle raw read karke kachra find karenge
                    temp_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    
                    # CA Logic: Find actual header row (containing 'Date' or 'Particulars')
                    header_row_index = 0
                    for i, row in temp_df.iterrows():
                        row_str = ' '.join(str(x).lower() for x in row.values)
                        if 'date' in row_str and ('particular' in row_str or 'description' in row_str or 'narration' in row_str):
                            header_row_index = i + 1
                            break
                    
                    # Ab asli data read karenge kachra hatakar
                    if uploaded_file.name.endswith('.xlsx'):
                        extracted_df = pd.read_excel(uploaded_file, skiprows=header_row_index)
                    else:
                        extracted_df = pd.read_csv(uploaded_file, skiprows=header_row_index)
                        
                    extracted_df.dropna(how='all', inplace=True)
                    
                    # CA Logic: Drop rows where Date column is empty (Removes footer junk)
                    date_col = [col for col in extracted_df.columns if 'date' in col.lower()]
                    if date_col:
                        extracted_df.dropna(subset=[date_col[0]], inplace=True)

                    extracted_df.fillna("-", inplace=True)
                    st.success("EXCEL/CSV: Header Detected. Bank Junk Removed. Data Sanitized.")

                # ==========================================
                # 🛠️ 2. PDF - ADVANCED CA CLEANING
                # ==========================================
                elif uploaded_file.name.endswith('.pdf'):
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
                # 🏦 LOGIC: BANK STATEMENT PDF (DATE-DRIVEN)
                # ==========================================
                elif scan_mode == "🏦 Bank Statement" and full_text:
                    ai_memory = {"ZOMATO": "Staff Welfare", "AWS": "Cloud Hosting", "CASH": "Cash A/c", "RAHUL": "Rahul Enterprises"}
                    lines = full_text.split('\n')
                    parsed_entries = []
                    
                    # CA Logic: Match lines starting with standard Date formats
                    # Like DD-MM-YYYY, DD/MM/YY, DD-Mon-YY
                    date_regex = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
                    
                    for line in lines:
                        line = line.strip()
                        # Agar line Date se shuru hoti hai, tabhi uthao (Ignore address/headers)
                        if date_regex.match(line):
                            clean_line = re.sub(r'\s+', ' ', line) # Remove extra spaces
                            
                            # Clean Narration: Remove bank codes
                            narration_clean = clean_line.replace("NEFT/", "").replace("IMPS/", "").replace("UPI/", "")
                            
                            assigned_ledger = "🟡 Suspense A/c"
                            for keyword, ledger in ai_memory.items():
                                if keyword.lower() in narration_clean.lower():
                                    assigned_ledger = f"🟢 {ledger}"
                                    break
                                    
                            parsed_entries.append({
                                "Sanitized Transaction": narration_clean[:70] + "...", 
                                "AI Ledger Map": assigned_ledger
                            })
                            
                    extracted_df = pd.DataFrame(parsed_entries)
                    
                    if extracted_df.empty:
                        st.warning("⚠️ No valid transactions found. Make sure it's a standard Bank Statement PDF.")

                # Final Display
                if not extracted_df.empty:
                    st.session_state.current_data = extracted_df
                    st.session_state.scan_type = "BANK" if scan_mode == "🏦 Bank Statement" else "BILL"
                    
                with st.expander("VIEW RAW DATA vs CA CLEANED DATA (Alpha View)"):
                    if full_text:
                        st.text("RAW PDF EXTRACT (Full of Junk):")
                        st.text(full_text[:1000] + "\n...[TRUNCATED]...")
                        
            except Exception as e:
                st.error(f"SYSTEM HALT: File format error. Error Details: {e}")
            
    if 'current_data' in st.session_state:
        st.dataframe(st.session_state.current_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    if 'current_data' in st.session_state:
        if st.session_state.scan_type == "BANK":
            st.info("🏦 BANK MODE: Suspense A/c entries routed for review. 'Green' entries ready for Tally.")
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
