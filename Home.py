import streamlit as st
import pandas as pd
import pdfplumber
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

css1 = ".hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}"
css2 = ".hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}"
css3 = ".metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }"
st.markdown(f"<style>{css1} {css2} {css3}</style>", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK STATEMENT TO TALLY EXCEL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Smart Auto-Unlock | Universal Format</div>', unsafe_allow_html=True)

# ==========================================
# 2. SMART PASSWORD ENGINE
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
                f4l = name_clean[:4].lower()
                f4u = name_clean[:4].upper()
                passwords.extend([f"{f4l}{d_str}{m_str}", f"{f4u}{d_str}{m_str}", f"{f4l}{d_str}{m_str}{y_full}"])
                
    if pan:
        passwords.extend([pan.lower().strip(), pan.upper().strip()])
        
    return list(set(passwords))

# ==========================================
# 3. BACKEND: PDF PARSER (Maa Baap Logic)
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    file.seek(0)
    pdf_bytes = file.read()
    
    matched_pwd = None
    is_locked = False
    
    # ⚡ ENGINE 1: NATIVE PDFPLUMBER UNLOCK (No Text Corruption)
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as test_pdf:
            pass
    except Exception:
        is_locked = True
        
    if is_locked:
        unlocked = False
        for pwd in password_list:
            if not pwd: continue
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes), password=pwd) as test_pdf:
                    pass
                unlocked = True
                matched_pwd = pwd
                break
            except Exception:
                continue
                
        if not unlocked:
            return None, "PDF is locked. Auto-Unlock failed. Please provide exact Password/PAN/DOB."

    # ⚡ ENGINE 2: EXACT ORIGINAL EXTRACTION LOGIC
    try:
        pdf_mem = io.BytesIO(pdf_bytes)
        with pdfplumber.open(pdf_mem, password=matched_pwd) as pdf:
            
            # Fix: ^\s* removed to capture dates ANYWHERE in the line
            dt_regex = r'(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})'
            date_pattern = re.compile(dt_regex)

            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                current_txn = None
                
                for line in lines:
                    line = line.strip()
                    if not line: continue

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

                        # YOUR ORIGINAL LOGIC
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

        # YOUR EXACT ORIGINAL MATH LOGIC
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
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
                narration_upper = curr["Narration"].upper()
                chk_kws = ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]
                if any(kw in narration_upper for kw in chk_kws):
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
