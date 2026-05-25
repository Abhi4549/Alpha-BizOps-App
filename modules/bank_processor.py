import pandas as pd
import pdfplumber
import re

def clean_amount(val):
    """Amount ko saaf karke float mein badlega"""
    try:
        if pd.isna(val) or val == "": return 0.0
        # ₹ aur commas hatayein
        s = str(val).replace('₹', '').replace(',', '').strip()
        return float(s)
    except: return 0.0

def process_bank_statement(file, pdf_pw=""):
    try:
        data = []
        with pdfplumber.open(file, password=pdf_pw) as pdf:
            for page in pdf.pages:
                # Lattice mode bank statements ke liye best hai
                table = page.extract_table(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "text"})
                if table:
                    for row in table:
                        # Row mein se Date, Narr, Debit, Credit nikalna
                        # [Date, Narr, Debit, Credit]
                        if len(row) >= 4 and row[0] and '/' in str(row[0]):
                            data.append({
                                "Date": row[0],
                                "Narration": row[1],
                                "Debit": clean_amount(row[2]),
                                "Credit": clean_amount(row[3])
                            })
        
        df = pd.DataFrame(data)
        # Entry count aur totals ke liye audit logic
        metrics = {
            "total_entries": len(df),
            "dr_count": int((df["Debit"] > 0).sum()),
            "cr_count": int((df["Credit"] > 0).sum()),
            "total_dr": df["Debit"].sum(),
            "total_cr": df["Credit"].sum()
        }
        return df, metrics
    except Exception as e:
        return None, str(e)
