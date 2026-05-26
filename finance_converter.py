# File: main_app.py
import streamlit as st
import pandas as pd
from modules.bank_engine import process_tally_standard, to_excel

# --- UI Setup ---
st.set_page_config(page_title="Alpha BizOps Hub", page_icon="🥷", layout="wide")

st.markdown("""
    <style>
    .hero-title { font-size: 40px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 5px;}
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #E5E7EB; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🥷 Alpha BizOps Hub</div>', unsafe_allow_html=True)

# --- Scalable Navigation Menu ---
# Yahan aage chalkar hum "Purchase Bill OCR", "GSTR Reconciliation" add karenge
menu = st.sidebar.radio("Select Tool", ["🏦 Bank Statement Cleaner", "🧾 Future Tools (Coming Soon)"])

if menu == "🏦 Bank Statement Cleaner":
    st.subheader("Deep Cleaned Engine for Tally")
    
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        pdf_password = col1.text_input("PDF Password (if any)", type="password")
        
        if st.button("🚀 Process Data", use_container_width=True):
            with st.spinner("Extracting with Alpha Logic..."):
                # Backend module ko call kiya gaya hai
                raw_data, meta, status = process_tally_standard(uploaded_file, pdf_password)
                
                if raw_data:
                    df = pd.DataFrame(raw_data)
                    st.success("✅ Extraction Completed!")
                    
                    st.markdown("### 📊 Summary")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.markdown(f'<div class="metric-card"><b>Opening Bal</b><br>₹ {meta["opening_bal"]:,.2f}</div>', unsafe_allow_html=True)
                    m2.markdown(f'<div class="metric-card"><b>Closing Bal</b><br>₹ {meta["closing_bal"]:,.2f}</div>', unsafe_allow_html=True)
                    m3.markdown(f'<div class="metric-card"><b>Debits</b><br>{meta["debit_count"]} Txns</div>', unsafe_allow_html=True)
                    m4.markdown(f'<div class="metric-card"><b>Credits</b><br>{meta["credit_count"]} Txns</div>', unsafe_allow_html=True)
                    
                    st.write("### 📝 Preview")
                    st.dataframe(df, use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    c1.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "tally_ready.csv", "text/csv", use_container_width=True)
                    c2.download_button("Download Excel", to_excel(df), "tally_ready.xlsx", use_container_width=True)
                else:
                    st.error(f"❌ Error: {status}")

elif menu == "🧾 Future Tools (Coming Soon)":
    st.info("Yahan hum aage Invoice OCR Scanner aur API modules add karenge. Backend bilkul safe rahega!")
