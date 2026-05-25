import streamlit as st
from logic.models import Party, Voucher
from logic.accounting import AccountingEngine
from logic.engine import create_tally_voucher_xml

st.set_page_config(page_title="Alpha Vyapar Pro", layout="wide")

st.title("🥷 ALPHA VYAPAR PRO | ENTERPRISE ERP")

# Sidebar Navigation
menu = st.sidebar.selectbox("Main Menu", ["Dashboard", "Sales Invoice", "Tally Sync"])

if menu == "Dashboard":
    st.subheader("Financial Health Overview")
    # Yahan hum future mein live graph daalenge
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sales", "₹ 0.00")
    c2.metric("GST Payable", "₹ 0.00")
    c3.metric("Outstanding", "₹ 0.00")

elif menu == "Sales Invoice":
    st.subheader("Generate GST Sales Invoice")
    with st.form("invoice_form"):
        col1, col2 = st.columns(2)
        party_name = col1.text_input("Party Name")
        taxable_amt = col2.number_input("Taxable Amount (₹)", min_value=0.0)
        gst_rate = st.slider("GST Rate (%)", 0, 28, 18)
        
        submitted = st.form_submit_button("Generate & Calculate")
        if submitted:
            cgst, sgst, total_tax = AccountingEngine.calculate_tax(taxable_amt, gst_rate)
            st.write(f"CGST: ₹{cgst} | SGST: ₹{sgst}")
            st.write(f"Total Amount: ₹{taxable_amt + total_tax}")
            
            # Voucher save karne ka logic (Mock)
            st.success("Invoice Details Saved Successfully!")

elif menu == "Tally Sync":
    st.subheader("Tally Native XML Export")
    if st.button("Generate Tally Import File"):
        # Yahan hum logic.engine ko call karenge
        st.info("Vouchers fetched from DB...")
