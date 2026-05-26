import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. FRONTEND: ALPHA BIZOPS UI
# ==========================================
st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🥷", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🥷 Alpha BizOps Hub [NO-API ENGINE]</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">100% Free, Secure, and Locally Processed Tally Formatter</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: SMART HEURISTIC PARSER (AI-Alternative)
# ==========================================
def clean_amount(val):
    """Numbers se comma aur text hata kar pure float mein badalna"""
    if not val: 
        return 0.0
    val = str(val).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def process_smart_no_api(file, password=""):
    extracted_data = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0}
    
    try:
        with pdfplumber.open(file, password=password) as pdf:
            # Date Pattern: 12/04/2026, 12-Apr-2026, etc.
            date_pattern = re.compile(r'^\d{1,2}[/\-\s]([a-zA-Z]{3}|\d{1,2})[/\-\s]\d{2,4}')
            
            for page in pdf.pages:
                # Text-based grid layout extract
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "intersection_tolerance": 15,
                    "snap_tolerance": 5,
                })
                
                for table in tables:
                    current_txn = None  # Buffer to hold transaction and stitch narration
                    
                    for row in table:
                        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        compact_row = [cell for cell in cleaned_row if cell != ""]
                        
                        if not compact_row: 
                            continue
                        row_text = " ".join(compact_row).lower()
                        
                        # --- Opening / Closing Balance Extractor ---
                        if "opening balance" in row_text or "b/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["opening_bal"] = clean_amount(nums[-1])
                        if "closing balance" in row_text or "c/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["closing_bal"] = clean_amount(nums[-1])

                        # --- Transaction & Narration Logic ---
                        if date_pattern.search(compact_row[0]):
                            # Save the previous transaction before starting a new one
                            if current_txn:
                                extracted_data.append(current_txn)
                            
                            date = compact_row[0]
                            narration = compact_row[1] if len(compact_row) > 1 else ""
                            
                            # Extract amounts from the end of the row
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
                                
                            current_txn = {
                                "Date": date,
                                "Narration": narration,
                                "Debit": debit,
                                "Credit": credit,
                                "Balance": balance
                            }
                            
                            if debit > 0: meta["debit_count"] += 1
                            if credit > 0: meta["credit_count"] += 1
                            
                        else:
                            # SMART STITCHING: If row has no date, it is part of the previous narration
                            # Ignore junk lines like "Page 1 of 2" or "Statement Summary"
                            junk_words = ["page", "statement", "summary", "branch"]
                            if current_txn and not any(j in row_text for j in junk_words):
                                extra_text = " ".join(compact_row)
                                # Append it smoothly
                                current_txn["Narration"] += " " + extra_text
                                
                    # End of table, append the last transaction
                    if current_txn:
                        extracted_data.append(current_txn)
                        
        return extracted_data, meta, "Success"
    except Exception as e:
        return None, None, str(e)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 3. DASHBOARD EXECUTION
# ==========================================
st.sidebar.title("Configuration")
st.sidebar.success("✅ Running No-API Heuristic Engine")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Select Tool", ["🏦 Bank Statement Cleaner", "🧾 Future Tools"])

if menu == "🏦 Bank Statement Cleaner":
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        pdf_password = col1.text_input("PDF Password (if any)", type="password")
        
        if st.button("🚀 Process & Clean Data", use_container_width=True):
            with st.spinner("Smart Heuristic Engine is analyzing the document..."):
                raw_data, meta, status = process_smart_no_api(uploaded_file, pdf_password)
                
                if raw_data:
                    df = pd.DataFrame(raw_data)
                    st.success("✅ Data Cleaned and Stitched Successfully!")
                    
                    st.markdown("### 📊 Statement Summary")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {meta["opening_bal"]:,.2f}</div>', unsafe_allow_html=True)
                    m2.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {meta["closing_bal"]:,.2f}</div>', unsafe_allow_html=True)
                    m3.markdown(f'<div class="metric-card"><b>Total Debits</b><br>{meta["debit_count"]} Txns</div>', unsafe_allow_html=True)
                    m4.markdown(f'<div class="metric-card"><b>Total Credits</b><br>{meta["credit_count"]} Txns</div>', unsafe_allow_html=True)
                    
                    st.write("<br>", unsafe_allow_html=True)
                    st.write("### 📝 Tally-Ready Data Preview")
                    st.dataframe(df, use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "tally_ready.csv", "text/csv", use_container_width=True)
                    c2.download_button("Download Excel", to_excel(df), "tally_ready.xlsx", use_container_width=True)
                else:
                    st.error(f"❌ Error: {status}")

elif menu == "🧾 Future Tools":
    st.info("Additional offline tools can be added here without breaking the core system.")
