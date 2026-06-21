with pdfplumber.open(unlocked_pdf_stream) as pdf:
    for page in pdf.pages:

        tables = page.extract_tables()

        if tables:
            for table in tables:
                for row in table:

                    if not row:
                        continue

                    row = [str(x).strip() if x else "" for x in row]

                    date_match = re.search(
                        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                        row[0] if len(row) else ""
                    )

                    if not date_match:
                        continue

                    date_val = date_match.group()

                    narration = " ".join(
                        x for x in row[1:-3]
                        if x
                    )

                    debit = 0.0
                    credit = 0.0
                    balance = 0.0

                    try:
                        balance = float(
                            row[-1].replace(",", "")
                        )
                    except:
                        pass

                    try:
                        debit = float(
                            row[-3].replace(",", "")
                        )
                    except:
                        pass

                    try:
                        credit = float(
                            row[-2].replace(",", "")
                        )
                    except:
                        pass

                    raw_transactions.append({
                        "Date": date_val,
                        "Narration": narration,
                        "Debit": debit,
                        "Credit": credit,
                        "Balance": balance
                    })

        else:
            text = page.extract_text()
