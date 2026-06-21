import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime
import requests
import json

# ==========================================
# 1. MEMORY & UI CONFIGURATION
# ==========================================
if 'raw_extracted_data' not in st.session_state:
    st.session_state['raw_extracted_data'] = None
if 'cleaned_data' not in st.session_state:
    st.session_state['cleaned_data'] = None

st.set_page_config(page_title="Alpha BizOps Hub v2", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 SMART BANK STATEMENT TO TALLY EXCEL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Hybrid Math Engine + AI Debit/Credit Assistant | Auto-Unlock Production Grade</div>', unsafe_allow_html=True)

# ==========================================
# 2. FREE AI ASSISTANT ENGINE (GEMINI FREE TIER)
# ==========================================
def ask_gemini_assistant(narration, amount, api_key):
    """
    Uses Gemini API to analyze transaction narration when math validation is ambiguous.
    Returns 'Debit', 'Credit', or 'Unknown' along with a suggested Tally Ledger Group.
    """
    if not api_key:
        return "Unknown", "Suspense Account"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    You are an expert Indian Chartered Accountant AI. Analyze this bank statement transaction narration and amount.
    Determine if this is a DEBIT (Money Out / Expense / Asset Purchase) or CREDIT (Money In / Income / Capital).
    Also suggest a standard Tally Ledger Group (e.g., Indirect Expenses, Sundry Debtors, Sundry Creditors, Bank Accounts, Income).
    
    Transaction Narration: "{narration}"
    Amount: {amount}
    
    Respond ONLY with a valid JSON object matching this schema exactly, do not include markdown formatting or blocks:
    {{"type": "Debit" or "Credit", "ledger": "Suggested Ledger Group Name"}}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            res_json = response.json()
            text_response = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean up potential markdown code block wrappers
            text_response = re.sub(r'```json|```', '', text_response).strip()
            
            data = json.loads(text_response)
            return data.get("type", "Unknown"), data.get("ledger", "Suspense Account")
    except Exception:
        pass
    return "Unknown", "Suspense Account"

# ==========================================
# 3. SMART PASSWORD ENGINE (INDIAN BANKS)
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
# 4. BACKEND: HYBRID MATHEMATICAL & AI PARSER
# ==========================================
def process_hybrid_parser(file, password_list, api_key):
    raw_transactions = []
    pdf_bytes = file.read()
    file.seek(0)
    
    unlocked_pdf_stream = None
    
    # ⚡ ENGINE 1: SECURITY BYPASS (FOR LOCKED & UNLOCKED)
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if not pwd: continue
                try:
                    if pdf_reader.decrypt(pwd): 
                        unlocked = True
                        break
                except Exception: continue
            
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

    # ⚡ ENGINE 2: ACCURATE EXTRACTION MATRIX
    try:
        with pdfplumber.open(unlocked_pdf_stream) as pdf:
            date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]+(?:\d{1,2}|[a-zA-Z]{3,10})[\s/\-\.]+\d{2,4})')

            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                cleaned_lines = []
                for l in lines:
                    l = l.strip()
                    if l and (not cleaned_lines or l != cleaned_lines[-1]):
                        cleaned_lines.append(l)

                current_txn = None

                for line in cleaned_lines:
                    match = date_pattern.search(line)
                    if match:
                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        date_str = re.sub(r'/+', '/', date_str)
                        
                        rem = line[match.end():].strip()
                        
                        force_dr = False
                        force_cr = False
                        if any(x in rem.upper() for x in ["DR", "WITHDRAWAL", "DEBIT", "DEBITED"]): force_dr = True
                        if any(x in rem.upper() for x in ["CR", "DEPOSIT", "CREDIT", "CREDITED"]): force_cr = True
                        
                        parts = rem.split()
                        numbers = []
                        
                        for part in reversed(parts):
                            clean_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', clean_part):
                                numbers.append(float(clean_part))
                            else: break 
                        numbers.reverse()

                        if numbers:
                            narration = " ".join(parts[:-len(numbers)])
                            balance = numbers[-1]
                            
                            if current_txn: raw_transactions.append(current_txn)

                            if len(numbers) == 2:
                                current_txn = {
                                    "Date": date_str, "Narration": narration, "Amount": numbers[0], 
                                    "Balance": balance, "Debit": 0.0, "Credit": 0.0, 
                                    "Force_Dr": force_dr, "Force_Cr": force_cr, "Needs_Calc": True, "AI_Ledger": "Pending"
                                }
                            elif len(numbers) >= 3:
                                cr_val = numbers[-2]
                                dr_val = numbers[-3]
                                current_txn = {
                                    "Date": date_str, "Narration": narration, "Amount": max(dr_val, cr_val), 
                                    "Balance": balance, "Debit": dr_val, "Credit": cr_val, 
                                    "Force_Dr": force_dr, "Force_Cr": force_cr, "Needs_Calc": False, "AI_Ledger": "Pending"
                                }
                            else:
                                current_txn = {
                                    "Date": date_str, "Narration": narration, "Amount": 0.0, 
                                    "Balance": balance, "Debit": 0.0, "Credit": 0.0, 
                                    "Force_Dr": force_dr, "Force_Cr": force_cr, "Needs_Calc": True, "AI_Ledger": "Pending"
                                }
                        else:
                            if current_txn: current_txn["Narration"] += " " + " ".join(parts)
                    else:
                        if current_txn and len(line) > 2:
                            ignore_words = ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing', 'brought forward', 'c/f', 'b/f']
                            if not any(ig in line.lower() for ig in ignore_words):
                                current_txn["Narration"] += " " + line

                if current_txn: raw_transactions.append(current_txn)

        if not raw_transactions:
            return None, "Document processed, but no valid transaction structures found."

        # ⚡ ENGINE 3: ANCHORING, MATHEMATICAL SYNC & AI ASSISTANT ROUTING
        filtered_txns = []
        opening_anchor = None
        
        for txn in raw_transactions:
            narr_lower = txn["Narration"].lower()
            if any(kw in narr_lower for kw in ["opening balance", "brought forward", "b/f", "bal b/f", "opening bal", "initial balance"]):
                opening_anchor = txn["Balance"]
                continue
            if any(kw in narr_lower for kw in ["particulars", "description", "statement of account"]) or (txn.get("Amount", 0) == 0.0 and txn["Balance"] == 0.0):
                continue
                
            if filtered_txns:
                prev = filtered_txns[-1]
                if txn["Date"] == prev["Date"] and txn["Balance"] == prev["Balance"] and txn["Narration"] == prev["Narration"]:
                    continue
                    
            filtered_txns.append(txn)
            
        raw_transactions = filtered_txns

        # Dynamic Routing Loop
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            prev_bal = raw_transactions[i-1]["Balance"] if i > 0 else opening_anchor

            if prev_bal is not None:
                diff = round(curr["Balance"] - prev_bal, 2)
                if diff > 0:
                    curr["Credit"] = diff
                    curr["Debit"] = 0.0
                elif diff < 0:
                    curr["Debit"] = abs(diff)
                    curr["Credit"] = 0.0
                else:
                    # Math delta is zero, let's invoke AI Assistant for routing text triggers safely
                    if curr.get("Force_Dr"):
                        curr["Debit"] = curr.get("Amount", 0.0)
                    elif curr.get("Force_Cr"):
                        curr["Credit"] = curr.get("Amount", 0.0)
                    else:
                        # Call free Gemini AI engine to cross-verify intent
                        ai_type, ai_ledg = ask_gemini_assistant(curr["Narration"], curr.get("Amount", 0.0), api_key)
                        curr["AI_Ledger"] = ai_ledg
                        if ai_type == "Debit":
                            curr["Debit"] = curr.get("Amount", 0.0)
                        elif ai_type == "Credit":
                            curr["Credit"] = curr.get("Amount", 0.0)
                        else:
                            if curr.get("Needs_Calc"): curr["Credit"] = curr.get("Amount", 0.0)
            else:
                # Missing opening balance fallback using Smart AI parsing
                ai_type, ai_ledg = ask_gemini_assistant(curr["Narration"], curr.get("Amount", 0.0), api_key)
                curr["AI_Ledger"] = ai_ledg
                if ai_type == "Debit":
                    curr["Debit"] = curr.get("Amount", 0.0)
                elif ai_type == "Credit":
                    curr["Credit"] = curr.get("Amount", 0.0)
                else:
                    if curr.get("Force_Dr") or any(kw in curr["Narration"].upper() for kw in ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]):
                        curr["Debit"] = curr.get("Amount", 0.0)
                    else:
                        curr["Credit"] = curr.get("Amount", 0.0)
            
            # Clean flags
            curr.pop("Needs_Calc", None)
            curr.pop("Amount", None)
            curr.pop("Force_Dr", None)
            curr.pop("Force_Cr", None)

        return raw_transactions, "Success"
    except Exception as e: return None, f"Parsing Error: {str(e)}"

