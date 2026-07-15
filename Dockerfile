FROM python:3.10-slim

# Cài đặt LibreOffice, Ghostscript và Font chữ cơ bản cho tiếng Việt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    ghostscript \
    fonts-dejavu \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cấu hình biến môi trường bắt buộc cho LibreOffice hoạt động trong môi trường không giao diện (headless)
ENV HOME=/tmp

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

EXPOSE 7860

# Chạy ứng dụng bằng Flask
CMD ["python", "app.py"]
