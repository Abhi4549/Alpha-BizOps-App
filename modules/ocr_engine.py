import pdfplumber
import re
import pandas as pd

def classify_invoice(text):
    text_lower = text.lower()
    if any(word in text_lower for word in ['tax invoice', 'bill to', 'retail invoice', 'cash memo']):
        return "Sales"
    return "Purchase"

def process_invoice_pdf(file, pdf_pw=""):
    try:
        full_text = ""
        extracted_tables = []
        
        # 1. READ FILE (PDF OR EXCEL)
        if file.name.endswith('.pdf'):
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                    tables = page.extract_tables()
                    for t in tables:
                        if t: extracted_tables.extend(t)
        else: # Excel / CSV Bill
            df_file = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            full_text = df_file.to_string()
            # Convert Excel directly to table format
            extracted_tables = [df_file.columns.tolist()] + df_file.values.tolist()

        # 2. HEADER EXTRACTION FOR TALLY
        gstin_pat = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
        date_pat = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})\b'
        amt_pat = r'(?:Total|Amount|Grand Total|Net Payable)[\s:₹A-Za-z]*([\d,]+\.\d{2})'
        inv_pat = r'(?:Invoice No|Bill No|Inv No|Receipt No)[\s:.-]*([A-Za-z0-9/-]+)'
        tax_pat = r'(?:IGST|CGST|SGST|Tax Amount)[\s@%]*[\d.]*[\s:₹]*([\d,]+\.\d{2})'
        
        gstins = list(set(re.findall(gstin_pat, full_text)))
        dates = re.findall(date_pat, full_text)
        amounts = re.findall(amt_pat, full_text, re.IGNORECASE)
        inv_nos = re.findall(inv_pat, full_text, re.IGNORECASE)
        taxes = re.findall(tax_pat, full_text, re.IGNORECASE)
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip() and len(l.strip()) > 3]
        party_name = lines[0] if lines else "🟡 Unknown Party"
        bill_type = classify_invoice(full_text)
        
        # 3. TALLY READY LINE ITEM EXTRACTION
        items_list = []
        if extracted_tables:
            for row in extracted_tables:
                if not row: continue
                row_str = " ".join(str(cell).lower() for cell in row if cell)
                
                if 'hsn' in row_str or 'qty' in row_str or 'rate' in row_str:
                    continue
                
                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                item_name = clean_row[0] if len(clean_row) > 0 else "Default Item"
                hsn, qty, rate, amt = "", "1", "0", "0"
                
                for cell in clean_row[1:]:
                    if re.match(r'^\d{4,8}$', cell): hsn = cell
                    elif re.match(r'^\d+$', cell) and qty == "1": qty = cell
                    elif re.match(r'^[\d,]+\.\d{2}$', cell):
                        if rate == "0": rate = cell.replace(',', '')
                        else: amt = cell.replace(',', '')
                        
                if item_name and (rate != "0" or amt != "0"):
                    items_list.append([item_name, hsn, qty, rate, amt])

        df_main = pd.DataFrame({
            "File Name": [file.name],
            "Voucher Type": [bill_type],
            "Invoice No": [inv_nos[0] if inv_nos else "1"],
            "Party Name": [party_name],
            "GSTIN Detected": [gstins[0] if gstins else "UNREGISTERED"],
            "Date": [dates[0] if dates else "01-04-2026"],
            "Tax (GST)": [taxes[0] if taxes else "0.00"],
            "Total Amount": [amounts[0] if amounts else "0.00"]
        })

        if items_list:
            df_items = pd.DataFrame(items_list, columns=["Item Name", "HSN", "Qty", "Rate", "Amount"])
        else:
            df_items = pd.DataFrame([["Misc Item", "9999", "1", amounts[0] if amounts else "0", amounts[0] if amounts else "0"]], columns=["Item Name", "HSN", "Qty", "Rate", "Amount"])

        return df_main, df_items, "Success"
        
    except Exception as e:
        return None, None, f"File Extraction Failed: {str(e)}"
