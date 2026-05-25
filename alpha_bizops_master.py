import streamlit as st
import pandas as pd
from supabase import create_client
from modules.bank_processor import process_bank_statement
from modules.ocr_engine import process_invoice_pdf
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SECURE CLOUD DATABASE (SUPABASE)
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
# 🥷 UI & ALPHA INVADER THEME
# ==========================================
st.set_page_config(page_title="Alpha BizOps ERP", layout="wide", page_icon="🥷")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; }
    h1, h2, h3 { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; letter-spacing: 1px; }
    .stButton>button { background-color: #00FF41; color: #000000; font-weight: bold; border: 1px solid #00FF41;}
    .stButton>button:hover { background-color: #000000; color: #00FF41; box-shadow: 0 0 10px #00FF41; }
    .summary-box { border: 2px solid #00FF41; border-radius: 8px; padding: 15px; background-color: #111111;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS [ERP CORE]</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#00FF41; font-family:monospace;'>SYSTEM PROTOCOL: SECURE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "[ 1 ] BANK STATEMENT", 
    "[ 2 ] INVOICE OCR", 
    "[ 3 ] MASTER SYNC", 
    "[ 4 ] GSTR DASHBOARD", 
    "[ 5 ] TALLY PUSH"
])

# ==========================================
# MODULE 1: BANK STATEMENT
# ==========================================
with tab1:
    st.subheader("🏦 Bank Statement Cleaner")
    bank_file = st.file_uploader("Upload Excel/CSV Statement", type=["xlsx", "csv"])
    
    if bank_file and st.button("PROCESS BANK DATA"):
        with st.spinner("Executing CA Logic..."):
            df, result = process_bank_statement(bank_file)
            if df is not None:
                st.session_state.bank_data = df
                st.markdown("<div class='summary-box'>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 OPENING BAL", f"₹ {result['op_bal']:,.2f}")
                c2.metric("🔴 DEBIT ENTRIES", result['dr_count'])
                c3.metric("🟢 CREDIT ENTRIES", result['cr_count'])
                c4.metric("🏁 CLOSING BAL", f"₹ {result['cl_bal']:,.2f}")
                st.markdown("</div><br>", unsafe_allow_html=True)
                st.dataframe(df, use_container_width=True)
                st.success("✅ Tally-ready format generated.")
            else:
                st.error(result)

# ==========================================
# MODULE 2: INVOICE OCR
# ==========================================
with tab2:
    st.subheader("🧾 Invoice OCR & Classifier")
    invoice_file = st.file_uploader("Upload PDF Bill/Invoice", type=["pdf"])
    
    if invoice_file and st.button("SCAN INVOICE"):
        with st.spinner("Extracting parameters..."):
            df, status = process_invoice_pdf(invoice_file)
            if df is not None:
                st.session_state.invoice_data = df
                st.dataframe(df, use_container_width=True)
                st.success("✅ OCR Extraction Complete.")
            else:
                st.error(f"OCR Error: {status}")

with tab3: st.info("Module 3 (Auto-Master Creation) will be integrated here next once extraction is confirmed.")
with tab4: st.info("Module 5 (GSTR Fetcher) will be integrated here next.")
with tab5: st.info("Module 4 (Supabase/Tally Push) will be integrated here next.")
