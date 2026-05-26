import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. FRONTEND: SAAS UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="Alpha Finance Converter", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 40px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">Alpha Finance Converter (Tally Pro)</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Deep Cleaned CSV/Excel engine optimized strictly for Tally Import</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: PRO DEEP CLEANING ENGINE 
# ==========================================
def clean_amount(val):
    """Numbers se comma aur text hata kar pure float mein badalna"""
    if not val: return 0.0
    val = str(val).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def process_tally_standard(file, password=""):
    extracted_data = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0}
    
    try:
        with pdfplumber.open(file, password=password) as pdf:
            # Smart Date Pattern (DD/MM/YYYY, DD-MM-YYYY, DD-MMM-YYYY)
            date_pattern = re.compile(r'^\d{1,2}[/\-\s]([a-zA-Z]{3}|\d{1,2})[/\-\s]\d{2,4}')
            
            for page in pdf.pages:
                # Advanced Snap Tolerance for invisible grids
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "intersection_tolerance": 15,
                    "snap_tolerance": 5,
                })
                
                for table in tables:
                    temp_row = None  # Buffer for merging multi-line narration
                    
                    for row in table:
                        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        # Remove completely blank items to fix column shifts
                        compact_row = [cell for cell in cleaned_row if cell != ""]
                        
                        if not compact_row: continue
                        row_text = " ".join(compact_row).lower()
                        
                        # --- Opening / Closing Balance Extractor ---
                        if "opening balance" in row_text or "b/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["opening_bal"] = clean_amount(nums[-1])
                        if "closing balance" in row_text or "c/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["closing_bal"] = clean_amount(nums[-1])

                        # --- Transaction Extractor ---
                        if date_pattern.search(compact_row[0]):
                            # Agar pichli entry complete ho gayi thi, toh usko save karo
                            if temp_row:
                                extracted_data.append(temp_row)
                            
                            date = compact_row[0]
                            narration = compact_row[1] if len(compact_row) > 1 else ""
                            
                            # Piche se amounts nikalna (Debit, Credit, Balance)
                            amounts = [clean_amount(x) for x in compact_row[2:] if re.match(r'^-?[\d,]+(\.\d{1,2})?$', str(x).replace(',',''))]
                            
                            debit, credit, balance = 0.0, 0.0, 0.0
                            
                            if len(amounts) >= 3:
                                debit, credit, balance = amounts[-3], amounts[-2], amounts[-1]
                            elif len(amounts) == 2:
                                debit, credit = amounts[0], amounts[1]
                            elif len(amounts) == 1:
                                val = amounts[0]
                                if "cr" in row_text: credit = val
                                else: debit = val
                                
                            temp_row = {
                                "Date": date,
                                "Narration": narration,
                                "Debit": debit,
                                "Credit": credit,
                                "Balance": balance
                            }
                            
                            if debit > 0:
