import streamlit as st
import os
import uuid
import subprocess

# Cấu hình trang web
st.set_page_config(page_title="Chuyển đổi Word sang PDF", page_icon="📄", layout="centered")

st.title("📄 Tool Chuyển Đổi Word Sang PDF Online")
st.write("Tải file `.docx` của bạn lên và hệ thống sẽ tự động chuyển đổi sang `.pdf`.")
st.write("---")

def convert_to_pdf(input_path, output_dir):
    """Hàm chuyển đổi linh hoạt giữa Windows (docx2pdf) và Linux (LibreOffice)"""
    if os.name == 'nt':  # Nếu là Windows (Chạy ở máy cá nhân của bạn)
        from docx2pdf import convert
        # Xác định tên file đầu ra cụ thể cho Windows
        pdf_name = os.path.basename(input_path).replace(".docx", ".pdf")
        convert(input_path, os.path.join(output_dir, pdf_name))
    else:  # Nếu là Linux (Chạy trên Server Streamlit Cloud)
        # Sử dụng LibreOffice được cài sẵn trên server để chuyển đổi
        cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path]
        subprocess.run(cmd, check=True)

# Khu vực kéo thả file
uploaded_files = st.file_uploader("Kéo và thả các file Word (.docx) vào đây:", type=["docx"], accept_multiple_files=True)

if uploaded_files:
    st.write(f"📂 Đã chọn **{len(uploaded_files)}** file.")
    
    if st.button("🚀 Bắt đầu chuyển đổi", type="primary"):
        temp_dir = f"temp_{uuid.uuid4().hex}"
        os.makedirs(temp_dir, exist_ok=True)
        
        for index, uploaded_file in enumerate(uploaded_files, start=1):
            with st.spinner(f"Đang xử lý file [{index}/{len(uploaded_files)}]: {uploaded_file.name}..."):
                try:
                    # 1. Lưu file Word tạm
                    input_word_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(input_word_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 2. Gọi hàm chuyển đổi
                    convert_to_pdf(input_word_path, temp_dir)
                    
                    # 3. Đọc file PDF đầu ra
                    output_pdf_name = uploaded_file.name.replace(".docx", ".pdf")
                    output_pdf_path = os.path.join(temp_dir, output_pdf_name)
                    
                    with open(output_pdf_path, "rb") as pdf_file:
                        pdf_data = pdf_file.read()
                    
                    # 4. Trả file cho người dùng tải về
                    st.success(f"✓ Đã chuyển đổi xong: {uploaded_file.name}")
                    st.download_button(
                        label=f"📥 Tải về file: {output_pdf_name}",
                        data=pdf_data,
                        file_name=output_pdf_name,
                        mime="application/pdf",
                        key=f"download_{index}"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Lỗi khi xử lý file {uploaded_file.name}: {e}")
                finally:
                    if os.path.exists(input_word_path):
                        os.remove(input_word_path)
        
        st.balloons()