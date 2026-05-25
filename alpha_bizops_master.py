import streamlit as st
import pandas as pd
from modules.bank_processor import process_bank_statement

# 1. Page Config sabse upar
st.set_page_config(page_title="Alpha ERP Core", layout="wide")

st.title("🥷 ALPHA BIZOPS ERP")

# 2. Tabs pehle define honi chahiye
tab1, tab2, tab4 = st.tabs(["[1] Upload", "[2] Mapper", "[4] Tally XML"])

# 3. Ab 'with tab1' use karein
with tab1:
    st.subheader("🏦 Bank Statement / Bill Upload")
    mode = st.radio("Target:", ["Bank Statement", "Bill Invoice"], horizontal=True)
    file = st.file_uploader("Upload File")
    
    if file and st.button("Process"):
        if mode == "Bank Statement":
            df, metrics = process_bank_statement(file)
            if df is not None:
                st.session_state.data = df
                st.session_state.metrics = metrics
                st.dataframe(df)
                
                # Metrics Display
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Entries", metrics['total_entries'])
                c2.metric("Debits", metrics['dr_count'], f"₹{metrics['total_dr']:,.2f}")
                c3.metric("Credits", metrics['cr_count'], f"₹{metrics['total_cr']:,.2f}")
            else:
                st.error(metrics)

with tab2:
    if 'data' in st.session_state:
        st.session_state.data = st.data_editor(st.session_state.data)

with tab4:
    if st.button("Generate Tally XML"):
        xml = "<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA><TALLYMESSAGE>"
        for _, r in st.session_state.data.iterrows():
            xml += f"<VOUCHER><DATE>20260525</DATE><NARRATION>{r[1]}</NARRATION></VOUCHER>"
        xml += "</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
        st.code(xml, language="xml")
