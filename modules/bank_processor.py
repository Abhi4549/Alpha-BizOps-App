import pandas as pd
import pdfplumber

def process_bank_statement(file):
    try:
        # Excel/CSV Reader
        if file.name.endswith(('.xlsx', '.csv')):
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file, encoding='latin1')
            df.columns = [str(c).lower().strip() for c in df.columns]
        
        # PDF Reader (Line-by-line reconstruction)
        else:
            data = []
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    lines = page.extract_text().split('\n')
                    for line in lines:
                        # Har line ko split karke data nikalna
                        parts = line.split()
                        if len(parts) > 2:
                            data.append({
                                "Date": parts[0],
                                "Narration": " ".join(parts[1:-1]), # Pura narration
                                "Amount": parts[-1]
                            })
            df = pd.DataFrame(data)
            
        return df, "Success"
    except Exception as e:
        return None, str(e)
