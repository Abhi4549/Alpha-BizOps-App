import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

# ==========================================
# 1. UI CONFIGURATION
# ==========================================
if 'raw_data' not in st.session_state:
    st.session_state['raw_data'] = None

st.set_page_config(page_title="Alpha Hub", layout="wide")

css1 = ".hero-title { font-size: 38px; font-weight: 800; }"
css2 = ".hero-title { color: #1E3A8A; text-align: center; }"
css3 = ".metric-card { background: #F3F4F6; padding: 15px; }"
css4 = ".metric-card { border-radius: 8px; text-align: center; }"
st.markdown(f"<style>{css1} {css2} {css3} {css4}</style>", unsafe_allow_html=True)

t1 = '<div class="hero-title">🏦 BANK TO TALLY</div>'
st.markdown(t1, unsafe_allow_html=True)

# ==========================================
# 2. PASSWORD ENGINE
# ==========================================
def get_pwds(name, dob, pan, cust_pwd):
    pwds = []
    if cust_pwd: 
        pwds.append(cust_pwd.strip())
    if dob:
        d = dob.strftime("%d")
        m = dob.strftime("%m")
        y_f = dob.strftime("%Y")
        y_s = dob.strftime("%y")
        pwds.extend([f"{d}{m}{y_f}", f"{d}{m}{y_s}"])
        if name:
            n_cln = re.sub(r'[^a-zA-Z]', '', name)
            if len(n_cln) >= 4:
                f4l = n_cln[:4].lower()
                f4u = n_cln[:4].upper()
                pwds.extend([f"{f4l}{d}{m}", f"{f4u}{d}{m}"])
                pwds.append(f"{f4l}{d}{m}{y_f}")
    if pan:
        pwds.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(pwds))

# ==========================================
# 3. PDF PARSER (Maa Baap Logic)
# ==========================================
def parse_pdf(file, pwd_list):
    txns = []
    file.seek(0)
    pdf_bytes = file.read()
    match_pwd = '' 
    
    try:
        temp_mem = io.BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(temp_mem)
        if reader.is_encrypted:
            unlocked = False
            for p in pwd_list:
                if not p: continue
                try:
                    if reader.decrypt(p): 
                        unlocked = True
                        match_pwd = p
                        break
                except Exception:
                    continue
            if not unlocked:
                return None, "PDF is locked. Password failed."
    except Exception as e:
        return None, f"Decrypt Error: {str(e)}"

    try:
        pdf_mem = io.BytesIO(pdf_bytes)
        with pdfplumber.open(pdf_mem, password=match_pwd) as pdf:
            dt_reg = r'^\s*(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})'
            dt_pat = re.compile(dt_reg)

            ig_kws = ['opening balance', 'closing balance', 'page total']
            ig_kws += ['brought forward', 'carried forward', 'summary of']
            ig_kws += ['total debits', 'total credits', 'generated on']

            curr_txn = None
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if not text: text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line: continue

                    match = dt_pat.search(line)
                    if match:
                        if curr_txn: txns.append(curr_txn)

                        d_str = re.sub(r'[\s\.\-]', '/', match.group(1))
                        d_str = re.sub(r'/+', '/', d_str)
                        
                        rem = line[len(match.group(0)):].strip()
                        parts = rem.split()
                        
                        nums = []
                        narr_w = []

                        # RIGHT TO LEFT FIX
                        for pt in reversed(parts):
                            cp = pt.replace(',', '').replace('Cr', '')
                            cp = cp.replace('Dr', '').replace('cr', '')
                            cp = cp.replace('dr', '').strip()
                            
                            num_reg = r'^-?\d+(\.\d+)?$'
                            if re.match(num_reg, cp) and len(nums) < 3:
                                if cp.startswith('0') and '.' not in cp and len(cp) >= 4:
                                    narr_w.insert(0, pt)
                                else:
                                    nums.insert(0, float(cp))
                            else:
                                narr_w.insert(0, pt)

                        l_low = line.lower()
                        if len(nums) >= 1 and not any(k in l_low for k in ig_kws):
                            narr = " ".join(narr_w)
                            bal = nums[-1]
                            amt = nums[-2] if len(nums) >= 2 else 0.0

                            curr_txn = {
                                "Date": d_str, 
                                "Narration": narr, 
                                "Amount": amt, 
                                "Balance": bal, 
                                "Debit": 0.0, 
                                "Credit": 0.0
                            }
                    else:
                        if curr_txn and len(line) > 2:
                            chk = ['page', 'balance', 'total', 'opening']
                            if not any(k in line.lower() for k in chk):
                                num_reg2 = r'^-?\d+(\.\d+)?$'
                                c_pts = [p for p in line.split() if not re.match(num_reg2, p.replace(',',''))]
                                if c_pts: 
                                    curr_txn["Narration"] += " " + " ".join(c_pts)

                if curr_txn: txns.append(curr_txn)

        if not txns:
            return None, "No transactions found."

        # MATH & DOUBLE ENTRY FIX
        final_ledger = []
        seen = set()
        txn_kws = ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "DR"]

        for curr in txns:
            fg = f"{curr['Date']}_{curr['Balance']}_{curr['Amount']}"
            if fg in seen: continue
            seen.add(fg)

            if len(final_ledger) > 0:
                prev_b = final_ledger[-1]["Balance"]
                curr_b = curr["Balance"]
                diff = round(curr_b - prev_b, 2)
                
                amt_val = curr["Amount"]
                
                if diff > 0:
                    curr["Credit"] = amt_val if amt_val > 0 else abs(diff)
                    curr["Debit"] = 0.0
                elif diff < 0:
                    curr["Debit"] = amt_val if amt_val > 0 else abs(diff)
                    curr["Credit"] = 0.0
                else:
                    curr["Credit"] = amt_val if amt_val > 0 else 0.0
                    curr["Debit"] = 0.0
            else:
                n_up = curr["Narration"].upper()
                if any(k in n_up for k in txn_kws):
                    curr["Debit"] = curr["Amount"]
                    curr["Credit"] = 0.0
                else:
                    curr["Credit"] = curr["Amount"]
                    curr["Debit"] = 0.0
                    
            final_ledger.append(curr)

        return final_ledger, "Success"
    except Exception as e: 
        return None, f"Parser Error: {str(e)}"

