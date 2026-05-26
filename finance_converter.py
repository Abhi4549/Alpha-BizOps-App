import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. FRONTEND: SAAS UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="Alpha Finance Converter", page_icon="⚙️", layout="centered")

# Custom CSS to make it look like a professional website (financefileconverter.com clone)
st.markdown("""
    <style>
    .hero-title { font-size: 48px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 10px;}
    .hero-subtitle { font-size: 18px; color: #4B5563; text-align: center; margin-bottom: 40px;}
    .upload-box { border: 2px dashed #3B82F6; padding: 30px; border-radius: 10px; background-color: #EFF6FF; text-align: center;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">Finance File Converter</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Convert PDF Bank Statements to CSV & Excel instantly. Highly accurate and secure.</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: CONVERSION ENGINE LOGIC
# ==========================================
def process_pdf_statement(file, password=""):
    extracted_data = []
    try:
        with pdfplumber.open(file, password=password) as pdf:
            for page in pdf.pages:
                # Extracting table using robust strategy
                table = page.extract_table(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
                
                if table:
                    for row in table:
                        # Cleaning empty cells and standardizing
                        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        
                        # Basic validation: Check if first column looks like a date
                        if cleaned_row and re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cleaned_row[0]):
                            extracted_data.append(cleaned_row)
        return extracted_data, "Success"
    except Exception as e:
        return None, str(e)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# ==========================================
# 3. FRONTEND: USER INTERACTION WIDGETS
# ==========================================
st.markdown('<div class="upload-box">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Drop your Bank Statement PDF here", type=['pdf'])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    st.write("---")
    st.subheader("⚙️ Conversion Settings")
    
    col1, col2 = st.columns(2)
    pdf_password = col1.text_input("PDF Password (Leave blank if none)", type="password")
    export_format = col2.selectbox("Export Format", ["CSV (Tally/Standard)", "Excel (.xlsx)"])
    
    if st.button("🚀 Convert Statement", use_container_width=True):
        with st.spinner("Our AI engine is extracting tabular data..."):
            
            # Call Backend Logic
            raw_data, status = process_pdf_statement(uploaded_file, pdf_password)
            
            if raw_data:
                st.success("✅ Conversion Successful!")
                
                # Assuming standard 4 columns: Date, Description, Debit, Credit
                # If the bank has more columns, pandas will handle it dynamically
                col_count = len(raw_data[0]) if raw_data else 4
                headers = ["Date", "Narration/Description", "Debit", "Credit", "Balance", "Extra1", "Extra2"][:col_count]
                
                # Create DataFrame
                df = pd.DataFrame(raw_data, columns=headers if len(headers) == col_count else None)
                
                # Show Preview
                st.write("### Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Download Logic
                st.write("### Download Your File")
                if export_format == "CSV (Tally/Standard)":
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name="converted_statement.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    excel_data = to_excel(df)
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name="converted_statement.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                if "password" in status.lower():
                    st.error("🔒 PDF is password protected or incorrect password provided.")
                else:
                    st.error(f"❌ Could not extract data: {status}")

# Footer
st.write("---")
st.caption("Alpha BizOps Security: Your files are processed in-memory and are never stored on our servers.")
