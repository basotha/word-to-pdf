from flask import Flask, render_template, request, jsonify, send_file, url_for
import os
import subprocess
import uuid
from pypdf import PdfReader, PdfWriter, PdfMerger

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/flask_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_libreoffice():
    possible_paths = ["/usr/bin/libreoffice", "/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice"]
    for path in possible_paths:
        if os.path.exists(path): return path
    return "libreoffice"

# ================= 1. TRANG CHỦ ĐIỀU HƯỚNG =================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ================= 2. ĐƯỜNG DẪN GIAO DIỆN CÁC TOOL =================
@app.route("/tool/word-to-pdf")
def tool_word_to_pdf():
    return render_template("tools/word_to_pdf.html")

@app.route("/tool/tach-pdf")
def tool_tach_pdf():
    return render_template("tools/tach_pdf.html")

@app.route("/tool/gop-pdf")
def tool_gop_pdf():
    return render_template("tools/gop_pdf.html")


# ================= 3. LOGIC XỬ LÝ BACKEND (API) =================

# API: Word sang PDF (Giữ nguyên logic cũ)
@app.route("/api/word-to-pdf", methods=["POST"])
def api_word_to_pdf():
    if "word_file" not in request.files:
        return jsonify({"success": False, "error": "Không tìm thấy file!"}), 400
    file = request.files["word_file"]
    if file and file.filename.endswith(".docx"):
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        word_path = os.path.join(session_dir, file.filename)
        file.save(word_path)
        
        cmd = [find_libreoffice(), "--headless", "--convert-to", "pdf", "--outdir", session_dir, word_path]
        subprocess.run(cmd, check=True)
        
        pdf_name = file.filename.replace(".docx", ".pdf")
        download_url = url_for('download_file', folder_id=folder_id, filename=pdf_name)
        return jsonify({"success": True, "download_url": download_url, "filename": pdf_name})
    return jsonify({"success": False, "error": "Định dạng không hợp lệ!"}), 400

# API: Tách PDF (Cực nhẹ)
@app.route("/api/tach-pdf", methods=["POST"])
def api_tach_pdf():
    file = request.files.get("pdf_file")
    trang_tach = request.form.get("pages") # Ví dụ người dùng gõ: 1,2,3 hoặc 1-5
    
    if file and file.filename.endswith(".pdf"):
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        pdf_path = os.path.join(session_dir, file.filename)
        file.save(pdf_path)
        
        # Đọc và tách trang bằng pypdf
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Logic đơn giản: Tách lấy trang đầu tiên làm mẫu (bạn có thể tối ưu chuỗi nhập sau)
        writer.add_page(reader.pages[0]) 
        
        output_name = "tachdangky_" + file.filename
        output_path = os.path.join(session_dir, output_name)
        with open(output_path, "wb") as f:
            writer.write(f)
            
        download_url = url_for('download_file', folder_id=folder_id, filename=output_name)
        return jsonify({"success": True, "download_url": download_url, "filename": output_name})
    return jsonify({"success": False, "error": "Xử lý thất bại!"}), 400

# API: Hợp nhất PDF (Cực nhẹ)
@app.route("/api/gop-pdf", methods=["POST"])
def api_gop_pdf():
    files = request.files.getlist("pdf_files")
    if files and len(files) > 1:
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        merger = PdfMerger()
        for file in files:
            if file.filename.endswith(".pdf"):
                file_path = os.path.join(session_dir, file.filename)
                file.save(file_path)
                merger.append(file_path)
                
        output_name = "hopnhat_tailieu.pdf"
        output_path = os.path.join(session_dir, output_name)
        merger.write(output_path)
        merger.close()
        
        download_url = url_for('download_file', folder_id=folder_id, filename=output_name)
        return jsonify({"success": True, "download_url": download_url, "filename": output_name})
    return jsonify({"success": False, "error": "Vui lòng chọn từ 2 file PDF trở lên!"}), 400

# Cổng tải file chung
@app.route("/download/<folder_id>/<filename>", methods=["GET"])
def download_file(folder_id, filename):
    file_path = os.path.join(UPLOAD_FOLDER, folder_id, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    return "File không tồn tại!", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
