import pdfplumber
import pandas as pd
import re

def process_invoice_pdf(file, pdf_pw=""):
    try:
        # --- 1. FILE TYPE IDENTIFICATION ---
        if file.name.endswith('.pdf'):
            full_text = ""
            extracted_tables = []
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                    extracted_tables.extend(page.extract_tables())
        else:
            # Excel/CSV ke liye Flexible Reader
            df_file = pd.read_excel(file, header=None) if file.name.endswith('.xlsx') else pd.read_csv(file, header=None)
            # Row 0 se 10 tak search karein ki header kahan hai
            header_row = 0
            for i in range(min(10, len(df_file))):
                if 'hsn' in str(df_file.iloc[i]).lower() or 'qty' in str(df_file.iloc[i]).lower():
                    header_row = i
                    break
            df_file.columns = df_file.iloc[header_row]
            df_file = df_file[header_row+1:]
            
            # DataFrame ko lists mein convert karein OCR engine ke liye
            full_text = df_file.to_string()
            extracted_tables = [df_file.columns.tolist()] + df_file.values.tolist()

        # --- 2. EXTRACTION LOGIC ---
        # (Wahi GSTIN, Date, Total wala logic)
        gstin = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b', full_text)
        total = re.search(r'(?:Total|Amount)[\s:₹]*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        
        items_list = []
        for row in extracted_tables:
            # Sirf wahi rows uthayein jisme digits (HSN/Qty) hain
            row_clean = [str(c).strip() if c else "" for c in row]
            if any(re.match(r'^\d', c) for c in row_clean if c):
                items_list.append(row_clean)

        df_main = pd.DataFrame({"Voucher": ["Sales"], "GSTIN": [gstin.group(0) if gstin else "N/A"], "Total": [total.group(1) if total else "0"]})
        
        # Line Items Table (HSN, Qty, Rate, Taxable)
        df_items = pd.DataFrame(items_list) if items_list else pd.DataFrame(columns=["Details", "HSN", "Qty", "Rate", "Taxable"])
        
        return df_main, df_items, "Success"
    except Exception as e:
        return None, None, f"Read Error: {str(e)}"
