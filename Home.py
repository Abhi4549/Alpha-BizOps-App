import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import io
import re
import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
if 'raw_extracted_data' not in st.session_state:
    st.session_state['raw_extracted_data'] = None

st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; }
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK TO TALLY</div>', unsafe_allow_html=True)

# ==========================================
# 2. PASSWORD ENGINE
# ==========================================
def get_pwds(name, dob, pan, cust_pwd):
    pwds = []
    if cust_pwd: pwds.append(cust_pwd.strip())
    if dob:
        d, m, y_f = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y")
        y_s = dob.strftime("%y")
        pwds.extend([f"{d}{m}{y_f}", f"{d}{m}{y_s}"])
        if name:
            n = re.sub(r'[^a-zA-Z]', '', name)
            if len(n) >= 4:
                pwds.extend([f"{n[:4].lower()}{d}{m}", f"{n[:4].upper()}{d}{m}"])
    if pan:
        pwds.extend([pan.lower().strip(), pan.upper().strip()])
    return list(set(pwds))

# ==========================================
# 3. PDF PARSER (Accuracy Focused)
# ==========================================
def parse_pdf(file, pwds):
    raw_txns = []
    pdf_bytes = file.read()
    file.seek(0)
    
    match_pwd = None
    # Check if locked
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted:
            for p in pwds:
                if reader.decrypt(p):
                    match_pwd = p
                    break
            if not match_pwd: return None, "Password incorrect."
    except: pass

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes), password=match_pwd) as pdf:
            dt_reg = r'(\d{1,2}[\s/\-\.]{1,3}(?:[a-zA-Z]{3,10}|\d{1,2})[\s/\-\.]{1,3}\d{2,4})'
            dt_pat = re.compile(dt_reg)
            
            for page in pdf.pages:
                text = page.extract_text(layout=True) or page.extract_text()
                if not text: continue
                
                curr = None
                for line in text.split('\n'):
                    line = line.strip()
                    match = dt_pat.search(line)
                    if match:
                        if curr: raw_txns.append(curr)
                        
                        d_str = re.sub(r'[\s\.\-]', '/', match.group(1))
                        rem = line[match.end():].strip()
                        parts = rem.split()
                        
                        nums = []
                        narr = []
                        for pt in parts:
                            c = pt.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            if re.match(r'^-?\d+(\.\d+)?$', c):
                                if c.startswith('0') and '.' not in c and len(c) >= 4: narr.append(pt)
                                else: nums.append(float(c))
                            else: narr.append(pt)
                            
                        curr = {
                            "Date": d_str, "Narration": " ".join(narr),
                            "Amount": nums[-2] if len(nums)>=2 else 0.0,
                            "Balance": nums[-1] if nums else 0.0,
                            "Debit": 0.0, "Credit": 0.0
                        }
                    elif curr:
                        if not any(k in line.lower() for k in ['page', 'balance', 'total']):
                            curr["Narration"] += " " + line
                if curr: raw_txns.append(curr)

        # Math Logic
        for i, t in enumerate(raw_txns):
            if i > 0:
                diff = round(t["Balance"] - raw_txns[i-1]["Balance"], 2)
                if diff > 0: t["Credit"] = t["Amount"] if t["Amount"] > 0 else diff
                else: t["Debit"] = t["Amount"] if t["Amount"] > 0 else abs(diff)
            else:
                t["Credit"] = t["Amount"]
        return raw_txns, "Success"
    except Exception as e: return None, str(e)

# ==========================================
# 4. UI & EXECUTION
# ==========================================
file_up = st.file_uploader("Upload Statement", type=['pdf'])
if file_up:
    c1, c2, c3, c4 = st.columns(4)
    n = c1.text_input("Name")
    d = c2.date_input("DOB", value=None)
    p = c3.text_input("PAN")
    pw = c4.text_input("Password", type="password")
    
    if st.button("Extract"):
        data, stat = parse_pdf(file_up, get_pwds(n, d, p, pw))
        if data:
            st.session_state['raw_data'] = pd.DataFrame(data)
            st.success("Extracted!")
            st.dataframe(st.session_state['raw_data'])
        else: st.error(stat)
