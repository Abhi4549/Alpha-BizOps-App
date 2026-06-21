import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

# ==========================================
# 1. MEMORY & UI CONFIGURATION
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
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Smart Auto-Unlock | Universal Format</div>', unsafe_allow_html=True)

# ==========================================
# 2. SMART PASSWORD ENGINE (INDIAN BANKS)
# ==========================================
def generate_bank_passwords(name, dob, pan, custom_pwd):
    passwords = []
    if custom_pwd: passwords.append(custom_pwd.strip())
    
    if dob:
        d_str = dob.strftime("%d")
        m_str = dob.strftime("%m")
        y_full = dob.strftime("%Y")
        y_short = dob.strftime("%y")
        passwords.extend([f"{d_str}{m_str}{y_full}", f"{d_str}{m_str}{y_short}"])
        
        if name:
            name_clean = re.sub(r'[^a-zA-Z]', '', name)
            if len(name_clean) >= 4:
                first_4_lower = name_clean[:4].lower()
                first_4_upper = name_clean[:4].upper()
                passwords.extend([
                    f"{first_4_lower}{d_str}{m_str}",
                    f"{first_4_upper}{d_str}{m_str}",
                    f"{first_4_lower}{d_str}{m_str}{y_full}"
                ])
                
    if pan:
        passwords.extend([pan.lower().strip(), pan.upper().strip()])
        
    return list(set(passwords))

# ==========================================
# 3. BACKEND: PDF PARSER WITH PyPDF2 BYPASS
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    file.seek(0)
    
    unlocked_pdf_stream = None
    
    # ⚡ ENGINE 1: PyPDF2 SECURITY BYPASS
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if not pwd: 
                    continue
                try:
                    if pdf_reader.decrypt(pwd): 
                        unlocked = True
                        break
                except Exception:
                    continue
            
            if not unlocked:
                return None, "PDF is locked. Auto-Unlock failed. Please provide exact Password/PAN/DOB."
            
            pdf_writer = PyPDF2.PdfWriter()
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            unlocked_pdf_stream = io.BytesIO()
            pdf_writer.write(unlocked_pdf_stream)
            unlocked_pdf_stream.seek(0)
        else:
            unlocked_pdf_stream = io.BytesIO(pdf_bytes)
            
    except Exception as e:
        return None, f"Decryption Engine Error: {str(e)}"

    # ⚡ ENGINE 2: PDFPLUMBER EXTRACTION WITH GOD-MODE REGEX
    try:
        with pdfplumber.open(unlocked_pdf_stream) as pdf:
            date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})')

            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: 
                    text = page.extract_text()
                if not text: 
                    continue
                
                lines = text.split('\n')

                current_txn = None
                for line in lines:
                    line = line.strip()
                    if not line: 
                        continue

                    match = date_pattern.search(line)
                    if match:
                        if current_txn: 
                            raw_transactions.append(current_txn)

                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        date_str = re.sub(r'/+', '/', date_str)
                        
                        rem = line[len(match.group(0)):].strip()

                        parts = rem.split()
                        numbers = []
                        narration_words = []

                        for part in parts:
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part):
                                if cl_part.startswith('0') and '.' not in cl_part and len(cl_part) >= 4:
                                    narration_words.append(part)
                                else:
                                    numbers.append(float(cl_part))
                            else:
                                narration_words.append(part)

                        narration = " ".join(narration_words)

                        balance = 0.0
                        txn_amount = 0.0
                        if len(numbers) >= 1: balance = numbers[-1] 
                        if len(numbers) >= 2: txn_amount = numbers[-2] 

                        current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}

                    else:
                        if current_txn and len(line) > 2:
                            ignore_words = ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing', 'brought forward']
                            if not any(ig in line.lower() for ig in ignore_words):
                                clean_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_parts: 
                                    current_txn["Narration"] += " " + " ".join(clean_parts)

                if current_txn: 
                    raw_transactions.append(current_txn)

        if not raw_transactions:
            return None, "Document unlocked, but no transactions found. Bank format might be unsupported or it's a scanned photo."

        # ⚡ ENGINE 3: THE FIX FOR THE "FIRST LINE" ERROR
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            narration_upper = curr["Narration"].upper()
            
            # Puraani pehli line ko detect karo
            is_opening_bal = any(kw in narration_upper for kw in ["OPENING", "BROUGHT FORWARD", "B/F", "BAL B/F", "O/B", "INITIAL"])
            
            if is_opening_bal:
                curr["Debit"] = 0.0
                curr["Credit"] = 0.0
                curr["Amount"] = 0.0
                # Balance as it is rahega
                continue

            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                diff = round(curr_bal - prev_bal, 2)

                if diff > 0:
                    curr["Credit"] = diff
                    curr["Debit"] = 0.0
                elif diff < 0:
                    curr["Debit"] = abs(diff)
                    curr["Credit"] = 0.0
                else:
                    curr["Credit"] = curr["Amount"] if curr["Amount"] > 0 else 0.0
            else:
                # Agar pehli line real transaction hai (opening balance nahi hai)
                if any(kw in narration_upper for kw in ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]):
                    curr["Debit"] = curr["Amount"]
                else:
                    curr["Credit"] = curr["Amount"]

        return raw_transactions, "Success"
    except Exception as e: 
        return None, f"Parsing Error: {str(e)}"

