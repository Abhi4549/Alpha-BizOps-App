import streamlit as st
import pandas as pd
import camelot
import os

st.set_page_config(layout="wide", page_title="Alpha BizOps Engine")

# --- ENGINE: CAMELOT (Repotic Style) ---
def parse_pdf_enterprise(file_path):
    """
    Camelot PDF table extraction (Best for Indian Bank Statements)
    """
    try:
        # Lattice mode handles grid-based bank statements
        tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
        
        all_dfs = []
        for table in tables:
            all_dfs.append(table.df)
        
        final_df = pd.concat(all_dfs)
        return final_df
    except Exception as e:
        return f"Extraction Error: {e}"

# --- UI LAYER ---
st.title("🏦 Alpha BizOps Engine: Enterprise Parser")

uploaded_file = st.file_uploader("Upload Bank PDF", type=['pdf'])

if st.button("Extract Data"):
    if uploaded_file:
        # Save temp file for Camelot
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with st.spinner("Processing through AI Engine..."):
            df = parse_pdf_enterprise("temp.pdf")
            if isinstance(df, pd.DataFrame):
                # Clean headers
                df.columns = df.iloc[0] 
                df = df[1:]
                st.session_state['data'] = df
                st.success("Successfully Mapped to Ledger.")
            else:
                st.error(df)

# --- REPOTIC-STYLE DASHBOARD ---
if 'data' in st.session_state:
    df = st.session_state['data']
    st.dataframe(df, use_container_width=True)
    st.download_button("Export Ledger (Tally XML)", df.to_csv(index=False), "Ledger.csv")
