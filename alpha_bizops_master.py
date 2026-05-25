import streamlit as st
import pandas as pd
from modules.bank_processor import process_bank_statement
from modules.ocr_engine import process_invoice_pdf

st.set_page_config(page_title="Alpha ERP", layout="wide")

st.title("🥷 ALPHA BIZOPS ERP CORE")

tab1, tab2, tab4 = st.tabs(["[1] Upload", "[2] Mapper", "[4] Tally XML"])

with tab1:
    mode = st.radio("Select:", ["Bank Statement", "Bill Invoice"], horizontal=True)
    file = st.file_uploader("Upload File")
    
    if file and st.button("Process Data"):
        if mode == "Bank Statement":
            df, status = process_bank_statement(file)
        else:
            df, status = process_invoice_pdf(file)
            
        if df is not None:
            st.session_state.data = df
            st.success(status)
            st.dataframe(df)
        else:
            st.error(status)

with tab2:
    if 'data' in st.session_state:
        st.session_state.data = st.data_editor(st.session_state.data)

with tab4:
    if 'data' in st.session_state and st.button("Generate Tally XML"):
        xml = "<ENVELOPE><TALLYMESSAGE>"
        for _, r in st.session_state.data.iterrows():
            xml += f"<VOUCHER><NARRATION>{str(r[0])}</NARRATION></VOUCHER>"
        xml += "</TALLYMESSAGE></ENVELOPE>"
        st.code(xml, language="xml")
