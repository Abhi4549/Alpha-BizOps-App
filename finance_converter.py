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

st.markdown('<div class="hero-title">Finance File Converter (Tally Pro)</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Deep Cleaned CSV/Excel engine optimized strictly for Tally Import</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: DEEP CLEANING ENGINE LOGIC
# ==========================================
def clean_amount(val):
    """Numbers se comma aur text hata kar pure float mein badalna"""
    if not val: return 0.0
    val = str(val).replace(',', '').replace('Cr', '').replace('Dr', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def process_tally_standard(file, password=""):
    extracted_data = []
    metadata = {
        "opening_bal": 0.0,
        "closing_bal": 0.0,
        "debit_count": 0,
        "credit_count": 0
    }
    
    try:
        with pdfplumber.open(file, password=password) as pdf:
            for page in pdf.pages:
                # Vertical lines ko ignore karke text block uthana
                table = page.extract_table(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
                
                if table:
                    for row in table:
                        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        row_text = " ".join(cleaned_row).lower()
                        
                        # --- 1. Opening/Closing Balance Extractor ---
                        if "opening balance" in row_text or "b/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: metadata["opening_bal"] = clean_amount(nums[-1])
                            
                        if "closing balance" in row_text or "c/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: metadata["closing_bal"] = clean_amount(nums[-1])

                        # --- 2. Strict Date & Transaction Check ---
                        # Sirf wo row jiska pehla column Date format mein ho (e.g., 12/05/2026 or 12-05-26)
                        if cleaned_row and re.search(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cleaned_row[0]):
                            date = cleaned_row[0]
                            narration = cleaned_row[1] if len(cleaned_row) > 1 else ""
                            
                            # Amount logic: Last ki 3 values aksar Debit, Credit, Balance hoti hain
                            amounts = [clean_amount(x) for x in cleaned_row[2:] if re.match(r'^-?[\d,]+(\.\d+)?$', str(x).replace(',',''))]
                            
                            debit = 0.0
                            credit = 0.0
                            balance = 0.0
                            
                            if len(amounts) >= 3:
                                debit, credit, balance = amounts[-3], amounts[-2], amounts[-1]
                            elif len(amounts) == 2:
                                debit, credit = amounts[0], amounts[1]
                            elif len(amounts) == 1:
                                # Agar ek hi number ho toh hum assume karte hain Debit/Credit column mix hai
                                val = amounts[0]
                                if "cr" in row_text: credit = val
                                else: debit = val

                            # Increment Counters
                            if debit > 0: metadata["debit_count"] += 1
                            if credit > 0: metadata["credit_count"] += 1
                            
                            extracted_data.append({
                                "Date": date,
                                "Narration": narration,
                                "Debit": debit,
                                "Credit": credit,
                                "Balance": balance
                            })
                            
        return extracted_data, metadata, "Success"
    except Exception as e:
        return None, None, str(e)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 3. FRONTEND: USER INTERACTION
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])

if uploaded_file:
    st.write("---")
    col1, col2 = st.columns(2)
    pdf_password = col1.text_input("PDF Password (if any)", type="password")
    
    if st.button("🚀 Process & Clean for Tally", use_container_width=True):
        with st.spinner("Applying Tally Standard Cleansing Rules..."):
            
            raw_data, meta, status = process_tally_standard(uploaded_file, pdf_password)
            
            if raw_data:
                df = pd.DataFrame(raw_data)
                
                st.success("✅ Deep Cleaning Completed!")
                
                # --- METRICS DASHBOARD ---
                st.markdown("### 📊 Statement Summary")
                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {meta["opening_bal"]:,.2f}</div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {meta["closing_bal"]:,.2f}</div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card"><b>Total Debits</b><br>{meta["debit_count"]} Txns</div>', unsafe_allow_html=True)
                m4.markdown(f'<div class="metric-card"><b>Total Credits</b><br>{meta["credit_count"]} Txns</div>', unsafe_allow_html=True)
                
                st.write("<br>", unsafe_allow_html=True)
                
                # --- CLEANED DATA PREVIEW ---
                st.write("### 📝 Tally-Ready Data Preview")
                st.dataframe(df, use_container_width=True)
                
                # --- EXPORT BUTTONS ---
                st.write("### 📥 Export")
                c1, c2 = st.columns(2)
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                c1.download_button("Download CSV (Tally Format)", csv_data, "tally_ready.csv", "text/csv", use_container_width=True)
                
                excel_data = to_excel(df)
                c2.download_button("Download Excel (.xlsx)", excel_data, "tally_ready.xlsx", use_container_width=True)
                
            else:
                st.error(f"❌ Error: {status}")
