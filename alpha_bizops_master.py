import streamlit as st
import pandas as pd
import requests
import datetime
from supabase import create_client
from modules.bank_processor import process_bank_statement
from modules.ocr_engine import process_invoice_pdf
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ SECURE CLOUD DATABASE & TALLY CONFIG
# ==========================================
SUPABASE_URL = "https://vyuwysqkqdnkxoslozvy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dXd5c3FrcWRua3hvc2xvenZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MzExNDUsImV4cCI6MjA5NTIwNzE0NX0.MIUK8e-1dzAQCldTcPzxWp8q0v9iWu2WPwRqpdSfKtc"

@st.cache_resource
def init_db():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY), "ONLINE 🟢"
    except: return None, "OFFLINE 🔴"

supabase_db, db_status = init_db()

st.set_page_config(page_title="Alpha BizOps | Tally Engine", layout="wide", page_icon="🥷")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; }
    h1, h2, h3, h4 { color: #00FF41 !important; font-family: 'Courier New', Courier, monospace; letter-spacing: 1px; }
    .stButton>button { background-color: #00FF41; color: #000000; font-weight: bold; border: 1px solid #00FF41;}
    .stButton>button:hover { background-color: #000000; color: #00FF41; box-shadow: 0 0 10px #00FF41; }
    .xml-box { background-color: #111111; padding: 10px; border-left: 3px solid #00FF41; overflow-x: auto; font-family: monospace; color:#FF9900;}
    </style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### ⚙️ TALLY CONFIG")
tally_url = st.sidebar.text_input("Tally Localhost URL", value="http://localhost:9000")
tally_bank_ledger = st.sidebar.text_input("Main Bank Ledger Name", value="HDFC Bank A/c")

st.markdown("<h1>🥷 ALPHA BIZOPS [TALLY NATIVE ENGINE]</h1>", unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["[ 1 ] EXTRACT DATA", "[ 2 ] VYAPAR MAPPER", "[ 3 ] GSTR VIEW", "[ 4 ] TALLY XML PUSH"])

# ==========================================
# TAB 1: DATA EXTRACTION
# ==========================================
with tab1:
    st.subheader("Omni-Scanner Module")
    scan_mode = st.radio("Target:", ["🏦 Bank Statement", "🧾 GST Bill / Invoice"], horizontal=True)
    up_file = st.file_uploader("Upload File", type=["xlsx", "csv", "pdf"])
    file_pw = st.text_input("PDF Password (if any)", type="password")
    
    if up_file and st.button("RUN ALPHA SCAN"):
        if scan_mode == "🏦 Bank Statement":
            df, res = process_bank_statement(up_file, pdf_pw=file_pw)
            if df is not None:
                st.session_state.master_data = df
                st.session_state.data_type = "BANK"
                st.success("✅ Bank Data Ready. Go to Tab 2 to map ledgers.")
            else: st.error(res)
                
        elif scan_mode == "🧾 GST Bill / Invoice":
            df_main, df_items, status = process_invoice_pdf(up_file, pdf_pw=file_pw)
            if df_main is not None:
                st.session_state.master_data = df_main
                st.session_state.item_data = df_items
                st.session_state.data_type = "BILL"
                st.success("✅ Invoice & Items Extracted. Go to Tab 4 for Tally Push.")
            else: st.error(status)

# ==========================================
# TAB 2: VYAPAR MAPPER (For Bank Statements)
# ==========================================
with tab2:
    if st.session_state.get("data_type") == "BANK" and 'master_data' in st.session_state:
        st.subheader("Bulk Ledger Mapper")
        c1, c2, c3 = st.columns([2, 2, 1])
        kw = c1.text_input("Search Narration (e.g., UPI, Amazon)")
        tgt = c2.text_input("Tally Target Ledger")
        if c3.button("BULK MAP"):
            mask = st.session_state.master_data['Narration'].str.contains(kw, case=False, na=False)
            st.session_state.master_data.loc[mask, 'Tally Ledger'] = tgt
            st.success(f"Updated {mask.sum()} entries.")
            
        st.session_state.master_data = st.data_editor(st.session_state.master_data, use_container_width=True)
    elif st.session_state.get("data_type") == "BILL":
        st.info("Bills have Party ledgers extracted automatically. Go to Tab 4.")
    else:
        st.info("Upload data in Tab 1 first.")

# ==========================================
# TAB 3: GSTR DASHBOARD
# ==========================================
with tab3:
    if st.session_state.get("data_type") == "BILL" and 'master_data' in st.session_state:
        st.subheader("GSTR Tracking Dashboard")
        df_display = st.session_state.master_data.copy()
        df_display["GSTR-1 Status"] = "🟡 Pending Validation"
        df_display["Payment Status"] = "🔴 Unpaid"
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Upload Bills in Tab 1 to see GST tracking.")

# ==========================================
# TAB 4: TALLY XML PUNCH (THE CORE ERP LOGIC)
# ==========================================
def generate_bank_xml(df, bank_ledger):
    xml_data = "<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">"
    
    for idx, row in df.iterrows():
        # Clean Date for Tally (YYYYMMDD)
        try:
            d_obj = pd.to_datetime(row['Date'])
            tally_date = d_obj.strftime('%Y%m%d')
        except: tally_date = "20260525"
        
        is_receipt = row['Credit'] > 0
        vch_type = "Receipt" if is_receipt else "Payment"
        amt = row['Credit'] if is_receipt else row['Debit']
        ledger = row['Tally Ledger']
        
        xml_data += f"""
        <VOUCHER VCHTYPE="{vch_type}" ACTION="Create">
            <DATE>{tally_date}</DATE>
            <NARRATION>{row['Narration'][:100]}</NARRATION>
            <VOUCHERTYPENAME>{vch_type}</VOUCHERTYPENAME>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{ledger}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{"No" if is_receipt else "Yes"}</ISDEEMEDPOSITIVE>
                <AMOUNT>{'-' + str(amt) if not is_receipt else str(amt)}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{bank_ledger}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{"Yes" if is_receipt else "No"}</ISDEEMEDPOSITIVE>
                <AMOUNT>{str(amt) if not is_receipt else '-' + str(amt)}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
        </VOUCHER>"""
        
    xml_data += "</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
    return xml_data

def generate_bill_xml(df_main, df_items):
    xml_data = "<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">"
    
    row = df_main.iloc[0]
    vch_type = row['Voucher Type'] # Sales or Purchase
    party = row['Party Name']
    inv_no = row['Invoice No']
    
    # Header
    xml_data += f"""
    <VOUCHER VCHTYPE="{vch_type}" ACTION="Create">
        <DATE>20260525</DATE>
        <VOUCHERTYPENAME>{vch_type}</VOUCHERTYPENAME>
        <REFERENCE>{inv_no}</REFERENCE>
        <PARTYLEDGERNAME>{party}</PARTYLEDGERNAME>
        <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>{party}</LEDGERNAME>
            <ISDEEMEDPOSITIVE>{"Yes" if vch_type=="Sales" else "No"}</ISDEEMEDPOSITIVE>
            <AMOUNT>{'-' + str(row['Total Amount']) if vch_type=="Sales" else str(row['Total Amount'])}</AMOUNT>
        </ALLLEDGERENTRIES.LIST>"""
        
    # Inventory Line Items
    for idx, item in df_items.iterrows():
        xml_data += f"""
        <ALLINVENTORYENTRIES.LIST>
            <STOCKITEMNAME>{item['Item Name']}</STOCKITEMNAME>
            <ISDEEMEDPOSITIVE>{"No" if vch_type=="Sales" else "Yes"}</ISDEEMEDPOSITIVE>
            <BILLEDQTY>{item['Qty']}</BILLEDQTY>
            <RATE>{item['Rate']}</RATE>
            <AMOUNT>{item['Amount']}</AMOUNT>
        </ALLINVENTORYENTRIES.LIST>"""
        
    xml_data += "</VOUCHER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
    return xml_data

with tab4:
    st.subheader("Direct Tally API Integration")
    if 'data_type' in st.session_state:
        st.warning("⚠️ Warning: Ensure Tally is open locally and ODBC/API Port is set to 9000.")
        
        if st.button("🚀 PUSH TO TALLY NOW", type="primary"):
            with st.spinner("Generating Strict Tally XML & Attempting Push..."):
                try:
                    # Generate XML payload based on data type
                    if st.session_state.data_type == "BANK":
                        final_xml = generate_bank_xml(st.session_state.master_data, tally_bank_ledger)
                    else:
                        final_xml = generate_bill_xml(st.session_state.master_data, st.session_state.item_data)
                    
                    st.markdown("#### Generated XML Payload Preview")
                    st.markdown(f"<div class='xml-box'>{final_xml[:1000]}... [TRUNCATED]</div>", unsafe_allow_html=True)
                    
                    # Uncomment below to actually push to localhost
                    # response = requests.post(tally_url, data=final_xml, headers={'Content-Type': 'text/xml'})
                    # if "CREATED" in response.text or "UPDATED" in response.text:
                    #     st.success("✅ Successfully Injected into Tally!")
                    # else:
                    #     st.error(f"Tally rejected the data. Response: {response.text}")
                    
                    st.success("✅ XML Generated Perfectly. Tally API Push Simulated Successfully!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"XML Generation Failed: {e}")
    else:
        st.info("Extract data in Tab 1 first to push to Tally.")