# ==========================================
# 5. EXCEL / CSV FALLBACK PARSER
# ==========================================
def process_excel_parser(file):
    raw_transactions = []
    try:
        df = pd.read_csv(file, skip_blank_lines=True) if file.name.endswith('.csv') else pd.read_excel(file)
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df = df.reset_index(drop=True)
        
        header_idx = -1
        for i in range(min(20, len(df))):
            row_str = ' '.join(str(x).lower() for x in df.iloc[i].values)
            if 'date' in row_str and any(k in row_str for k in ['narration', 'particulars', 'description']):
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
        
        if not date_col or not narration_col: return None, "Format error: Date/Narration column missing."
            
        for _, row in df.iterrows():
            raw_date = row[date_col]
            if pd.isna(raw_date) or str(raw_date).strip().lower() == 'nan': continue
            date_val = raw_date.strftime('%d/%m/%Y') if isinstance(raw_date, pd.Timestamp) else str(raw_date).split(' ')[0]
            narration_val = str(row[narration_col]).strip()
            if narration_val.lower() == 'nan': narration_val = ""
            
            def clean_val(v):
                try: return float(str(v).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip())
                except: return 0.0
                    
            raw_transactions.append({
                "Date": date_val, "Narration": narration_val, 
                "Debit": clean_val(row[debit_col]) if debit_col else 0.0, 
                "Credit": clean_val(row[credit_col]) if credit_col else 0.0, 
                "Balance": clean_val(row[balance_col]) if balance_col else 0.0,
                "AI_Ledger": "Auto-Detected"
            })
            
        return raw_transactions, "Success"
    except Exception as e: return None, f"Excel Error: {str(e)}"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyReadyData')
    return output.getvalue()

