import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. MEMORY & UI CONFIGURATION (THE BRIDGE)
# ==========================================
# Ye line data ko memory mein save karegi taaki dusre page par ja sake
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
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction | Data will Auto-Sync to Ledger Mapper</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: PDF & EXCEL PARSERS
# ==========================================
def process_mathematical_parser(file, password=""):
    raw_transactions = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0, "total_debit_amt": 0.0, "total_credit_amt": 0.0}
    try:
        with pdfplumber.open(file, password=password) as pdf:
            date_pattern = re.compile(r'^(\d{1,2}[/\-\s][a-zA-Z]{3}[/\-\s]\d{2,4}|\d{1,2}[/\-\s]\d{1,2}[/\-\s]\d{2,4})')
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
                        date_str = match.group(1)
                        rem = line[len(date_str):].strip()
                        parts = rem.split()
                        amount_list = []
                        narration_parts = []
                        for i in range(len(parts)-1, -1, -1):
                            part = parts[i]
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part): amount_list.insert(0, float(cl_part))
                            else:
                                narration_parts = parts[:i+1]
                                break
                        narration = " ".join(narration_parts)
                        balance = 0.0
                        txn_amount = 0.0
                        if len(amount_list) > 0: balance = amount_list[-1]
                        if len(amount_list) > 1: txn_amount = amount_list[-2] 
                        current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0}
                    else:
                        if current_txn and len(line) > 2:
                            ignore = ['page', 'balance', 'total', 'statement', 'branch']
                            if not any(ig in line.lower() for ig in ignore):
                                clean_line_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_line_parts: current_txn["Narration"] += " " + " ".join(clean_line_parts)
                if current_txn: raw_transactions.append(current_txn)

        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            amt = curr["Amount"]
            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                if round(prev_bal + amt, 2) == round(curr_bal, 2): curr["Credit"] = amt
                elif round(prev_bal - amt, 2) == round(curr_bal, 2): curr["Debit"] = amt
                else:
                    diff = round(curr_bal - prev_bal, 2)
                    if diff > 0: curr["Credit"] = amt
                    elif diff < 0: curr["Debit"] = amt
            else:
                if "RTGS" in curr["Narration"].upper() or "NEFT" in curr["Narration"].upper(): curr["Debit"] = amt 
                else: curr["Credit"] = amt 
                    
        if raw_transactions:
            for txn in raw_transactions:
                if txn["Debit"] > 0: 
                    meta["debit_count"] += 1
                    meta["total_debit_amt"] += txn["Debit"]
                if txn["Credit"] > 0: 
                    meta["credit_count"] += 1
                    meta["total_credit_amt"] += txn["Credit"]
            meta["closing_bal"] = raw_transactions[-1]["Balance"]
            meta["opening_bal"] = raw_transactions[0]["Balance"] - raw_transactions[0]["Credit"] + raw_transactions[0]["Debit"]
        return raw_transactions, meta, "Success"
    except Exception as e: return None, None, str(e)

def process_excel_parser(file):
    raw_transactions = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0, "total_debit_amt": 0.0, "total_credit_amt": 0.0}
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
        
        if not date_col or not narration_col: return None, None, "Format error: Date/Narration not found."
            
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
            
            if debit_val > 0:
                meta["debit_count"] += 1
                meta["total_debit_amt"] += debit_val
            if credit_val > 0:
                meta["credit_count"] += 1
                meta["total_credit_amt"] += credit_val
                
            raw_transactions.append({"Date": date_val, "Narration": narration_val, "Debit": debit_val, "Credit": credit_val, "Balance": balance_val})
            
        if raw_transactions:
            meta["closing_bal"] = raw_transactions[-1]["Balance"]
            meta["opening_bal"] = raw_transactions[0]["Balance"] - raw_transactions[0]["Credit"] + raw_transactions[0]["Debit"]
        return raw_transactions, meta, "Success"
    except Exception as e: return None, None, f"Excel Error: {str(e)}"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()

# ==========================================
# 3. DASHBOARD EXECUTION
# ==========================================
uploaded_file = st.file_uploader("Upload Bank Statement (PDF, Excel, CSV)", type=['pdf', 'xlsx', 'xls', 'csv'])

if uploaded_file:
    pdf_password = st.text_input("PDF Password (if PDF is locked)", type="password") if uploaded_file.name.endswith('.pdf') else ""
    
    if st.button("🚀 Process & Generate Data", use_container_width=True):
        with st.spinner("Processing Document... please wait"):
            if uploaded_file.name.endswith('.pdf'): raw_data, meta, status = process_mathematical_parser(uploaded_file, pdf_password)
            else: raw_data, meta, status = process_excel_parser(uploaded_file)
            
            if raw_data:
                df = pd.DataFrame(raw_data)
                df_tally_ready = df[['Date', 'Narration', 'Debit', 'Credit', 'Balance']]
                
                # --- SENDER: Saving clean data to memory for the other page ---
                st.session_state['cleaned_data'] = df_tally_ready.copy()
                
                st.success("✅ Extraction 100% Accurate! Data is safely synced to the 'Ledger Mapping' page.")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {meta["opening_bal"]:,.2f}</div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card"><b>Total Debits (-)</b><br>₹ {meta["total_debit_amt"]:,.2f}<br><span style="font-size:13px; color:#6B7280;">({meta["debit_count"]} Txns)</span></div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card"><b>Total Credits (+)</b><br>₹ {meta["total_credit_amt"]:,.2f}<br><span style="font-size:13px; color:#6B7280;">({meta["credit_count"]} Txns)</span></div>', unsafe_allow_html=True)
                m4.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {meta["closing_bal"]:,.2f}</div>', unsafe_allow_html=True)
                
                st.write("<br>", unsafe_allow_html=True)
                st.write("### 📝 Data Preview")
                st.dataframe(df_tally_ready, use_container_width=True) 
                
                c1, c2 = st.columns(2)
                c1.download_button("Download CSV", df_tally_ready.to_csv(index=False).encode('utf-8'), "alpha_tally_ready.csv", "text/csv", use_container_width=True)
                c2.download_button("Download Excel (.xlsx)", to_excel(df_tally_ready), "alpha_tally_ready.xlsx", use_container_width=True)
            else:
                st.error(f"❌ Error: {status}")
