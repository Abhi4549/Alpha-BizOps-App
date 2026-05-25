import pandas as pd
import re
import pdfplumber

def clean_narration(text):
    text = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '', str(text))
    return re.sub(r'\s+', ' ', text).strip()

def process_bank_statement(file, pdf_pw=""):
    try:
        if file.name.endswith('.pdf'):
            with pdfplumber.open(file, password=pdf_pw) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages])
            lines = [l for l in text.split('\n') if re.match(r'^\d{1,2}[/-]\d{1,2}', l)]
            data = [{"Date": l.split()[0], "Narration": clean_narration(" ".join(l.split()[1:])), "Debit": 0.0, "Credit": 0.0} for l in lines]
            return pd.DataFrame(data), {"dr_count": 0, "cr_count": 0}
        else:
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, encoding='latin1')
            # Assuming standard headers: Date, Narration, Debit, Credit
            df.columns = [c.lower() for c in df.columns]
            # Simple column mapping
            return df, {"dr_count": len(df), "cr_count": len(df)}
    except Exception as e:
        return None, str(e)
