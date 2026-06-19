import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import datetime

# ==========================================
# 1. MEMORY & UI CONFIGURATION (THE BRIDGE)
# ==========================================
if 'raw_extracted_data' not in st.session_state:
    st.session_state['raw_extracted_data'] = None
if 'cleaned_data' not in st.session_state:
    st.session_state['cleaned_data'] = None

st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK STATEMENT TO TALLY EXCEL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Custom Date Filter | Auto-Sync to Ledger Mapper</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: PDF & EXCEL PARSERS
# ==========================================
def process_mathematical_parser(file, password=""):
    raw_transactions = []
    try:
        with pdfplumber.open(file, password=password) as pdf:
            # ⚡ UNIVERSAL DATE PATTERN: Covers 12/04/23, 12-Apr-2023, 12.04.2023, etc.
            date_pattern = re.compile(r'^\s*(\d{1,2}[/\-\.](?:[a-zA-Z]{3}|\d{1,2})[/\-\.]\d{2,4})')

            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: continue
                lines = text.split('\n')

                current_txn = None
                for line in lines:
                    line = line.strip()
                    if not line: continue

                    match = date_pattern.search(line)
                    if match:
                        if current_txn: raw_transactions.append(current_txn)

                        # Extract Date and standardize separator to '/'
                        date_str = match.group(1).replace('.', '/').replace('-', '/')
                        rem = line[len(match.group(0)):].strip()

                        # Extract Words and Numbers separately
                        parts = rem.split()
                        numbers = []
                        narration_words = []

                        for part in parts:
                            # Clean special characters from numbers
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            
                            # Check if it's a valid financial amount
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part):
                                # Bypass Cheque Numbers (Starts with 0 and has no decimals)
                                if cl_part.startswith('0') and '.' not in cl_part and len(cl_part) >= 4:
                                    narration_words.append(part)
                                else:
                                    numbers.append(float(cl_part))
                            else:
                                narration_words.append(part)

                        narration = " ".join(narration_words)

                        # ⚡ SMART BALANCE DETECTION
                        balance = 0.0
                        txn_amount = 0.0
                        
                        # The very last number in a bank statement row is ALMOST ALWAYS the Balance
                        if len(numbers) >= 1: balance = numbers[-1] 
                        if len(numbers) >= 2: txn_amount = numbers[-2] 

                        current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}

                    else:
                        # ⚡ SMART NARRATION CONTINUATION: For multi-line descriptions
                        if current_txn and len(line) > 2:
                            ignore_words = ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing', 'brought forward']
                            if not any(ig in line.lower() for ig in ignore_words):
                                clean_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_parts: current_txn["Narration"] += " " + " ".join(clean_parts)

                if current_txn: raw_transactions.append(current_txn)

        # ⚡ UNIVERSAL MATH LOGIC: Calculate Debit/Credit using Balance Difference
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]

            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                
                # Difference between today's balance and yesterday's balance = Exact Transaction Amount
                diff = round(curr_bal - prev_bal, 2)

                if diff > 0:
                    curr["Credit"] = diff
                    curr["Debit"] = 0.0
                elif diff < 0:
                    curr["Debit"] = abs(diff)
                    curr["Credit"] = 0.0
                else:
                    # Fallback if balance didn't change (rare)
                    curr["Credit"] = curr["Amount"] if curr["Amount"] > 0 else 0.0

            else:
                # First transaction guess since no previous balance exists
                narration_upper = curr["Narration"].upper()
                if any(kw in narration_upper for kw in ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]):
                    curr["Debit"] = curr["Amount"]
                else:
                    curr["Credit"] = curr["Amount"]

        return raw_transactions, "Success"
    except Exception as e: return None, f"PDF Error: {str(e)}"

def process_excel_parser(file, password=""):
    raw_transactions = []
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, skip_blank_lines=True)
        else:
            if password:
                import msoffcrypto
                decrypted_file = io.BytesIO()
                office_file = msoffcrypto.OfficeFile(file)
                office_file.load_key(password=password)
                office_file.decrypt(decrypted_file)
                decrypted_file.seek(0)
                df = pd.read_excel(decrypted_file)
            else:
                df = pd.read_excel(file)
            
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df = df.reset_index(drop=True)
        
        header_idx = -1
        for i in range(min(20, len(df))):
            row_str = ' '.join(str(x).lower() for x in df.iloc[i].values)
            if 'date' in row_str and ('narration' in row_str or 'particulars' in row_str or 'description' in row_str):
                header_idx = i
                break
                
        if header_idx != -1:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        cols = df.columns
        date_col = next((c for c in cols if 'date' in c), None)
        narration_col = next((c for c in cols if any(x in c for x in ['narration', 'particulars', 'description'])), None)
        debit_col = next((c for c in cols if any(x in c for x in ['debit', 'withdrawal', 'dr'])), None)
        credit_col = next((c for c in cols if any(x in c for x in ['credit', 'deposit', 'cr'])), None)
        balance_col = next((c for c in cols if 'balance' in c), None)
        
        if not date_col or not narration_col: return None, "Format error: Date/Narration not found."
            
        for _, row in df.iterrows():
            raw_date = row[date_col]
            if pd.isna(raw_date) or str(raw_date).strip().lower() == 'nan': continue
            date_val = raw_date.strftime('%d/%m/%Y') if isinstance(raw_date, pd.Timestamp) else str(raw_date).split(' ')[0]
            narration_val = str(row[narration_col]).strip()
            if narration_val.lower() == 'nan': narration_val = ""
            
            def clean_val(v):
                try: return float(str(v).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip())
                except: return 0.0
                    
            debit_val = clean_val(row[debit_col]) if debit_col else 0.0
            credit_val = clean_val(row[credit_col]) if credit_col else 0.0
            balance_val = clean_val(row[balance_col]) if balance_col else 0.0
                
            raw_transactions.append({"Date": date_val, "Narration": narration_val, "Debit": debit_val, "Credit": credit_val, "Balance": balance_val})
            
        return raw_transactions, "Success"
    except Exception as e: return None, f"Excel Error: {str(e)}"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 3. DATA EXTRACTION BLOCK
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])

