import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# ==========================================
# 1. FRONTEND: UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="BANK PDF TO TALLY EXCEL", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 38px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .hero-subtitle { font-size: 16px; color: #4B5563; text-align: center; margin-bottom: 30px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🏦 BANK PDF TO TALLY EXCEL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">100% Accurate Data Extraction with Auto-Reconciliation & Dashboard</div>', unsafe_allow_html=True)

# ==========================================
# 2. BACKEND: 100% ACCURATE MATH PARSER
# ==========================================
def process_mathematical_parser(file, password=""):
    raw_transactions = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0}
    
    try:
        with pdfplumber.open(file, password=password) as pdf:
            # Date Pattern
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
                        if current_txn:
                            raw_transactions.append(current_txn)
                            
                        date_str = match.group(1)
                        rem = line[len(date_str):].strip()
                        parts = rem.split()
                        amount_list = []
                        narration_parts = []
                        
                        for i in range(len(parts)-1, -1, -1):
                            part = parts[i]
                            cl_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            
                            if re.match(r'^-?\d+(\.\d+)?$', cl_part):
                                amount_list.insert(0, float(cl_part))
                            else:
                                narration_parts = parts[:i+1]
                                break
                                
                        narration = " ".join(narration_parts)
                        balance = 0.0
                        txn_amount = 0.0
                        
                        if len(amount_list) > 0: balance = amount_list[-1]
                        if len(amount_list) > 1: txn_amount = amount_list[-2] 
                            
                        current_txn = {
                            "Date": date_str,
                            "Narration": narration,
                            "Amount": txn_amount,
                            "Balance": balance,
                            "Debit": 0.0,   
                            "Credit": 0.0   
                        }
                    else:
                        if current_txn and len(line) > 2:
                            ignore = ['page', 'balance', 'total', 'statement', 'branch']
                            if not any(ig in line.lower() for ig in ignore):
                                clean_line_parts = [p for p in line.split() if not re.match(r'^-?\d+(\.\d+)?$', p.replace(',',''))]
                                if clean_line_parts:
                                    current_txn["Narration"] += " " + " ".join(clean_line_parts)
                                    
                if current_txn:
                    raw_transactions.append(current_txn)

        # --- MATHEMATICAL RECONCILIATION ---
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            amt = curr["Amount"]
            
            if i > 0:
                prev_bal = raw_transactions[i-1]["Balance"]
                curr_bal = curr["Balance"]
                
                if round(prev_bal + amt, 2) == round(curr_bal,
