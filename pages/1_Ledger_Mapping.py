import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import io

st.set_page_config(page_title="Alpha Ledger Mapper", page_icon="🔗", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 32px; font-weight: 800; color: #1E3A8A; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🔗 Alpha Ledger Mapping Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Map Cleaned Data to Tally Ledgers | Auto-Suspense Allocation</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300) 
def fetch_tally_ledgers():
    tally_url = "http://localhost:9000"
    xml_request = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
    try:
        response = requests.post(tally_url, data=xml_request, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            ledgers = [elem.attrib.get('NAME') for elem in root.findall('.//LEDGER') if elem.attrib.get('NAME')]
            if "Suspense A/c" not in ledgers: ledgers.append("Suspense A/c")
            return sorted(ledgers)
        else: return ["Suspense A/c", "Sales", "Purchase", "Bank A/c", "Cash"]
    except:
        return ["Suspense A/c", "Sales", "Purchase", "Bank A/c", "Cash", "Rahul Sharma", "Alpha Services"]

st.sidebar.title("⚙️ Tally Connection")
tally_status = st.sidebar.empty()
tally_ledgers = fetch_tally_ledgers()

if len(tally_ledgers) > 10: tally_status.success("🟢 Tally Connected (Live Ledgers)")
else: tally_status.warning("🟡 Using Offline Draft Ledgers")

df_map = None

# --- BRIDGE RECEIVER: Check if data came from the Main Page ---
if 'cleaned_data' in st.session_state and st.session_state['cleaned_data'] is not None:
    st.success("🔗 Live Data Synced from Bank Extraction Tool!")
    df_map = st.session_state['cleaned_data'].copy()
    
    if st.button("🗑️ Clear Synced Data & Upload Manually"):
        st.session_state['cleaned_data'] = None
        st.rerun()
else:
    st.info("Upload a file OR extract data from the main page to auto-sync here.")
    uploaded_file = st.file_uploader("Upload Cleaned Excel/CSV", type=['csv', 'xlsx'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'): df_map = pd.read_csv(uploaded_file)
        else: df_map = pd.read_excel(uploaded_file)

# --- PROCESS DATA ---
if df_map is not None:
    st.write("---")
    st.info("💡 Engine automatically assigned unknown entries to 'Suspense A/c'. You can change them in the table below.")
    
    if 'Narration' not in df_map.columns:
        st.error("❌ Uploaded file mein 'Narration' column nahi hai.")
    else:
        if 'Mapped_Ledger' not in df_map.columns:
            def auto_map(narration):
                narr_lower = str(narration).lower()
                if 'cash' in narr_lower: return 'Cash'
                if 'bank' in narr_lower or 'neft' in narr_lower or 'rtgs' in narr_lower or 'upi' in narr_lower:
                    return 'Suspense A/c' 
                return 'Suspense A/c'
                
            df_map['Mapped_Ledger'] = df_map['Narration'].apply(auto_map)
            df_map['Action_Required'] = df_map['Mapped_Ledger'].apply(lambda x: "⚠️ Review" if x == "Suspense A/c" else "✅ Ready")

        display_cols = ['Action_Required', 'Date', 'Narration', 'Debit', 'Credit', 'Mapped_Ledger']
        df_display = df_map[[c for c in display_cols if c in df_map.columns]]
        
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Mapped_Ledger": st.column_config.SelectboxColumn("Mapped Ledger (Tally)", width="large", options=tally_ledgers, required=True),
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
