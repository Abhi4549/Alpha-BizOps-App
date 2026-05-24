import streamlit as st
import pandas as pd
import time
import re
import pdfplumber
from supabase import create_client
import warnings
warnings.filterwarnings('ignore')

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
st.set_page_config(page_title="Alpha BizOps | Vyapar Engine", layout="wide", page_icon="🥷")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; }
    h1, h2, h3, h4 { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; letter-spacing: 1px; }
    .stButton>button { background-color: #00FF41; color: #000000; border-radius: 2px; font-weight: bold; border: 1px solid #00FF41;}
    .stButton>button:hover { background-color: #000000; color: #00FF41; box-shadow: 0 0 10px #00FF41; }
    .terminal-font { font-family: 'Courier New', Courier, monospace; color: #00FF41; }
    div[data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; font-size: 24px; font-weight: bold;}
    div[data-testid="stMetricLabel"] { color: #AAAAAA !important; font-size: 14px; font-weight: bold;}
    .summary-box { border: 2px solid #00FF41; border-radius: 8px; padding: 15px; background-color: #111111; margin-top: 20px;}
    .bulk-box { border: 1px solid #00FF41; border-radius: 5px; padding: 15px; background-color: #0a0a0a; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS [VYAPAR-STYLE CA ENGINE]</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>SYSTEM PROTOCOL: SECURE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 🛠️ 3. STRICT PRO CA CLEANING ENGINE
# ==========================================
def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).replace(',', '').replace('₹', '').replace('Cr', '').replace('Dr', '').strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

def pre_map_ledger(narration):
    """Initial Auto-Mapping based on basic rules"""
    nl = str(narration).lower()
    auto_rules = {
        "zomato": "Office Welfare", "swiggy": "Office Welfare",
        "amazon": "Office Expenses", "aws": "Software Subscriptions",
        "hdfc": "Bank Charges", "sbi": "Bank Charges", "icici": "Bank Charges",
        "salary": "Staff Salary A/c", "gst": "GST Payable",
    }
    for key, ledger in auto_rules.items():
        if key in nl:
            return ledger
    return "🟡 Suspense A/c"

def process_bank_excel(file):
    try:
        df_raw = pd.read_excel(file, header=None) if file.name.endswith('.xlsx') else pd.read_csv(file, header=None)
    except Exception as e:
        return None, f"System Error: Could not read file. {e}"
    
    header_idx = -1
    for idx, row in df_raw.iterrows():
        row_str = " ".join(str(x).lower() for x in row.values if pd.notna(x))
        if ('date' in row_str or 'txn' in row_str) and ('bal' in row_str or 'credit' in row_str or 'debit' in row_str):
            header_idx = idx
            break
            
    if header_idx == -1:
        return None, "Error: Could not find Bank Header row. Ensure it's a valid Bank Statement."

    df = pd.read_excel(file, skiprows=header_idx) if file.name.endswith('.xlsx') else pd.read_csv(file, skiprows=header_idx)
    
    date_c, desc_c, debit_c, credit_c, bal_c = None, None, None, None, None
    for col in df.columns:
        c = str(col).lower().replace('\n', ' ').replace('.', '').strip()
        if not date_c and any(w in c for w in ['date', 'value dt', 'txn dt']): date_c = col
        elif not desc_c and any(w in c for w in ['narration', 'particular', 'description', 'remark']): desc_c = col
        elif not debit_c and any(w in c for w in ['debit', 'withdrawal', 'dr', 'paid out']): debit_c = col
        elif not credit_c and any(w in c for w in ['credit', 'deposit', 'cr', 'paid in']): credit_c = col
        elif not bal_c and any(w in c for w in ['balance', 'bal', 'closing']): bal_c = col

    if not (debit_c and credit_c and bal_c and date_c and desc_c):
        return None, f"Error: Failed to map exact columns. Found: {list(df.columns)}"

    df[bal_c] = df[bal_c].apply(extract_pure_number)
    valid_balances = df[df[bal_c] != 0.0][bal_c]
    
    metrics = {
        "op_bal": valid_balances.iloc[0] if not valid_balances.empty else 0.0,
        "cl_bal": valid_balances.iloc[-1] if not valid_balances.empty else 0.0,
    }

    df[debit_c] = df[debit_c].apply(extract_pure_number)
    df[credit_c] = df[credit_c].apply(extract_pure_number)

    df = df[(df[debit_c] > 0) | (df[credit_c] > 0)]
    df.dropna(subset=[date_c], inplace=True)

    df_clean = pd.DataFrame()
    df_clean["Date"] = df[date_c].astype(str).str.replace('00:00:00', '').str.strip()
    df_clean["Narration"] = df[desc_c].astype(str).str.replace('\n', ' ').str.replace('  ', ' ').str.strip()
    df_clean["Debit"] = df[debit_c]
    df_clean["Credit"] = df[credit_c]
    
    # Apply Initial Auto-Mapping
    df_clean["Tally Ledger"] = df_clean["Narration"].apply(pre_map_ledger)

    metrics["dr_count"] = int((df_clean["Debit"] > 0).sum())
    metrics["cr_count"] = int((df_clean["Credit"] > 0).sum())
    metrics["total_dr_amt"] = float(df_clean["Debit"].sum())
    metrics["total_cr_amt"] = float(df_clean["Credit"].sum())
        
    return df_clean, metrics

# ==========================================
# 🚀 4. DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] RAW SCAN", "[ 2 ] VYAPAR BULK MAPPER", "[ 3 ] GSTR BOT", "[ 4 ] TALLY PUSH"])

with tab1:
    st.subheader("1. UPLOAD & EXTRACT DATA")
    scan_mode = st.radio("TARGET PROTOCOL:", ["🏦 Bank Statement (Excel/CSV)"], horizontal=True)
    uploaded_file = st.file_uploader("Upload Bank Statement", type=["xlsx", "csv"])

    if uploaded_file and st.button("RUN EXTRACTION"):
        with st.spinner("Extracting standard columns..."):
            try:
                df_final, result = process_bank_excel(uploaded_file)
                if df_final is not None:
                    # Save to session state for Bulk Mapping
                    st.session_state.master_data = df_final
                    st.session_state.metrics = result
                    
                    st.success("✅ EXTRACTED SUCCESSFULLY. GO TO '[ 2 ] VYAPAR BULK MAPPER' TO MAP LEDGERS.")
                    
                    st.markdown("<div class='summary-box'><h3 style='text-align:center; color:#00FF41; margin-top:0;'>📊 DATA SUMMARY</h3>", unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("📌 OPENING BALANCE", f"₹ {result['op_bal']:,.2f}")
                    c2.metric(f"🔴 DEBIT ({result['dr_count']} Entries)", f"₹ {result['total_dr_amt']:,.2f}")
                    c3.metric(f"🟢 CREDIT ({result['cr_count']} Entries)", f"₹ {result['total_cr_amt']:,.2f}")
                    c4.metric("🏁 CLOSING BALANCE", f"₹ {result['cl_bal']:,.2f}")
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.error(result)
            except Exception as e:
                st.error(f"SYSTEM ERROR -> {str(e)}")

with tab2:
    st.subheader("2. AUTO & BULK LEDGER MAPPING")
    
    if 'master_data' in st.session_state:
        # 1. BULK MAPPER TOOL (Vyapar Style)
        st.markdown("<div class='bulk-box'>", unsafe_allow_html=True)
        st.markdown("#### ⚡ QUICK BULK MAPPER")
        colA, colB, colC = st.columns([2, 2, 1])
        with colA:
            search_kw = st.text_input("🔍 Search keyword in Narration (e.g., UPI, Rahul, Cash)")
        with colB:
            assign_ledger = st.text_input("✍️ Assign Tally Ledger (e.g., Traveling Exp)")
        with colC:
            st.write("")
            st.write("")
            if st.button("UPDATE ALL"):
                if search_kw and assign_ledger:
                    mask = st.session_state.master_data['Narration'].str.contains(search_kw, case=False, na=False)
                    updated_count = mask.sum()
                    st.session_state.master_data.loc[mask, 'Tally Ledger'] = assign_ledger
                    st.success(f"✅ {updated_count} Entries successfully mapped to '{assign_ledger}'")
                else:
                    st.warning("Please enter both Keyword and Ledger name.")
        st.markdown("</div>", unsafe_allow_html=True)

        # 2. EDITABLE GRID (Like Vyapar/Excel)
        st.markdown("#### 📝 LIVE DATA EDITOR (Click any cell to edit manually)")
        st.info("💡 You can manually fix any single Ledger directly in the table below.")
        
        # st.data_editor creates a real Excel-like editable grid in Streamlit!
        st.session_state.master_data = st.data_editor(
            st.session_state.master_data, 
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Tally Ledger": st.column_config.TextColumn(
                    "Tally Ledger",
                    help="Map this to a Tally ledger name",
                    required=True,
                )
            }
        )
        
        if st.button("💾 SAVE MASTER DATA TO MEMORY"):
            st.success("✅ Mapped data locked and ready for Tally XML Push!")
            
    else:
        st.warning("No data found. Please upload a Bank Statement in Tab 1 first.")

with tab3:
    st.subheader("GSTR INVISIBLE BOT")
    st.info("Stealth mode active. Awaiting targets.")

with tab4:
    st.subheader("TALLY INJECTION PROTOCOL")
    st.warning("XML Push paused. Waiting for data to be finalized in Tab 2.")
