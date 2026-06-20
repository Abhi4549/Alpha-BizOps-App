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
    match_pwd = None 
    
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
        # Pass None if no password is required for Unlocked PDFs
        with pdfplumber.open(pdf_mem, password=match_pwd) as pdf:
            # ⚡ FIX: Removed ^\s* so it catches dates ANYWHERE in the line
            dt_reg = r'(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})'
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
    out = io
