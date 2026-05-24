import streamlit as st
import pandas as pd
import time
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
    st.subheader("INITIATE DOCUMENT SCAN")
    uploaded_file = st.file_uploader("Upload Target Files (PDF/IMG)", type=["pdf", "png", "jpg"])
    
    if uploaded_file and st.button("RUN DEEP SCAN"):
        with st.spinner("Extracting Data Vectors..."):
            time.sleep(1) # Simulation delay
            # Dummy OCR Data
            raw_data = {
                "Date": ["2026-05-20", "2026-05-21"],
                "Party Name": ["Rahul Enterprises", "Alpha Tech Solutions"],
                "Supplier GSTIN": ["07RAHULXXX1Z5", host_gstin],
                "Billed To GSTIN": [host_gstin, "27CUSTOMERXX1Z"],
                "Item Details": ["Logitech Wireless Mouse", "Retainer Fee"],
                "HSN/SAC": ["84716060", "998213"],
                "Amount": [12000.00, 50000.00]
            }
            df = pd.DataFrame(raw_data)
            
            # Auto Detect Logic
            voucher_types = []
            for index, row in df.iterrows():
                if row["Supplier GSTIN"] == host_gstin:
                    voucher_types.append("🟢 SALES")
                elif row["Billed To GSTIN"] == host_gstin:
                    voucher_types.append("🔴 PURCHASE")
                else:
                    voucher_types.append("🟡 SUSPENSE")
                    
            df["Auto-Detected Voucher"] = voucher_types
            st.session_state.current_data = df
            st.success("SCAN COMPLETE. TARGETS IDENTIFIED.")
            
    if 'current_data' in st.session_state:
        st.dataframe(st.session_state.current_data, use_container_width=True)

with tab2:
    st.subheader("COGNITIVE AI MAPPER")
    if 'current_data' in st.session_state:
        df = st.session_state.current_data.copy()
        st.info("⚠️ MISSING MASTERS DETECTED. AUTO-CREATION PENDING.")
        
        action_df = pd.DataFrame({
            "Target Entity": ["Rahul Enterprises", "Logitech Wireless Mouse"],
            "Category": ["Ledger", "Stock Item"],
            "System Action": ["Create: Sundry Creditors", "Create: Primary (HSN 84716060)"]
        })
        st.dataframe(action_df, use_container_width=True)
        
        if st.button("AUTHORIZE CREATION"):
            st.success("AUTHORIZED. MASTERS READY FOR TALLY INJECTION.")
            st.session_state.final_push_data = df
    else:
        st.info("AWAITING TARGET DATA FROM SCANNER.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    st.markdown("<p class='terminal-font'>Deploying Headless Browser to GST Portal...</p>", unsafe_allow_html=True)
    
    if 'current_data' in st.session_state:
        if st.button("DEPLOY STEALTH BOT"):
            my_bar = st.progress(0, text="Establishing anonymous connection to portal...")
            time.sleep(1)
            my_bar.progress(30, text="Bypassing Captcha via OCR Engine...")
            time.sleep(1)
            my_bar.progress(60, text="Querying GSTIN: 07RAHULXXX1Z5...")
            time.sleep(1)
            my_bar.progress(100, text="Audit Complete.")
            
            audit_data = st.session_state.current_data.copy()
            status_list = ["🚩 GSTR-1 MISSING" if gstin == "07RAHULXXX1Z5" else "⚪ N/A (Self)" for gstin in audit_data["Supplier GSTIN"]]
            audit_data["Portal Status"] = status_list
            st.dataframe(audit_data[["Party Name", "Supplier GSTIN", "Portal Status"]], use_container_width=True)
            st.error("SYSTEM HALT: ITC BLOCKED FOR RAHUL ENTERPRISES.")
    else:
        st.info("AWAITING TARGET DATA FROM SCANNER.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    if 'final_push_data' in st.session_state:
        if st.button("EXECUTE XML PUSH"):
            st.success("⚡ DATA INJECTED SUCCESSFULLY ON PORT 9000. SESSION CLOSED.")
    else:
        st.warning("PLEASE AUTHORIZE LEDGER CREATION IN TAB 2 FIRST.")
