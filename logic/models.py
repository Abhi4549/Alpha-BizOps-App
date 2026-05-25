# logic/models.py
class Party:
    def __init__(self, name, gst_no, type):
        self.name = name
        self.gst_no = gst_no
        self.type = type 

class InventoryItem:
    def __init__(self, name, hsn, gst_rate, purchase_price, sale_price):
        self.name = name
        self.hsn = hsn
        self.gst_rate = gst_rate
        self.purchase_price = purchase_price
        self.sale_price = sale_price

class Voucher:
    def __init__(self, date, party, items, v_type):
        self.date = date
        self.party = party
        self.items = items # List of dicts: {'name': str, 'qty': int, 'rate': float}
        self.v_type = v_type # Sales/Purchase

    def get_total(self):
        return sum(item['qty'] * item['rate'] for item in self.items)
