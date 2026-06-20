import streamlit as st
import pikepdf
import io
import pandas as pd
import re

# ==========================================
# 1. AGGRESSIVE UNLOCKER ENGINE
# ==========================================
def force_unlock_pdf(uploaded_file, password_list):
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    
    # Try every password in the list
    for pwd in password_list:
        try:
            # allow_overwriting_input=True ensures we bypass read-only locks
            with pikepdf.open(io.BytesIO(file_bytes), password=pwd, allow_overwriting_input=True) as pdf:
                # Save into a new memory buffer to strip encryption
                output_buffer = io.BytesIO()
                pdf.save(output_buffer)
                output_buffer.seek(0)
                return output_buffer, "SUCCESS"
        except pikepdf.PasswordError:
            continue
        except Exception as e:
            return None, str(e)
            
    return None, "FAILED: Password not in list."

# ==========================================
# 2. PASSWORD GENERATOR
# ==========================================
def generate_bank_passwords(name, dob, pan, custom):
    pwds = [custom] if custom else []
    if dob:
        d, m, y, y2 = dob.strftime("%d"), dob.strftime("%m"), dob.strftime("%Y"), dob.strftime("%y")
        # Standard Bank Patterns
        pwds.extend([f"{d}{m}{y}", f"{d}{m}{y2}"])
        if name:
            n4 = re.sub(r'[^a-zA-Z]', '', name)[:4].lower()
            pwds.extend([f"{n4}{d}{m}", f"{n4}{d}{m}{y}"])
    if pan:
        pwds.extend([pan.lower(), pan.upper()])
    return list(set(filter(None, pwds)))

# ==========================================
# 3. STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Alpha Unlocker", layout="centered")
st.title("🏦 Alpha PDF Unlocker")

uploaded_file = st.file_uploader("Upload Locked PDF", type=['pdf'])
name = st.text_input("Name (First 4 chars)")
dob = st.date_input("DOB", None)
pan = st.text_input("PAN")
custom = st.text_input("Manual Password Override")

if st.button("Attempt Unlock"):
    if not uploaded_file:
        st.error("Upload file first!")
    else:
        pwds = generate_bank_passwords(name, dob, pan, custom)
        st.write(f"Trying passwords: {pwds}") # Debugging
        
        unlocked_stream, status = force_unlock_pdf(uploaded_file, pwds)
        
        if unlocked_stream:
            st.success("✅ File Unlocked Successfully!")
            st.download_button("Download Unlocked PDF", unlocked_stream, "unlocked_statement.pdf")
        else:
            st.error(f"❌ {status}. Try manually entering the correct password in the override field.")
