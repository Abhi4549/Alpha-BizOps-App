import streamlit as st
from logic.models import Party, InventoryItem, Voucher

st.set_page_config(layout="wide", page_title="Alpha Vyapar Pro")

st.sidebar.title("🥷 ALPHA VYAPAR PRO")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Sales Invoice", "GST Reports", "Tally Sync"])

if menu == "Dashboard":
    st.title("📊 Financial Overview")
    # Yahan hum P&L aur Stock ka logic layenge
    
elif menu == "Sales Invoice":
    st.title("🧾 Generate Invoice")
    # Invoice banne ka logic
    party_name = st.text_input("Party Name")
    if st.button("Save Invoice"):
        st.success(f"Invoice for {party_name} saved!")
