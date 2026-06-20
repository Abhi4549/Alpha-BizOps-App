import pikepdf
import io

def robust_unlocker(file_bytes, password_list):
    for pwd in password_list:
        try:
            # Attempt to open with password
            with pikepdf.open(io.BytesIO(file_bytes), password=pwd) as pdf:
                # Force re-save in memory to strip permissions
                output_stream = io.BytesIO()
                pdf.save(output_stream)
                output_stream.seek(0)
                return output_stream # Return the unlocked stream
        except:
            continue
    return None