# ==========================================
# 4. EXCEL PARSER
# ==========================================
def parse_excel(file):
    try:
        if file.name.endswith('.csv'): 
            df = pd.read_csv(file, skip_blank_lines=True)
        else: 
            df = pd.read_excel(file)
            
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df = df.reset_index(drop=True)
        
        h_idx = -1
        for i in range(min(20, len(df))):
            r_str = ' '.join(str(x).lower() for x in df.iloc[i].values)
            if 'date' in r_str and ('narration' in rstr or 'particulars' in rstr):
                h_idx = i
                break
                
        if h_idx != -1:
            df.columns = df.iloc[h_idx]
            df = df.iloc[h_idx+1:].reset_index(drop=True)
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        cols = df.columns
        
        d_col = next((c for c in cols if 'date' in c), None)
        
        n_kws = ['narration', 'particulars', 'description']
        n_col = next((c for c in cols if any(x in c for x in n_kws)), None)
        
        dr_kws = ['debit', 'withdrawal', 'dr']
        dr_col = next((c for c in cols if any(x in c for x in dr_kws)), None)
        
        cr_kws = ['credit', 'deposit', 'cr']
        cr_col = next((c for c in cols if any(x in c for x in cr_kws)), None)
        
        bal_col = next((c for c in cols if 'balance' in c), None)
        
        if not d_col or not n_col: 
            return None, "Format error: Columns missing."
            
        raw_txns = []
        for _, row in df.iterrows():
            rd = row[d_col]
            if pd.isna(rd) or str(rd).strip().lower() == 'nan': 
                continue
            
            if isinstance(rd, pd.Timestamp):
                d_val = rd.strftime('%d/%m/%Y')
            else:
                d_val = str(rd).split(' ')[0]
                
            n_val = str(row[n_col]).strip()
            if n_val.lower() == 'nan': n_val = ""
            
            def cln(v):
                try: 
                    cs = str(v).replace(',', '').replace('Cr', '')
                    cs = cs.replace('Dr', '').replace('cr', '')
                    return float(cs.replace('dr', '').strip())
                except: return 0.0
                    
            dr_v = cln(row[dr_col]) if dr_col else 0.0
            cr_v = cln(row[cr_col]) if cr_col else 0.0
            b_v = cln(row[bal_col]) if bal_col else 0.0
                
            raw_txns.append({
                "Date": d_val, "Narration": n_val, 
                "Debit": dr_v, "Credit": cr_v, "Balance": b_v
            })
            
        return raw_txns, "Success"
    except Exception as e: 
        return None, f"Excel Error: {str(e)}"

