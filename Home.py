import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(layout="wide", page_title="Alpha BizOps Engine")

# --- CORE ENGINE (No External Binaries) ---
def parse_statement_advanced(file, pwd):
    pdf_bytes = file.read()
    all_rows = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
            for page in pdf.pages:
                # Table Extraction (pdfplumber's native tool)
                table = page.extract_table(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
                if table:
                    for row in table:
                        # Row filtering: Date wali lines hi leni hain
                        all_rows.append([str(cell).replace('\n', ' ') if cell else "" for cell in row])
        
        # DataFrame creation
        df = pd.DataFrame(all_rows)
        # Assuming first row is header
        df.columns = df.iloc[0]
        df = df[1:]
        return df
    except Exception as e:
        return f"Parsing Error: {str(e)}"

# --- UI LAYER ---
st.title("🏦 Alpha BizOps - Statement Engine")
uploaded = st.file_uploader("Upload Bank PDF", type=['pdf'])
pwd = st.text_input("Password", type="password")

if st.button("🚀 Process Statement"):
    if uploaded:
        with st.spinner("Processing..."):
            result = parse_statement_advanced(uploaded, pwd)
            if isinstance(result, pd.DataFrame):
                st.session_state['data'] = result
                st.success("Extraction Successful!")
            else:
                st.error(result)

# --- DASHBOARD ---
if 'data' in st.session_state:
    df = st.session_state['data']
    st.dataframe(df, use_container_width=True)
    st.download_button("Download Tally-Ready CSV", df.to_csv(index=False), "Ledger.csv")
