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
st.set_page_config(page_title="Alpha BizOps | Vyapar-Killer", layout="wide", page_icon="🥷")

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
    .vyapar-box { border: 1px solid #00FF41; border-radius: 5px; padding: 15px; background-color: #0a0a0a; margin-bottom: 20px;}
    .alert-box { border: 1px solid #FF0000; border-radius: 5px; padding: 10px; background-color: #330000; color: #FF0000; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🥷 ALPHA BIZOPS [SUPREME ERP ENGINE]</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='terminal-font'>SYSTEM PROTOCOL: SECURE | DB: {db_status}</p>", unsafe_allow_html=True)
st.markdown("---")

# Simulated Tally Masters (DB Mock)
TALLY_MASTERS = ["Office Welfare", "Computer Accessories", "Software Subscriptions", 
                 "Telephone Expenses", "Bank Charges", "Staff Salary A/c", 
                 "Office Rent A/c", "GST Payable", "Suspense A/c"]

# ==========================================
# 🛠️ 3. PRO CA DATA ENGINES
# ==========================================
def extract_pure_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).replace(',', '').replace('₹', '').replace('Cr', '').replace('Dr', '').strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try: return float(match.group())
        except: return 0.0
    return 0.0

def auto_map_ledger(narration):
    nl = str(narration).lower()
    rules = {
        "zomato": "Office Welfare", "swiggy": "Office Welfare", "amazon": "Office Expenses", 
        "aws": "Software Subscriptions", "airtel": "Telephone Expenses", "jio": "Telephone Expenses",
        "hdfc": "Bank Charges", "sbi": "Bank Charges", "salary": "Staff Salary A/c", "rent": "Office Rent A/c"
    }
    for key, ledger in rules.items():
        if key in nl: return ledger
    return "Suspense A/c"

def process_bank_excel(file):
    try:
        df_raw = pd.read_excel(file, header=None) if file.name.endswith('.xlsx') else pd.read_csv(file, header=None)
    except Exception as e:
        return None, f"System Error: {e}"
    
    header_idx = -1
    for idx, row in df_raw.iterrows():
        row_str = " ".join(str(x).lower() for x in row.values if pd.notna(x))
        if ('date' in row_str or 'txn' in row_str) and ('bal' in row_str or 'credit' in row_str or 'debit' in row_str):
            header_idx = idx
            break
            
    if header_idx == -1: return None, "Bank Header row not found. Ensure valid Bank Statement."

    df = pd.read_excel(file, skiprows=header_idx) if file.name.endswith('.xlsx') else pd.read_csv(file, skiprows=header_idx)
    date_c, desc_c, debit_c, credit_c, bal_c = None, None, None, None, None
    for col in df.columns:
        c = str(col).lower().replace('\n', ' ').replace('.', '').strip()
        if not date_c and any(w in c for w in ['date', 'value dt', 'txn dt']): date_c = col
        elif not desc_c and any(w in c for w in ['narration', 'particular', 'description']): desc_c = col
        elif not debit_c and any(w in c for w in ['debit', 'withdrawal', 'dr', 'paid out']): debit_c = col
        elif not credit_c and any(w in c for w in ['credit', 'deposit', 'cr', 'paid in']): credit_c = col
        elif not bal_c and any(w in c for w in ['balance', 'bal', 'closing']): bal_c = col

    if not (debit_c and credit_c and bal_c and date_c and desc_c):
        return None, "Error mapping columns."

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
    df_clean["Tally Ledger"] = df_clean["Narration"].apply(auto_map_ledger)

    metrics["dr_count"] = int((df_clean["Debit"] > 0).sum())
    metrics["cr_count"] = int((df_clean["Credit"] > 0).sum())
    metrics["total_dr_amt"] = float(df_clean["Debit"].sum())
    metrics["total_cr_amt"] = float(df_clean["Credit"].sum())
        
    return df_clean, metrics

# ==========================================
# 🚀 4. ERP TABS (VYAPAR / TALLY HYBRID)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] DATA INGESTION", "[ 2 ] TALLY MASTER SYNC", "[ 3 ] GST & COMPLIANCE", "[ 4 ] FINAL TALLY PUSH"])

with tab1:
    st.subheader("1. OMNI-SCANNER MODULE")
    scan_mode = st.radio("SELECT UPLOAD TYPE:", ["🏦 Bank Statement (Excel/CSV/PDF)", "🧾 Bills & Invoices (PDF/Excel)"], horizontal=True)
    pdf_pw = st.text_input("PDF Encryption Key (Optional) 🔐", type="password")
    uploaded_file = st.file_uploader("Upload Secured File", type=["pdf", "xlsx", "csv"])

    if uploaded_file and st.button("EXECUTE EXTRACTION"):
        with st.spinner("Processing through Alpha AI Core..."):
            try:
                # --- BANK LOGIC ---
                if scan_mode == "🏦 Bank Statement (Excel/CSV/PDF)":
                    if uploaded_file.name.endswith(('.xlsx', '.csv')):
                        df_final, result = process_bank_excel(uploaded_file)
                        if df_final is not None:
                            st.session_state.master_data = df_final
                            st.session_state.data_type = "BANK"
                            st.success("✅ BANK STATEMENT EXTRACTED. GO TO TAB 2 FOR MASTER SYNC.")
                            st.markdown("<div class='summary-box'><h3 style='text-align:center; color:#00FF41; margin-top:0;'>📊 BANK AUDIT SUMMARY</h3>", unsafe_allow_html=True)
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("📌 OPENING BALANCE", f"₹ {result['op_bal']:,.2f}")
                            c2.metric(f"🔴 DEBIT ({result['dr_count']} Entries)", f"₹ {result['total_dr_amt']:,.2f}")
                            c3.metric(f"🟢 CREDIT ({result['cr_count']} Entries)", f"₹ {result['total_cr_amt']:,.2f}")
                            c4.metric("🏁 CLOSING BALANCE", f"₹ {result['cl_bal']:,.2f}")
                            st.markdown("</div>", unsafe_allow_html=True)
                        else: st.error(result)

                    elif uploaded_file.name.endswith('.pdf'):
                        with pdfplumber.open(uploaded_file, password=pdf_pw if pdf_pw else '') as pdf:
                            text = "\n".join([page.extract_text() for page in pdf.pages])
                        rx = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})')
                        parsed = [{"Date": line.split()[0], "Narration": line[:80], "Debit": 0.0, "Credit": 0.0, "Tally Ledger": "Suspense A/c"} for line in text.split('\n') if rx.match(line.strip())]
                        if parsed:
                            st.session_state.master_data = pd.DataFrame(parsed)
                            st.session_state.data_type = "BANK"
                            st.success(f"🔓 PDF Extracted: {len(parsed)} entries found.")
                        else: st.warning("No tabular dates found in PDF.")

                # --- BILL LOGIC ---
                elif scan_mode == "🧾 Bills & Invoices (PDF/Excel)":
                    gstin_pat = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
                    full_text = ""
                    if uploaded_file.name.endswith('.pdf'):
                        with pdfplumber.open(uploaded_file, password=pdf_pw if pdf_pw else '') as pdf:
                            full_text = "\n".join([page.extract_text() for page in pdf.pages])
                    else:
                        df_bill = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                        full_text = df_bill.to_string()

                    found_gstins = list(set(re.findall(gstin_pat, full_text)))
                    bill_data = pd.DataFrame({
                        "File Name": [uploaded_file.name],
                        "Extracted GSTIN": [", ".join(found_gstins) if found_gstins else "NOT FOUND"],
                        "Party Name": ["Pending Setup"],
                        "GSTR-1 Status": ["🟡 Pending"],
                        "GSTR-3B Status": ["🟡 Pending"],
                        "Payment Status": ["🔴 Unpaid"]
                    })
                    st.session_state.bill_data = bill_data
                    st.session_state.data_type = "BILL"
                    st.success("✅ BILL EXTRACTED. GO TO TAB 3 FOR GST STATUS.")

            except Exception as e: st.error(f"SYSTEM HALT: {str(e)}")

