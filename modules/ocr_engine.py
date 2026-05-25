import pdfplumber
import re
import pandas as pd

def process_invoice_pdf(file, pdf_pw=""):
    try:
        full_text = ""
        with pdfplumber.open(file, password=pdf_pw) as pdf:
            full_text = "\n".join([p.extract_text() for p in pdf.pages])
        
        # Regex for Tally Fields
        gstin = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b', full_text)
        inv = re.search(r'(?:Invoice No|Bill No)[\s:.-]*([A-Za-z0-9/-]+)', full_text, re.IGNORECASE)
        total = re.search(r'(?:Total|Amount)[\s:₹]*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        
        df_main = pd.DataFrame({
            "Invoice No": [inv.group(1) if inv else "N/A"],
            "GSTIN": [gstin.group(0) if gstin else "N/A"],
            "Total": [total.group(1) if total else "0"]
        })
        return df_main, "Success"
    except Exception as e:
        return None, str(e)
