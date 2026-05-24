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
    st.subheader("INITIATE REAL DOCUMENT SCAN")
    uploaded_file = st.file_uploader("Upload Target Files (PDF Only)", type=["pdf"])
    
    if uploaded_file and st.button("RUN DEEP SCAN"):
        with st.spinner("Extracting Real Data Vectors from PDF..."):
            try:
                # 1. Asli PDF ko read karna
                with pdfplumber.open(uploaded_file) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                # 2. Asli GSTIN numbers nikalna regex (pattern) se
                gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                found_gstins = list(set(re.findall(gstin_pattern, full_text)))
                
                # 3. Agar GSTIN nahi mila toh default action
                if not found_gstins:
                    found_gstins = ["GSTIN NOT DETECTED"]

                # 4. Asli data ko table mein fit karna
                raw_data = {
                    "File Name": [uploaded_file.name],
                    "Detected GSTINs": [", ".join(found_gstins)],
                    "Host GSTIN": [host_gstin]
                }
                df = pd.DataFrame(raw_data)
                
                st.session_state.current_data = df
                st.success("REAL SCAN COMPLETE. TEXT EXTRACTED.")
                
                with st.expander("VIEW RAW EXTRACTED TEXT FROM PDF (Alpha View)"):
                    st.text(full_text)
                    
            except Exception as e:
                st.error(f"SCAN FAILED: File might be image-based (Scanned PDF) or corrupted. Error: {e}")
            
    if 'current_data' in st.session_state:
        st.dataframe(st.session_state.current_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    st.info("AI Matrix is analyzing the extracted text. Pending implementation of Ledger mapping.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    if 'current_data' in st.session_state:
        st.info("Targets acquired. GSTR Bot awaits final GSTIN validation.")
    else:
        st.warning("Upload and Scan a PDF first.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    st.warning("Awaiting final validation.")
