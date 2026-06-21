import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re

st.set_page_config(layout="wide")

def process_file(file, pwd_list):
    file_content = file.read()
    
    # 1. Excel/CSV Handler
    if file.name.endswith(('.xlsx', '.xls', '.csv')):
        return pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)

    # 2. PDF Handler
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        pwd = None
        if reader.is_encrypted:
            for p in pwd_list:
                try:
                    if reader.decrypt(p): pwd = p; break
                except: continue
        
        extracted_rows = []
        with pdfplumber.open(io.BytesIO(file_content), password=pwd) as pdf:
            # Pattern: Date (DD/MM/YYYY or DD-MM-YYYY)
            date_pat = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')
            
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split('\n'):
                    match = date_pat.search(line)
                    if match:
                        parts = line.split()
                        # Extract numbers: filter parts that are purely digits/floats
                        nums = [float(p.replace(',', '')) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]
                        if len(nums) >= 1: # Kam se kam balance toh milna chahiye
                            extracted_rows.append({
                                "Date": match.group(1),
                                "Narration": " ".join([p for p in parts if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',', ''))]),
                                "Balance": nums[-1]
                            })
        
        df = pd.DataFrame(extracted_rows)
        if df.empty: return None
        
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date'])
        df['Debit'], df['Credit'] = 0.0, 0.0
        
        # Calculate Dr/Cr based on balance shift
        for i in range(1, len(df)):
            diff = round(df.loc[i, 'Balance'] - df.loc[i-1, 'Balance'], 2)
            if diff < 0: df.loc[i, 'Debit'] = abs(diff)
            elif diff > 0: df.loc[i, 'Credit'] = diff
            
        return df
    except Exception as e:
        st.error(f"Critical Parsing Error: {e}")
        return None

# UI logic waisa hi rahega... (Pass it into the structure provided previously)