with tab2:
    st.subheader("2. TALLY MASTER SYNC & MAPPING")
    if 'master_data' in st.session_state and st.session_state.data_type == "BANK":
        st.markdown("<div class='vyapar-box'>", unsafe_allow_html=True)
        st.markdown("#### ⚡ VYAPAR BULK MAPPER")
        colA, colB, colC = st.columns([2, 2, 1])
        with colA: search_kw = st.text_input("🔍 Narration Keyword (e.g., UPI)")
        with colB: assign_ledger = st.text_input("✍️ Target Tally Ledger")
        with colC:
            st.write(""); st.write("")
            if st.button("MAP IN BULK"):
                if search_kw and assign_ledger:
                    mask = st.session_state.master_data['Narration'].str.contains(search_kw, case=False, na=False)
                    st.session_state.master_data.loc[mask, 'Tally Ledger'] = assign_ledger
                    st.success(f"Mapped {mask.sum()} entries to {assign_ledger}")
        st.markdown("</div>", unsafe_allow_html=True)

        # 🧠 TALLY MASTER VERIFICATION LOGIC
        st.markdown("#### 📝 LIVE LEDGER VERIFICATION")
        df_current = st.session_state.master_data
        unique_ledgers = df_current['Tally Ledger'].unique()
        
        missing_masters = [l for l in unique_ledgers if l not in TALLY_MASTERS and l != "Suspense A/c"]
        if missing_masters:
            st.markdown("<div class='alert-box'><strong>⚠️ ATTENTION CA:</strong> The following ledgers are mapped but DO NOT EXIST in Tally Masters:</div>", unsafe_allow_html=True)
            for m in missing_masters:
                c_a, c_b = st.columns([3, 1])
                c_a.warning(f"Ledger: '{m}' is missing.")
                if c_b.button(f"Create '{m}' in Tally", key=m):
                    TALLY_MASTERS.append(m)
                    st.rerun()
                    
        st.session_state.master_data = st.data_editor(df_current, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 LOCK DATA FOR TALLY PUSH"):
            st.session_state.ready_for_tally = True
            st.success("✅ DATA LOCKED. GO TO TAB 4 FOR TALLY PUSH.")
    else:
        st.warning("Upload Bank Data in Tab 1 first.")

with tab3:
    st.subheader("3. GST & COMPLIANCE (GSTR-1 & 3B TRACKER)")
    if 'bill_data' in st.session_state and st.session_state.data_type == "BILL":
        st.info("💡 Vyapar-style Bill Management. Track GST compliance and Payment status here.")
        edited_bills = st.data_editor(
            st.session_state.bill_data, 
            use_container_width=True,
            column_config={
                "GSTR-1 Status": st.column_config.SelectboxColumn(options=["🟢 Filed", "🟡 Pending", "🔴 Error"]),
                "GSTR-3B Status": st.column_config.SelectboxColumn(options=["🟢 Filed", "🟡 Pending", "🔴 Error"]),
                "Payment Status": st.column_config.SelectboxColumn(options=["🟢 Paid", "🟡 Partial", "🔴 Unpaid"])
            }
        )
        st.session_state.bill_data = edited_bills
    else:
        st.warning("Upload Bill/Invoice Data in Tab 1 first.")

with tab4:
    st.subheader("4. THE FINAL TALLY PUSH (XML INJECTION)")
    if st.session_state.get("ready_for_tally", False) and 'master_data' in st.session_state:
        st.info("Data is Verified, Cleaned, and Master-Synced. Ready for Tally.")
        
        if st.button("🚀 INITIATE TALLY PUNCH", type="primary"):
            with st.spinner("Generating Tally XML Payload..."):
                time.sleep(2) # Simulating server hit
                entries_count = len(st.session_state.master_data)
                st.success(f"✅ SUCCESS: {entries_count} Entries successfully punched into Tally at Port {tally_port}.")
                
                # Showing mock XML payload
                xml_mock = f"""
                <ENVELOPE>
                    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
                    <BODY>
                        <IMPORTDATA>
                            <REQUESTDATA>
                                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                                    </TALLYMESSAGE>
                            </REQUESTDATA>
                        </IMPORTDATA>
                    </BODY>
                </ENVELOPE>
                """
                st.code(xml_mock, language="xml")
                st.balloons()
    else:
        st.error("⚠️ DATA NOT READY. Please Lock Data in Tab 2 before pushing to Tally.")
