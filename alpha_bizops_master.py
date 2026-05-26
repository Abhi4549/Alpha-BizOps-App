import streamlit as st
import pandas as pd
from logic.parser import extract_data

st.set_page_config(layout="wide", page_title="Bank-to-Tally Pro")
st.title("🥷 ALPHA BIZOPS [TALLY SYNC ENGINE]")

# Tab System
tab1, tab2 = st.tabs(["[1] PDF/Excel Upload", "[2] Tally Mapping"])

with tab1:
    uploaded_file = st.file_uploader("Upload Bank Statement")
    pdf_pw = st.text_input("Password (if any)", type="password")
    
    if uploaded_file and st.button("Extract"):
        df = extract_data(uploaded_file, pdf_pw)
        st.session_state.data = df
        st.dataframe(df)

with tab2:
    if 'data' in st.session_state:
        st.subheader("Map Columns to Tally")
        # Column Selector
        cols = st.session_state.data.columns
        date_map = st.selectbox("Select Date Column", cols)
        narr_map = st.selectbox("Select Narration Column", cols)
        amt_map = st.selectbox("Select Amount Column", cols)
        
        if st.button("Generate Tally XML"):
            # XML Generator Logic
            xml = "<ENVELOPE><TALLYMESSAGE>"
            for _, r in st.session_state.data.iterrows():
                xml += f"<VOUCHER><DATE>{r[date_map]}</DATE><NARRATION>{r[narr_map]}</NARRATION><AMOUNT>{r[amt_map]}</AMOUNT></VOUCHER>"
            xml += "</TALLYMESSAGE></ENVELOPE>"
            st.code(xml, language="xml")
            st.download_button("Download XML", xml, "tally_import.xml")
