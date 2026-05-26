# File: modules/bank_engine.py
import pdfplumber
import pandas as pd
import io
import re

def clean_amount(val):
    if not val: return 0.0
    val = str(val).replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
    try: return float(val)
    except: return 0.0

def process_tally_standard(file, password=""):
    extracted_data = []
    meta = {"opening_bal": 0.0, "closing_bal": 0.0, "debit_count": 0, "credit_count": 0}
    
    try:
        with pdfplumber.open(file, password=password) as pdf:
            date_pattern = re.compile(r'^\d{1,2}[/\-\s]([a-zA-Z]{3}|\d{1,2})[/\-\s]\d{2,4}')
            for page in pdf.pages:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "intersection_tolerance": 15,
                    "snap_tolerance": 5,
                })
                
                for table in tables:
                    temp_row = None
                    for row in table:
                        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        compact_row = [cell for cell in cleaned_row if cell != ""]
                        if not compact_row: continue
                        row_text = " ".join(compact_row).lower()
                        
                        if "opening balance" in row_text or "b/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["opening_bal"] = clean_amount(nums[-1])
                        if "closing balance" in row_text or "c/f" in row_text:
                            nums = re.findall(r'[\d,]+\.\d{2}', row_text)
                            if nums: meta["closing_bal"] = clean_amount(nums[-1])

                        if date_pattern.search(compact_row[0]):
                            if temp_row: extracted_data.append(temp_row)
                            
                            date = compact_row[0]
                            narration = compact_row[1] if len(compact_row) > 1 else ""
                            amounts = [clean_amount(x) for x in compact_row[2:] if re.match(r'^-?[\d,]+(\.\d{1,2})?$', str(x).replace(',',''))]
                            
                            debit, credit, balance = 0.0, 0.0, 0.0
                            if len(amounts) >= 3: debit, credit, balance = amounts[-3], amounts[-2], amounts[-1]
                            elif len(amounts) == 2: debit, credit = amounts[0], amounts[1]
                            elif len(amounts) == 1:
                                if "cr" in row_text: credit = amounts[0]
                                else: debit = amounts[0]
                                
                            temp_row = {"Date": date, "Narration": narration, "Debit": debit, "Credit": credit, "Balance": balance}
                            if debit > 0: meta["debit_count"] += 1
                            if credit > 0: meta["credit_count"] += 1
                        else:
                            if temp_row and len(compact_row) > 0:
                                temp_row["Narration"] += " " + " ".join(compact_row)
                    if temp_row: extracted_data.append(temp_row)
        return extracted_data, meta, "Success"
    except Exception as e: return None, None, str(e)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TallyData')
    return output.getvalue()
