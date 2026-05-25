import pdfplumber
import pandas as pd

def process_invoice_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            full_text = "\n".join([p.extract_text() for p in pdf.pages])
        # Basic Header (Dummy for now)
        df = pd.DataFrame({"Info": ["Invoice Read Successfully"], "Content": [full_text[:50]]})
        return df, "Success"
    except Exception as e:
        return None, str(e)