def make_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='TallyData')
    return out.getvalue()

# ==========================================
# 5. UI BLOCK
# ==========================================
file_up = st.file_uploader("Upload Statement", type=['pdf', 'xlsx', 'csv'])

if file_up:
    st.markdown("### 🔐 Smart Unlock")
    c1, c2, c3, c4 = st.columns(4)
    with c1: c_name = st.text_input("Name")
    with c2: c_dob = st.date_input("DOB", value=None)
    with c3: c_pan = st.text_input("PAN")
    with c4: c_pwd = st.text_input("Password", type="password")
    
    if st.button("🚀 Extract Data", use_container_width=True):
        with st.spinner("Processing..."):
            
            pwds = get_pwds(c_name, c_dob, c_pan, c_pwd)
            
            # SHORT LINES FIX FOR SYNTAX ERROR
            is_pdf = file_up.name.endswith('.pdf')
            if is_pdf:
                res = parse_pdf(file_up, pwds)
            else:
                res = parse_excel(file_up)
                
            data = res[0]
            stat = res[1]
            
            if data is not None:
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    st.session_state['raw_data'] = df.copy()
                else:
                    st.error("❌ No transactions found.")
            else:
                st.error(f"❌ Error: {stat}")

# ==========================================
# 6. DASHBOARD
# ==========================================
if st.session_state.get('raw_data') is not None:
    f_df = st.session_state['raw_data'].copy()
    
    st.write("---")
    st.markdown("### 📅 Select Dates")
    
    f_df['D_Obj'] = pd.to_datetime(f_df['Date'], errors='coerce', dayfirst=True)
    v_dates = f_df.dropna(subset=['D_Obj'])
    
    if not v_dates.empty:
        min_d = v_dates['D_Obj'].min().date()
        max_d = v_dates['D_Obj'].max().date()
    else:
        min_d = datetime.date(2023, 4, 1)
        max_d = datetime.date.today()
        
    c1, c2 = st.columns(2)
    with c1: dt_from = st.date_input("From:", value=min_d)
    with c2: dt_to = st.date_input("To:", value=max_d)
    
    mask = (f_df['D_Obj'].dt.date >= dt_from) & (f_df['D_Obj'].dt.date <= dt_to)
    flt_df = f_df.loc[mask].copy()
    
    if flt_df.empty:
        st.warning("⚠️ No data for these dates.")
        flt_df = f_df.copy()
        
    flt_df = flt_df.drop(columns=['D_Obj'], errors='ignore')
    
    if not flt_df.empty:
        op_bal = flt_df.iloc[0]['Balance'] - flt_df.iloc[0]['Credit'] + flt_df.iloc[0]['Debit']
        cl_bal = flt_df.iloc[-1]['Balance']
        dr_c = (flt_df['Debit'] > 0).sum()
        cr_c = (flt_df['Credit'] > 0).sum()
        dr_amt = flt_df['Debit'].sum()
        cr_amt = flt_df['Credit'].sum()
    else:
        op_bal=cl_bal=dr_c=cr_c=dr_amt=cr_amt=0.0
    
    st.success("✅ Data Extracted Successfully.")
    
    m1, m2, m3, m4 = st.columns(4)
    h1 = f'<div class="metric-card"><b>Open</b><br>₹ {op_bal:,.2f}</div>'
    h2 = f'<div class="metric-card"><b>Debit</b><br>₹ {dr_amt:,.2f}</div>'
    h3 = f'<div class="metric-card"><b>Credit</b><br>₹ {cr_amt:,.2f}</div>'
    h4 = f'<div class="metric-card"><b>Close</b><br>₹ {cl_bal:,.2f}</div>'
    
    m1.markdown(h1, unsafe_allow_html=True)
    m2.markdown(h2, unsafe_allow_html=True)
    m3.markdown(h3, unsafe_allow_html=True)
    m4.markdown(h4, unsafe_allow_html=True)
    
    st.dataframe(flt_df, use_container_width=True) 
    
    d1, d2 = st.columns(2)
    csv_str = flt_df.to_csv(index=False).encode('utf-8')
    d1.download_button("Download CSV", csv_str, "tally.csv", "text/csv", use_container_width=True)
    xl_str = make_excel(flt_df)
    d2
