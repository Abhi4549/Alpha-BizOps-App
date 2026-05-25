def process_bank_statement(file, pdf_pw=""):
    # ... wahi code ...
    # Amount Cleaning Logic change karein:
    def parse_amount(val):
        # Narration aur amount ko separate karne ka logic
        val = str(val).replace(',', '').strip()
        # Regex to find float number at the end of a string
        match = re.search(r'(\d+\.\d{2})\s*(DR|CR)?$', val, re.IGNORECASE)
        if match:
            amt = float(match.group(1))
            type_ = match.group(2)
            if type_ and type_.upper() == 'DR': return amt, 0.0
            return 0.0, amt
        return 0.0, 0.0
    
    # Apply to dataframe
    df[['Debit', 'Credit']] = df[amt_col].apply(lambda x: pd.Series(parse_amount(x)))
