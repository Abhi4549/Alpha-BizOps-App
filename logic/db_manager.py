# logic/db_manager.py
import sqlite3

def init_db():
    conn = sqlite3.connect('alpha_erp.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS invoices 
                 (id INTEGER PRIMARY KEY, party_name TEXT, amount REAL, gst_rate REAL, date TEXT)''')
    conn.commit()
    conn.close()

def save_invoice(party, amount, gst, date):
    conn = sqlite3.connect('alpha_erp.db')
    c = conn.cursor()
    c.execute("INSERT INTO invoices (party_name, amount, gst_rate, date) VALUES (?, ?, ?, ?)", 
              (party, amount, gst, date))
    conn.commit()
    conn.close()

def get_all_invoices():
    conn = sqlite3.connect('alpha_erp.db')
    c = conn.cursor()
    c.execute("SELECT * FROM invoices")
    data = c.fetchall()
    conn.close()
    return data
