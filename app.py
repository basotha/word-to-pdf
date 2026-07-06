from flask import Flask, render_template, request, jsonify, send_file, url_for
import os
import subprocess
import uuid

app = Flask(__name__)

# Thư mục lưu file tạm thời trên server Render
UPLOAD_FOLDER = "/tmp/flask_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_libreoffice():
    possible_paths = ["/usr/bin/libreoffice", "/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice"]
    for path in possible_paths:
        if os.path.exists(path): return path
    return "libreoffice"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# Cổng xử lý chuyển đổi (Trả về dữ liệu JSON chứa link tải thay vì tải trực tiếp)
@app.route("/convert", methods=["POST"])
def convert():
    if "word_file" not in request.files:
        return jsonify({"success": False, "error": "Không tìm thấy file!"}), 400
        
    file = request.files["word_file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Tên file trống!"}), 400

    if file and file.filename.endswith(".docx"):
        # Tạo thư mục độc nhất cho lượt tải này
        folder_id = uuid.uuid4().hex
        session_dir = os.path.join(UPLOAD_FOLDER, folder_id)
        os.makedirs(session_dir, exist_ok=True)
        
        word_path = os.path.join(session_dir, file.filename)
        file.save(word_path)
        
        # Chuyển đổi bằng LibreOffice
        libreoffice_bin = find_libreoffice()
        cmd = [libreoffice_bin, "--headless", "--convert-to", "pdf", "--outdir", session_dir, word_path]
        subprocess.run(cmd, check=True)
        
        pdf_name = file.filename.replace(".docx", ".pdf")
        
        # Trả về đường dẫn link để JavaScript kích hoạt nút bấm
        download_url = url_for('download_file', folder_id=folder_id, filename=pdf_name)
        return jsonify({"success": True, "download_url": download_url, "filename": pdf_name})

    return jsonify({"success": False, "error": "Định dạng file không hợp lệ!"}), 400

# Cổng phục vụ nút bấm tải file về
@app.route("/download/<folder_id>/<filename>", methods=["GET"])
def download_file(folder_id, filename):
    file_path = os.path.join(UPLOAD_FOLDER, folder_id, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    return "File không tồn tại hoặc đã bị xóa!", 404
# Đường dẫn đến thư mục chứa font
FONT_DIR = os.path.join('static', 'fonts')

@app.route("/fonts", methods=["GET"])
def fonts_page():
    font_list = []
    
    # Tự động quét thư mục static/fonts nếu nó tồn tại
    if os.path.exists(FONT_DIR):
        for filename in os.listdir(FONT_DIR):
            if filename.lower().endswith(('.ttf', '.woff', '.woff2', '.otf')):
                # Lấy tên font bỏ phần đuôi mở rộng để làm hiển thị (Ví dụ: UTM-Alessio)
                font_name = os.path.splitext(filename)[0]
                font_list.append({
                    "name": font_name,
                    "filename": filename
                })
                
    # Sắp xếp tên font theo thứ tự bảng chữ cái A-Z cho đẹp
    font_list.sort(key=lambda x: x["name"])
    
    return render_template("fonts.html", fonts=font_list)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