# ==========================================
# 4. EXCEL CSV PARSER
# ==========================================
def process_excel_parser(file):
    raw_transactions = []
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, skip_blank_lines=True)
        else: df = pd.read_excel(file)
            
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
# 5. UI: DATA EXTRACTION BLOCK
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])

if uploaded_file:
    st.markdown("### 🔐 Smart Auto-Unlock (For Locked PDFs)")
    st.info("Enter client details once, and we'll automatically try all combinations (ICICI, SBI, Axis formats).")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: client_name = st.text_input("First Name (e.g. Rahul)", help="Required for ICICI/Axis")
    with col2: client_dob = st.date_input("Date of Birth", value=None, help="Required for SBI/ICICI")
    with col3: client_pan = st.text_input("PAN Number", help="Required for HDFC/Axis")
    with col4: custom_pwd = st.text_input("Or exact Password/CRN", type="password")
    
    if st.button("🚀 Process & Extract Data", use_container_width=True):
        with st.spinner("Decoding Document & Extracting Data... please wait"):
            
            passwords_to_try = generate_bank_passwords(client_name, client_dob, client_pan, custom_pwd)
            
            if uploaded_file.name.endswith('.pdf'): 
                raw_data, status = process_mathematical_parser(uploaded_file, passwords_to_try)
            else: 
                raw_data, status = process_excel_parser(uploaded_file)
            
            if raw_data is not None:
                if len(raw_data) > 0:
                    df = pd.DataFrame(raw_data)
                    df_tally_ready = df[['Date', 'Narration', 'Debit', 'Credit', 'Balance']]
                    st.session_state['raw_extracted_data'] = df_tally_ready.copy()
                else:
                    st.error("❌ Error: Document unlocked, but no transactions found. Format might be unreadable or a scanned photo.")
            else:
                st.error(f"❌ Error: {status}")

# ==========================================
# 6. UI: DATE FILTER & DASHBOARD
# ==========================================
if st.session_state.get('raw_extracted_data') is not None:
    full_df = st.session_state['raw_extracted_data'].copy()
    
    st.write("---")
    st.markdown("### 📅 Select Specific Dates for Tally")
    
    full_df['Date_Obj'] = pd.to_datetime(full_df['Date'], errors='coerce', dayfirst=True)
    valid_dates = full_df.dropna(subset=['Date_Obj'])
    
    if not valid_dates.empty:
        min_date = valid_dates['Date_Obj'].min().date()
        max_date = valid_dates['Date_Obj'].max().date()
    else:
        min_date = datetime.date(2023, 4, 1)
        max_date = datetime.date.today()
        
    c1, c2 = st.columns(2)
    with c1: from_date = st.date_input("From Date:", value=min_date)
    with c2: to_date = st.date_input("To Date:", value=max_date)
    
    mask = (full_df['Date_Obj'].dt.date >= from_date) & (full_df['Date_Obj'].dt.date <= to_date)
    filtered_df = full_df.loc[mask].copy()
    
    if filtered_df.empty:
        st.warning("⚠️ Warning: No transactions found for these dates. Showing all data.")
        filtered_df = full_df.copy()
        
    filtered_df = filtered_df.drop(columns=['Date_Obj'], errors='ignore')
    
    meta_filtered = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0, "total_debit_amt": 0.0, "total_credit_amt": 0.0}
    if not filtered_df.empty:
        meta_filtered["opening_bal"] = filtered_df.iloc[0]['Balance'] - filtered_df.iloc[0]['Credit'] + filtered_df.iloc[0]['Debit']
        meta_filtered["closing_bal"] = filtered_df.iloc[-1]['Balance']
        meta_filtered["debit_count"] = (filtered_df['Debit'] > 0).sum()
        meta_filtered["credit_count"] = (filtered_df['Credit'] > 0).sum()
        meta_filtered["total_debit_amt"] = filtered_df['Debit'].sum()
        meta_filtered["total_credit_amt"] = filtered_df['Credit'].sum()
    
    st.session_state['cleaned_data'] = filtered_df.copy()
    
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
