FROM python:3.11-slim

WORKDIR /app

# System dependencies for Tesseract and pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY main.py .

# Environment
ENV PYTHONUNBUFFERED=1
ENV OCR_DPI=300
ENV MIN_TEXT_THRESHOLD=200
ENV MAX_WORKERS=4

EXPOSE 8080

CMD ["python", "main.py"]
