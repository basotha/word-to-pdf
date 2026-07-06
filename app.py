from flask import Flask, render_template, request, send_file, flash, redirect
import os
import subprocess
import uuid

app = Flask(__name__)
app.secret_key = "secret_key_cho_session_flask"

UPLOAD_FOLDER = "/tmp/flask_uploads" if os.name != 'nt' else "C:/tmp/flask_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_libreoffice():
    """Tự động tìm đường dẫn LibreOffice trên Linux"""
    possible_paths = [
        "/usr/bin/libreoffice", "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice"
    ]
    for path in possible_paths:
        if os.path.exists(path): return path
    return "libreoffice" # Giả định hệ thống nhận lệnh global

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Kiểm tra xem người dùng có upload file lên không
        if "word_files" not in request.files:
            flash("Không tìm thấy file nào được gửi lên!")
            return redirect(request.url)
            
        files = request.files.getlist("word_files")
        
        # Ở bản Flask đơn giản này, ta xử lý chuyển đổi file đầu tiên thành công
        # (Bạn có thể nâng cấp gộp zip nếu người dùng up nhiều file)
        for file in files:
            if file.filename == "": continue
            if file and file.filename.endswith(".docx"):
                # Tạo thư mục tạm riêng cho lượt xử lý này
                session_dir = os.path.join(UPLOAD_FOLDER, uuid.uuid4().hex)
                os.makedirs(session_dir, exist_ok=True)
                
                # Lưu file Word tạm
                word_path = os.path.join(session_dir, file.filename)
                file.save(word_path)
                
                # Tiến hành chuyển đổi
                if os.name == 'nt':  # Windows
                    from docx2pdf import convert
                    pdf_name = file.filename.replace(".docx", ".pdf")
                    pdf_path = os.path.join(session_dir, pdf_name)
                    convert(word_path, pdf_path)
                else:  # Linux (Hugging Face / Docker)
                    libreoffice_bin = find_libreoffice()
                    cmd = [libreoffice_bin, "--headless", "--convert-to", "pdf", "--outdir", session_dir, word_path]
                    subprocess.run(cmd, check=True)
                    pdf_name = file.filename.replace(".docx", ".pdf")
                    pdf_path = os.path.join(session_dir, pdf_name)
                
                # Trả file PDF về thẳng trình duyệt của người dùng để tải xuống
                return send_file(pdf_path, as_attachment=True, download_name=pdf_name)
                
        flash("Vui lòng chọn đúng file định dạng .docx")
        return redirect(request.url)
        
    return render_template("index.html")

if __name__ == "__main__":
    # Hugging Face yêu cầu chạy cổng 7860
    app.run(host="0.0.0.0", port=7860, debug=True)
