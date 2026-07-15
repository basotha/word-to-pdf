import os
import subprocess
import uuid
import time
import shutil
from flask import Flask, render_template, request, jsonify, send_file, url_for
from pypdf import PdfReader, PdfWriter, PdfMerger

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Giới hạn 16MB bảo vệ RAM

UPLOAD_FOLDER = "/tmp/flask_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_libreoffice():
    possible_paths = ["/usr/bin/libreoffice", "/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice"]
    for path in possible_paths:
        if os.path.exists(path): return path
    return "libreoffice"

# ================= 1. TỰ ĐỘNG DỌN RÁC =================
@app.before_request
def cleanup_old_files():
    """Tự động xóa các thư mục rác đã tạo quá 15 phút trước"""
    now = time.time()
    if os.path.exists(UPLOAD_FOLDER):
        for folder in os.listdir(UPLOAD_FOLDER):
            folder_path = os.path.join(UPLOAD_FOLDER, folder)
            if os.path.isdir(folder_path):
                # Kiểm tra thời gian chỉnh sửa cuối cùng của thư mục (900 giây = 15 phút)
                if now - os.path.getmtime(folder_path) > 900: 
                    try:
                        shutil.rmtree(folder_path)
                        print(f"🔥 Đã dọn dẹp thư mục rác: {folder}")
                    except Exception as e:
                        print(f"Không thể xóa {folder_path}: {e}")
    
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
    
@app.route("/tool/nen-pdf")
def tool_nen_pdf():
    return render_template("tools/nen_pdf.html")


# ================= 3. LOGIC XỬ LÝ BACKEND (API) =================

# API: Word sang PDF
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

# API: Tách PDF
@app.route("/api/tach-pdf", methods=["POST"])
def api_tach_pdf():
    file = request.files.get("pdf_file")
    pages_str = request.form.get("pages", "").strip()
    
    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"success": False, "error": "Định dạng file không hợp lệ!"}), 400
        
    if not pages_str:
        return jsonify({"success": False, "error": "Vui lòng nhập số trang cần tách!"}), 400

    try:
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        pdf_path = os.path.join(session_dir, file.filename)
        file.save(pdf_path)
        
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        writer = PdfWriter()
        
        selected_pages = set()
        for part in pages_str.split(','):
            part = part.strip()
            if '-' in part:  # Đã tối ưu bọc bảo vệ khi người dùng gõ sai khoảng trang
                try:
                    parts = part.split('-')
                    if len(parts) == 2:
                        start, end = parts[0].strip(), parts[1].strip()
                        if start.isdigit() and end.isdigit():
                            start_idx = int(start) - 1
                            end_idx = int(end) - 1
                            for p in range(max(0, start_idx), min(total_pages, end_idx + 1)):
                                selected_pages.add(p)
                except Exception:
                    pass
            else:
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < total_pages:
                        selected_pages.add(idx)

        pages_to_extract = sorted(list(selected_pages))

        if not pages_to_extract:
            return jsonify({"success": False, "error": "Số trang bạn nhập không nằm trong phạm vi của file PDF!"}), 400

        for page_num in pages_to_extract:
            writer.add_page(reader.pages[page_num])
        
        output_name = f"extracted_{file.filename}"
        output_path = os.path.join(session_dir, output_name)
        with open(output_path, "wb") as f:
            writer.write(f)
            
        download_url = url_for('download_file', folder_id=folder_id, filename=output_name)
        return jsonify({"success": True, "download_url": download_url, "filename": output_name})

    except Exception as e:
        print(f"Lỗi tách PDF: {str(e)}")
        return jsonify({"success": False, "error": "Có lỗi xảy ra trong quá trình xử lý file!"}), 500

# API: Hợp nhất PDF
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
    
# API: Nén PDF đa chế độ (Tương thích chuẩn mô hình pdf.io)
@app.route("/api/nen-pdf", methods=["POST"])
def api_nen_pdf():
    file = request.files.get("pdf_file")
    compression_level = request.form.get("level", "medium") # Mặc định là nén tiêu chuẩn
    
    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"success": False, "error": "Định dạng file không hợp lệ!"}), 400

    # Khởi tạo tham số cấu hình nén dựa trên lựa chọn người dùng
    if compression_level == "high":     # Nén tối đa (Chất lượng thấp hơn)
        dpi = 90
        quality = 45
    elif compression_level == "low":    # Nén nhẹ (Giữ độ nét cao)
        dpi = 220
        quality = 75
    else:                               # Nén tiêu chuẩn (Cân bằng tốt nhất - medium)
        dpi = 150
        quality = 60

    try:
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        pdf_path = os.path.join(session_dir, file.filename)
        file.save(pdf_path)
        
        output_name = f"compressed_{file.filename}"
        
        # Cấu hình chuỗi lọc dữ liệu nén động gửi thẳng vào LibreOffice
        filter_options = f'pdf:writer_pdf_Export:{{"MaxImageResolution":{{"type":"long","value":{dpi}}},"Quality":{{"type":"long","value":{quality}}}}}'
        
        cmd = [
            find_libreoffice(),
            "--headless",
            "--convert-to", filter_options,
            "--outdir", session_dir,
            pdf_path
        ]
        
        # Chạy lệnh biên dịch ép ảnh hệ thống
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45, check=True)
        
        default_out_path = os.path.join(session_dir, file.filename)
        final_out_path = os.path.join(session_dir, output_name)
        
        if os.path.exists(default_out_path):
            os.rename(default_out_path, final_out_path)
        else:
            # Phương án Fallback nếu LibreOffice gặp file mã hóa đặc biệt
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                try: page.compress_content_streams()
                except Exception: pass
                writer.add_page(page)
            with open(final_out_path, "wb") as f:
                writer.write(f)

        download_url = url_for('download_file', folder_id=folder_id, filename=output_name)
        return jsonify({"success": True, "download_url": download_url, "filename": output_name})

    except Exception as e:
        print(f"Lỗi nén đa chế độ: {str(e)}")
        return jsonify({"success": False, "error": "Có lỗi xảy ra trong quá trình tối ưu file!"}), 500
        
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
