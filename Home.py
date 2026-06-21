# ==========================================
# 3. BACKEND: PDF PARSER WITH PyPDF2 BYPASS
# ==========================================
def process_mathematical_parser(file, password_list):
    raw_transactions = []
    pdf_bytes = file.read()
    file.seek(0)
    
    unlocked_pdf_stream = None
    
    # ⚡ ENGINE 1: PyPDF2 SECURITY BYPASS
    try:
        temp_stream = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(temp_stream)
        
        if pdf_reader.is_encrypted:
            unlocked = False
            for pwd in password_list:
                if not pwd: 
                    continue
                try:
                    if pdf_reader.decrypt(pwd): 
                        unlocked = True
                        break
                except Exception:
                    continue
            
            if not unlocked:
                return None, "PDF is locked. Auto-Unlock failed. Please provide exact Password/PAN/DOB."
            
            pdf_writer = PyPDF2.PdfWriter()
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            unlocked_pdf_stream = io.BytesIO()
            pdf_writer.write(unlocked_pdf_stream)
            unlocked_pdf_stream.seek(0)
        else:
            unlocked_pdf_stream = io.BytesIO(pdf_bytes)
            
    except Exception as e:
        return None, f"Decryption Engine Error: {str(e)}"

    # ⚡ ENGINE 2: PROFESSIONAL PDF EXTRACTION (Fixed Logic)
    try:
        with pdfplumber.open(unlocked_pdf_stream) as pdf:
            # More forgiving date regex: handles spaces, slashes, dashes, dots
            date_pattern = re.compile(r'^\s*(\d{1,2}[\s/\-\.]+(?:\d{1,2}|[a-zA-Z]{3,10})[\s/\-\.]+\d{2,4})')

            for page in pdf.pages:
                # Removed layout=True to prevent erratic space injections
                text = page.extract_text()
                if not text: 
                    continue
                
                lines = text.split('\n')
                current_txn = None

                for line in lines:
                    line = line.strip()
                    if not line: 
                        continue

                    match = date_pattern.search(line)
                    if match:
                        if current_txn: 
                            raw_transactions.append(current_txn)

                        # Standardize date format
                        raw_date_str = match.group(1)
                        date_str = re.sub(r'[\s\.\-]', '/', raw_date_str)
                        date_str = re.sub(r'/+', '/', date_str)
                        
                        rem = line[match.end():].strip()

                        # Professional Logic: Scan right-to-left to safely extract amounts
                        parts = rem.split()
                        numbers = []
                        
                        for part in reversed(parts):
                            clean_part = part.replace(',', '').replace('Cr', '').replace('Dr', '').replace('cr', '').replace('dr', '').strip()
                            # Check if it's a valid decimal amount
                            if re.match(r'^-?\d+(\.\d+)?$', clean_part):
                                numbers.append(float(clean_part))
                            else:
                                break # Stop when we hit alphabetical words (the narration)

                        # Restore correct left-to-right order for the numbers
                        numbers.reverse()

                        # Everything before the numbers is the narration
                        if numbers:
                            narration = " ".join(parts[:-len(numbers)])
                        else:
                            narration = " ".join(parts)

                        # Assign numbers based on columns found
                        balance = 0.0
                        debit = 0.0
                        credit = 0.0

                        if len(numbers) >= 1:
                            balance = numbers[-1]
                        
                        if len(numbers) == 2:
                            # We have Amount and Balance. Will calculate Dr/Cr below.
                            txn_amount = numbers[-2]
                            current_txn = {"Date": date_str, "Narration": narration, "Amount": txn_amount, "Balance": balance, "Debit": 0.0, "Credit": 0.0, "Needs_Calc": True}
                        elif len(numbers) >= 3:
                            # We have standard 3 columns: Debit, Credit, Balance
                            credit = numbers[-2]
                            debit = numbers[-3]
                            current_txn = {"Date": date_str, "Narration": narration, "Amount": max(debit, credit), "Balance": balance, "Debit": debit, "Credit": credit, "Needs_Calc": False}
                        else:
                            # Edge case: No clear amounts found on this line
                            current_txn = {"Date": date_str, "Narration": narration, "Amount": 0.0, "Balance": balance, "Debit": 0.0, "Credit": 0.0, "Needs_Calc": True}

                    else:
                        # Append multi-line descriptions securely
                        if current_txn and len(line) > 2:
                            ignore_words = ['page', 'balance', 'total', 'statement', 'branch', 'opening', 'closing', 'brought forward', 'c/f', 'b/f']
                            if not any(ig in line.lower() for ig in ignore_words):
                                current_txn["Narration"] += " " + line

                if current_txn: 
                    raw_transactions.append(current_txn)

        if not raw_transactions:
            return None, "Document unlocked, but no transactions found. If this is a scanned photo, standard digital parsing cannot read it."

        # Post-Processing: Calculate any missing Debits/Credits using Balance deltas
        for i in range(len(raw_transactions)):
            curr = raw_transactions[i]
            if curr.get("Needs_Calc", False):
                if i > 0:
                    prev_bal = raw_transactions[i-1]["Balance"]
                    curr_bal = curr["Balance"]
                    diff = round(curr_bal - prev_bal, 2)

                    if diff > 0:
                        curr["Credit"] = diff
                        curr["Debit"] = 0.0
                    elif diff < 0:
                        curr["Debit"] = abs(diff)
                        curr["Credit"] = 0.0
                    else:
                        curr["Credit"] = curr["Amount"] if curr["Amount"] > 0 else 0.0
                else:
                    # Guess for the very first transaction based on keywords
                    narration_upper = curr["Narration"].upper()
                    if any(kw in narration_upper for kw in ["RTGS", "NEFT", "UPI", "IMPS", "CHQ", "ATM", "WITHDRAW", "DR", "DEBIT"]):
                        curr["Debit"] = curr["Amount"]
                    else:
                        curr["Credit"] = curr["Amount"]
            
            # Clean up temporary keys before passing to pandas/Tally
            curr.pop("Needs_Calc", None)
            curr.pop("Amount", None)

        return raw_transactions, "Success"
    except Exception as e: 
        return None, f"Parsing Error: {str(e)}"