# ==========================================
# 6. UI: CONFIGURATION & CONFIG MATRIX
# ==========================================
st.sidebar.markdown("### 🔑 AI Core Configuration")
gemini_api_key = st.sidebar.text_input("Gemini API Key (Free Tier)", type="password", help="Enter free Gemini API Key to enable AI ledger mapping & smart debit/credit assignment.")
if not gemini_api_key:
    st.sidebar.warning("⚠️ AI Assistant is offline. Enter an API key to auto-detect Ledgers & fix complex routing.")

uploaded_file = st.file_uploader("Upload Bank Statement (Locked/Unlocked PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])

if uploaded_file:
    st.markdown("### 🔐 Security & Auto-Unlock Suite")
    st.info("Statement locked ho ya unlocked, system use internally bypass karega. Agar profile matching passwords chahiye toh niche details bharein:")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: client_name = st.text_input("First Name (e.g. Rahul)", help="For ICICI/Axis formats")
    with col2: client_dob = st.date_input("Date of Birth", value=None, help="For SBI/ICICI patterns")
    with col3: client_pan = st.text_input("PAN Number", help="For HDFC statements")
    with col4: custom_pwd = st.text_input("Exact Password (If known)", type="password")
    
    if st.button("🚀 Process Engine with Hybrid Verification", use_container_width=True):
        with st.spinner("Executing extraction matrix & running AI checks..."):
            pwds = generate_bank_passwords(client_name, client_dob, client_pan, custom_pwd)
            
            if uploaded_file.name.endswith('.pdf'):
                raw_data, status = process_hybrid_parser(uploaded_file, pwds, gemini_api_key)
            else:
                raw_data, status = process_excel_parser(uploaded_file)
            
            if raw_data is not None and len(raw_data) > 0:
                df_tally = pd.DataFrame(raw_data)[['Date', 'Narration', 'Debit', 'Credit', 'Balance', 'AI_Ledger']]
                st.session_state['raw_extracted_data'] = df_tally.copy()
                st.success("🎉 Statement successfully processed!")
            else:
                st.error(f"❌ Error: {status if raw_data is None else 'No transactions found.'}")

# ==========================================
# 7. UI: DASHBOARD & EXPORT (TALLY READY)
# ==========================================
if st.session_state.get('raw_extracted_data') is not None:
    full_df = st.session_state['raw_extracted_data'].copy()
    
    st.write("---")
    st.markdown("### 📅 Select Dates for Tally Sync")
    
    full_df['Date_Obj'] = pd.to_datetime(full_df['Date'], errors='coerce', dayfirst=True)
    valid_dates = full_df.dropna(subset=['Date_Obj'])
    
    min_date = valid_dates['Date_Obj'].min().date() if not valid_dates.empty else datetime.date(2023, 4, 1)
    max_date = valid_dates['Date_Obj'].max().date() if not valid_dates.empty else datetime.date.today()
        
    c1, c2 = st.columns(2)
    with c1: from_date = st.date_input("From Date:", value=min_date)
    with c2: to_date = st.date_input("To Date:", value=max_date)
    
    filtered_df = full_df.loc[(full_df['Date_Obj'].dt.date >= from_date) & (full_df['Date_Obj'].dt.date <= to_date)].copy()
    
    if filtered_df.empty:
        st.warning("⚠️ No transactions in this range. Showing all.")
        filtered_df = full_df.copy()
        
    filtered_df = filtered_df.drop(columns=['Date_Obj'], errors='ignore')
    st.session_state['cleaned_data'] = filtered_df.copy()
    
    if not filtered_df.empty:
        op_bal = filtered_df.iloc[0]['Balance'] - filtered_df.iloc[0]['Credit'] + filtered_df.iloc[0]['Debit']
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {op_bal:,.2f}</div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><b>Total Debits (-)</b><br>₹ {filtered_df["Debit"].sum():,.2f} <span style="font-size:12px; color:#6B7280;">({(filtered_df["Debit"] > 0).sum()})</span></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><b>Total Credits (+)</b><br>₹ {filtered_df["Credit"].sum():,.2f} <span style="font-size:12px; color:#6B7280;">({(filtered_df["Credit"] > 0).sum()})</span></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {filtered_df.iloc[-1]["Balance"]:,.2f}</div>', unsafe_allow_html=True)
    
    st.write("<br>### 📝 Tally-Ready Data Preview (With AI Enrichment)", unsafe_allow_html=True)
    st.dataframe(filtered_df, use_container_width=True) 
    
    colA, colB = st.columns(2)
    colA.download_button("Download CSV", filtered_df.to_csv(index=False).encode('utf-8'), "tally_ready.csv", "text/csv", use_container_width=True)
    colB.download_button("Download Excel (.xlsx)", to_excel(filtered_df), "tally_ready.xlsx", use_container_width=True)
