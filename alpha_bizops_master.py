import streamlit as st
from modules.bank_processor import process_bank_statement

st.set_page_config(layout="wide")
st.title("🥷 ALPHA BIZOPS [PDF PARSER]")

tab1, tab2 = st.tabs(["[1] Upload & Extract", "[2] Tally Mapper"])

with tab1:
    file = st.file_uploader("Upload Bank PDF")
    pw = st.text_input("PDF Password", type="password")
    
    if file and st.button("Extract Data"):
        df, metrics = process_bank_statement(file, pdf_pw=pw)
        if df is not None:
            st.session_state.data = df
            # Audit Summary
            c1, c2, c3 = st.columns(3)
            c1.metric("Entries", metrics['total_entries'])
            c2.metric("Debit Total", f"₹{metrics['total_dr']:,.2f}")
            c3.metric("Credit Total", f"₹{metrics['total_cr']:,.2f}")
            st.dataframe(df)
        else:
            st.error(metrics)
