import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

st.set_page_config(layout="wide")

def get_data_from_pdf(file, pwd):
    pdf_bytes = file.read()
    raw_text = ""
    
    # Text extraction with protection
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
    except Exception as e:
        return f"PDF Open Error: {e}"

    if not raw_text: return "No text found in PDF."

    # Pattern extraction (Date, Description, Amount)
    rows = []
    # Logic: Har wo line uthao jisme date (DD/MM/YYYY) hai
    for line in raw_text.split('\n'):
        # Matches: Date (optional space) Description (optional space) Amount
        match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})', line)
        if match:
            rows.append({
                "Date": match.group(1),
                "Narration": match.group(2),
                "Amount": float(match.group(3).replace(',', ''))
            })
    
    if not rows: return "No transaction pattern matched."
    
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df['Debit'] = df['Amount'].apply(lambda x: abs(x) if x < 0 else 0.0)
    df['Credit'] = df['Amount'].apply(lambda x: x if x > 0 else 0.0)
    return df

# UI Layer
st.title("🏦 Alpha BizOps - Statement Processor")
uploaded = st.file_uploader("Upload PDF", type=['pdf'])
pwd = st.text_input("Password", type="password")

if st.button("🚀 Process"):
    if uploaded:
        result = get_data_from_pdf(uploaded, pwd)
        if isinstance(result, pd.DataFrame):
            st.session_state['df'] = result
            st.success("Extraction Done!")
        else:
            st.error(result)

if 'df' in st.session_state:
    df = st.session_state['df']
    
    # Metrics - Safe from empty sum error
    c1, c2, c3 = st.columns(3)
    c1.metric("Debits", f"₹{df['Debit'].sum():,.2f}")
    c2.metric("Credits", f"₹{df['Credit'].sum():,.2f}")
    c3.metric("Total Rows", len(df))
    
    st.dataframe(df, use_container_width=True)
