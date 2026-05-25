import streamlit as st
from modules.bank_processor import process_bank_statement
from modules.ocr_engine import process_invoice_pdf

st.set_page_config(layout="wide")
st.title("🥷 Alpha ERP Core")

tab1, tab2, tab4 = st.tabs(["[1] Upload", "[2] Mapper", "[4] Tally XML"])

with tab1:
    mode = st.radio("Select:", ["Bank Statement", "Bill Invoice"])
    file = st.file_uploader("Upload")
    if file and st.button("Process"):
        if mode == "Bank Statement":
            df, res = process_bank_statement(file)
            st.session_state.data = df
            st.dataframe(df)
        else:
            df, status = process_invoice_pdf(file)
            st.session_state.data = df
            st.dataframe(df)

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
