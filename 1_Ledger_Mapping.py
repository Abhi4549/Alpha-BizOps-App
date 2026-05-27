import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import io

# ==========================================
# 1. UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="Alpha Ledger Mapper", page_icon="🔗", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 32px; font-weight: 800; color: #1E3A8A; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🔗 Alpha Ledger Mapping Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Map Bank Narrations to Tally Ledgers | Auto-Suspense Allocation</div>', unsafe_allow_html=True)

# ==========================================
# 2. TALLY LIVE FETCH LOGIC (PORT 9000)
# ==========================================
@st.cache_data(ttl=300) # 5 minute tak ledger list yaad rakhega
def fetch_tally_ledgers():
    tally_url = "http://localhost:9000"
    xml_request = """<ENVELOPE>
        <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
        <BODY>
            <EXPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>List of Accounts</REPORTNAME>
                    <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
                </REQUESTDESC>
            </EXPORTDATA>
        </BODY>
    </ENVELOPE>"""
    
    try:
        response = requests.post(tally_url, data=xml_request, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            ledgers = [elem.attrib.get('NAME') for elem in root.findall('.//LEDGER') if elem.attrib.get('NAME')]
            if "Suspense A/c" not in ledgers:
                ledgers.append("Suspense A/c")
            return sorted(ledgers)
        else:
            return ["Suspense A/c", "Sales", "Purchase", "Bank A/c", "Cash"]
    except:
        # Agar Tally band hai ya cloud par test kar rahe hain, toh default list
        return ["Suspense A/c", "Sales", "Purchase", "Bank A/c", "Cash", "Rahul Sharma", "Alpha Services"]

# ==========================================
# 3. MAPPING ENGINE
# ==========================================
st.sidebar.title("Configuration")
tally_status = st.sidebar.empty()

# Tally se ledgers fetch karna
tally_ledgers = fetch_tally_ledgers()
if len(tally_ledgers) > 10:
    tally_status.success("🟢 Tally Connected (Live Ledgers Fetched)")
else:
    tally_status.warning("🟡 Tally Not Found on Port 9000. Using Offline Draft Ledgers.")

# Upload Cleaned File
uploaded_file = st.file_uploader("Upload Cleaned Excel/CSV (From Bank Engine)", type=['csv', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    st.write("---")
    st.subheader("🛠️ Bulk Ledger Mapping")
    st.info("💡 Engine ne unknown parties ko automatically 'Suspense A/c' par set kar diya hai. Aap table mein hi unhe change ya naya naam type kar sakte hain.")
    
    # Check if necessary columns exist
    if 'Narration' not in df.columns:
        st.error("Uploaded file mein 'Narration' column nahi hai. Kripya Bank Engine se nikli hui file upload karein.")
    else:
        # Create a mapping column if not exists
        if 'Mapped_Ledger' not in df.columns:
            # Smart Auto-Allocation Logic
            def auto_map(narration):
                narr_lower = str(narration).lower()
                if 'cash' in narr_lower: return 'Cash'
                if 'bank' in narr_lower or 'neft' in narr_lower or 'rtgs' in narr_lower or 'upi' in narr_lower:
                    return 'Suspense A/c' # Inhe manually check karna best hai
                return 'Suspense A/c'
                
            df['Mapped_Ledger'] = df['Narration'].apply(auto_map)
            df['Action_Required'] = df['Mapped_Ledger'].apply(lambda x: "⚠️ Review" if x == "Suspense A/c" else "✅ Ready")

        # Reorder columns for better UI
        display_cols = ['Action_Required', 'Date', 'Narration', 'Debit', 'Credit', 'Mapped_Ledger']
        df_display = df[[c for c in display_cols if c in df.columns]]
        
        # Interactive Data Editor (Excel-like editing in browser)
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Mapped_Ledger": st.column_config.SelectboxColumn(
                    "Mapped Ledger (Tally)",
                    help="Select a ledger from Tally or type a new one.",
                    width="large",
                    options=tally_ledgers,
                    required=True,
                ),
                "Action_Required": st.column_config.TextColumn("Status", disabled=True)
            },
            use_container_width=True,
            num_rows="dynamic"
        )
        
        st.write("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("📊 Mapping Status")
            suspense_count = len(edited_df[edited_df['Mapped_Ledger'] == 'Suspense A/c'])
            ready_count = len(edited_df) - suspense_count
            st.write(f"✅ Ready for Tally: **{ready_count}** Entries")
            st.write(f"⚠️ In Suspense A/c: **{suspense_count}** Entries")
            
        with c2:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("📥 Download Final Tally-Ready File", use_container_width=True):
                # Finalizing Data
                final_df = edited_df.drop(columns=['Action_Required'])
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='TallyData')
                
                st.download_button(
                    label="Download Excel (.xlsx)",
                    data=output.getvalue(),
                    file_name="Alpha_Final_Mapped.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
