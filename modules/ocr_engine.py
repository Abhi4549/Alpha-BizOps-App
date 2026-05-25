import pdfplumber
import re
import pandas as pd

def classify_invoice(text):
    text_lower = text.lower()
    if any(word in text_lower for word in ['tax invoice', 'bill to', 'retail invoice']):
        return "SALE"
    return "PURCHASE"

def process_invoice_pdf(file):
    try:
        full_text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
        
        gstin_pat = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
        date_pat = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
        amt_pat = r'(?:Total|Amount|Grand Total)[\s:₹]*([\d,]+\.\d{2})'
        
        gstins = list(set(re.findall(gstin_pat, full_text)))
        dates = re.findall(date_pat, full_text)
        amounts = re.findall(amt_pat, full_text, re.IGNORECASE)
        
        bill_type = classify_invoice(full_text)
        
        df = pd.DataFrame({
            "File Name": [file.name],
            "Type": [f"🟢 {bill_type}"],
            "GSTIN Detected": [gstins[0] if gstins else "NOT FOUND"],
            "Date": [dates[0] if dates else "UNKNOWN"],
            "Extracted Amount": [amounts[0] if amounts else "0.00"],
            "Party Name": ["🟡 Pending Setup"]
        })
        return df, "Success"
    except Exception as e:
        return None, str(e)
