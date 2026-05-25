with tab1:
    st.subheader("🏦 Bank Statement Cleaner")
    file = st.file_uploader("Upload Bank Statement")
    if file and st.button("Process Bank"):
        df, metrics = process_bank_statement(file)
        if df is not None:
            st.session_state.data = df
            # Audit Summary Box
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Entries", metrics['total_entries'])
            col2.metric("Debit Entries", metrics['dr_count'], f"₹{metrics['total_dr']:,.2f}")
            col3.metric("Credit Entries", metrics['cr_count'], f"₹{metrics['total_cr']:,.2f}")
            
            st.dataframe(df, use_container_width=True)
        else:
            st.error(metrics)
