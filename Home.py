import streamlit as st
import pandas as pd
import pdfplumber
import pikepdf
import io
import tempfile
import os

st.set_page_config(page_title="Bank Ledger to Tally Converter", layout="wide")

st.title("🏦 Bank Statement to Tally Ledger Converter")
st.markdown("Upload your Bank Statement (PDF/CSV/Excel) to convert it into a Tally-ready Excel format.")

# File Uploader
uploaded_file = st.file_uploader("Upload Bank Statement", type=["pdf", "csv", "xlsx"])
pdf_password = st.text_input("Enter PDF Password (if protected):", type="password")

def decrypt_pdf(file, password):
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        with pikepdf.open(file, password=password) as pdf:
            pdf.save(temp_file.name)
        return temp_file.name
    except pikepdf.PasswordError:
        st.error("Incorrect Password! Please enter the correct password.")
        return None
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def extract_data_from_pdf(pdf_path):
    all_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        all_data.append(row)
        return pd.DataFrame(all_data[1:], columns=all_data[0]) if all_data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error extracting data: {e}")
        return pd.DataFrame()

if uploaded_file is not None:
    df = pd.DataFrame()
    
    # Process PDF
    if uploaded_file.name.endswith('.pdf'):
        file_to_process = uploaded_file
        
        # Handle Encryption
        if pdf_password:
            decrypted_path = decrypt_pdf(uploaded_file, pdf_password)
            if decrypted_path:
                df = extract_data_from_pdf(decrypted_path)
                os.remove(decrypted_path) # Clean up temp file
        else:
            try:
                df = extract_data_from_pdf(uploaded_file)
            except Exception:
                st.warning("This PDF might be password protected. Please enter the password above.")
                
    # Process CSV/Excel
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)

    # Display Data
    if not df.empty:
        st.success("File processed successfully!")
        st.write("### Preview of Extracted Data:")
        st.dataframe(df)

        # Download Button for Tally Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tally_Ledger')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 Download Tally-Ready Excel",
            data=excel_data,
            file_name="Tally_Converted_Ledger.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        if uploaded_file.name.endswith('.pdf') and not pdf_password:
            st.info("If the table is empty, the PDF might be encrypted or heavily formatted.")
