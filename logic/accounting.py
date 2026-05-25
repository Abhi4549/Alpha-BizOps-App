# logic/accounting.py

class AccountingEngine:
    @staticmethod
    def calculate_tax(taxable_amount, gst_rate):
        """GST aur Tax split ka surgical math"""
        tax_amount = taxable_amount * (gst_rate / 100)
        cgst = tax_amount / 2
        sgst = tax_amount / 2
        return round(cgst, 2), round(sgst, 2), round(tax_amount, 2)

    @staticmethod
    def apply_round_off(amount):
        """Tally-style rounding"""
        rounded = round(amount)
        diff = rounded - amount
        return rounded, round(diff, 2)

    @staticmethod
    def generate_ledger_entry(party_name, amount, v_type):
        """Entry object jo Tally XML engine ko jayega"""
        return {
            "ledger": party_name,
            "amount": amount,
            "type": "Debit" if v_type == "Sales" else "Credit"
        }