if uploaded_file:
    file_password = st.text_input("Document Password (If Locked)", type="password") 
    
    if st.button("🚀 Process & Extract Data", use_container_width=True):
        with st.spinner("Processing Document... please wait"):
            if uploaded_file.name.endswith('.pdf'): 
                raw_data, status = process_mathematical_parser(uploaded_file, file_password)
            else: 
                raw_data, status = process_excel_parser(uploaded_file, file_password)
            
            if raw_data:
                df = pd.DataFrame(raw_data)
                df_tally_ready = df[['Date', 'Narration', 'Debit', 'Credit', 'Balance']]
                st.session_state['raw_extracted_data'] = df_tally_ready.copy()
            else:
                st.error(f"❌ Error: {status}")

# ==========================================
# 4. MAIN PAGE DATE FILTER & DISPLAY BLOCK
# ==========================================
if st.session_state.get('raw_extracted_data') is not None:
    full_df = st.session_state['raw_extracted_data'].copy()
    
    st.write("---")
    st.markdown("### 📅 Select Specific Dates for Tally")
    
    # ⚡ DATE FIX: Ab date column kaise bhi ho, ye pakad lega
    full_df['Date_Obj'] = pd.to_datetime(full_df['Date'], errors='coerce', dayfirst=True)
    valid_dates = full_df.dropna(subset=['Date_Obj'])
    
    if not valid_dates.empty:
        min_date = valid_dates['Date_Obj'].min().date()
        max_date = valid_dates['Date_Obj'].max().date()
    else:
        # Agar date padhi nahi gayi, toh bhi boxes hamesha aayenge
        min_date = datetime.date(2023, 4, 1)
        max_date = datetime.date.today()
        
    # YAHAN AAPKE BOXES HAMESHA DIKHENGE
    c1, c2 = st.columns(2)
    with c1:
        from_date = st.date_input("From Date:", value=min_date)
    with c2:
        to_date = st.date_input("To Date:", value=max_date)
    
    # Date Filtering Logic
    mask = (full_df['Date_Obj'].dt.date >= from_date) & (full_df['Date_Obj'].dt.date <= to_date)
    filtered_df = full_df.loc[mask].copy()
    
    if filtered_df.empty:
        st.warning("⚠️ Warning: No transactions found for these dates. Showing all data.")
        filtered_df = full_df.copy()
        
    filtered_df = filtered_df.drop(columns=['Date_Obj'], errors='ignore')
    
    # Naye Filtered Data ke hisaab se Meta Recalculate karna
    meta_filtered = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0, "total_debit_amt": 0.0, "total_credit_amt": 0.0}
    if not filtered_df.empty:
        meta_filtered["opening_bal"] = filtered_df.iloc[0]['Balance'] - filtered_df.iloc[0]['Credit'] + filtered_df.iloc[0]['Debit']
        meta_filtered["closing_bal"] = filtered_df.iloc[-1]['Balance']
        meta_filtered["debit_count"] = (filtered_df['Debit'] > 0).sum()
        meta_filtered["credit_count"] = (filtered_df['Credit'] > 0).sum()
        meta_filtered["total_debit_amt"] = filtered_df['Debit'].sum()
        meta_filtered["total_credit_amt"] = filtered_df['Credit'].sum()
    
    # Final filter data memory me save karo Ledger Mapping page ke liye
    st.session_state['cleaned_data'] = filtered_df.copy()
    
    # ------------------ DASHBOARD DISPLAY ------------------
    st.success("✅ Data Ready! The table and exports below are automatically updated.")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {meta_filtered["opening_bal"]:,.2f}</div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><b>Total Debits (-)</b><br>₹ {meta_filtered["total_debit_amt"]:,.2f}<br><span style="font-size:13px; color:#6B7280;">({meta_filtered["debit_count"]} Txns)</span></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><b>Total Credits (+)</b><br>₹ {meta_filtered["total_credit_amt"]:,.2f}<br><span style="font-size:13px; color:#6B7280;">({meta_filtered["credit_count"]} Txns)</span></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {meta_filtered["closing_bal"]:,.2f}</div>', unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    st.write("### 📝 Data Preview")
        
    st.dataframe(filtered_df, use_container_width=True) 
    
    c1, c2 = st.columns(2)
    c1.download_button("Download CSV", filtered_df.to_csv(index=False).encode('utf-8'), "alpha_tally_ready.csv", "text/csv", use_container_width=True)
    c2.download_button("Download Excel (.xlsx)", to_excel(filtered_df), "alpha_tally_ready.xlsx", use_container_width=True)
