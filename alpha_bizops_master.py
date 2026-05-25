import streamlit as st
from datetime import datetime
from logic.models import Party, Voucher
from logic.accounting import AccountingEngine
from logic.db_manager import init_db, save_invoice, get_all_invoices
from logic.engine import create_tally_voucher_xml

# 1. App Configuration
st.set_page_config(page_title="Alpha Vyapar Pro", layout="wide")
init_db() # Database start

st.title("🥷 ALPHA VYAPAR PRO | ENTERPRISE ERP")

# 2. Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Sales Invoice", "Ledger Sync", "Tally XML"])

# 3. DASHBOARD PANEL
if menu == "Dashboard":
    st.subheader("Financial Overview")
    invoices = get_all_invoices()
    total_sales = sum([inv[2] for inv in invoices])
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sales", f"₹ {total_sales:,.2f}")
    c2.metric("Total Invoices", len(invoices))
    st.dataframe(invoices, use_container_width=True)

# 4. SALES INVOICE PANEL
elif menu == "Sales Invoice":
    st.subheader("GST Sales Invoice Generator")
    with st.form("invoice_form"):
        col1, col2 = st.columns(2)
        party_name = col1.text_input("Party Name")
        amt = col2.number_input("Taxable Amount", min_value=0.0)
        gst = st.slider("GST Rate (%)", 0, 28, 18)
        
        if st.form_submit_button("Save & Generate"):
            # Calculate Tax
            cgst, sgst, tax = AccountingEngine.calculate_tax(amt, gst)
            # Save to DB
            save_invoice(party_name, amt + tax, gst, str(datetime.now().date()))
            st.success(f"Invoice Saved! Total: ₹{amt + tax:,.2f}")

# 5. TALLY XML GENERATOR
elif menu == "Tally XML":
    st.subheader("Generate Tally Import XML")
    if st.button("Export All Data"):
        invoices = get_all_invoices()
        xml_output = "<ENVELOPE><TALLYMESSAGE>"
        for inv in invoices:
            # Fake mapping for demo
            xml_output += f"<VOUCHER><PARTY>{inv[1]}</PARTY><AMOUNT>{inv[2]}</AMOUNT></VOUCHER>"
        xml_output += "</TALLYMESSAGE></ENVELOPE>"
        st.code(xml_output, language="xml")
        st.download_button("Download XML", xml_output, "tally_import.xml")
