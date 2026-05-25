import pdfplumber
import re
import pandas as pd

def process_invoice_pdf(file, pdf_pw=""):
    try:
        full_text = ""
        items_list = []
        
        with pdfplumber.open(file, password=pdf_pw) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
                # Table reading for HSN, Qty, Rate, Tax
                for table in page.extract_tables():
                    for row in table:
                        row_clean = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                        # Logic: Agar row mein 4 se zyada columns hain aur digits hain, toh ye Item Row hai
                        if len(row_clean) >= 4 and any(re.match(r'^\d', c) for c in row_clean[1:]):
                            items_list.append(row_clean)

        # Extraction Logic
        gstin = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b', full_text)
        date = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', full_text)
        total = re.search(r'(?:Total|Grand Total|Net Payable)[\s:₹]*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        
        # Classification (Sale/Purchase)
        bill_type = "Sales" if any(x in full_text.lower() for x in ['tax invoice', 'bill to']) else "Purchase"
        
        # Structure Item Table
        df_items = pd.DataFrame(items_list, columns=["Description", "HSN", "Qty", "Rate", "Taxable Amt", "GST Amt", "Total"][:len(items_list[0]) if items_list else 0])
        
        df_main = pd.DataFrame({
            "Voucher": [bill_type],
            "Date": [date.group(1) if date else "N/A"],
            "GSTIN": [gstin.group(0) if gstin else "N/A"],
            "Total": [total.group(1) if total else "0.00"]
        })
        
        return df_main, df_items, "Success"
    except Exception as e:
        return None, None, str(e)
