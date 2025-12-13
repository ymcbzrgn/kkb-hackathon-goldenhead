FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# System dependencies for OCR and PDF
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers
RUN playwright install chromium

# Application code
COPY main.py .

# Debug directory
RUN mkdir -p /tmp/tsg_debug

# Environment
ENV PYTHONUNBUFFERED=1
ENV PAGE_TIMEOUT=30000
ENV MAX_RETRIES=3
ENV TSG_EMAIL=""
ENV TSG_PASSWORD=""
ENV LLM_GATEWAY_URL="http://llm-gateway.news-agent:8080"

EXPOSE 8080

CMD ["python", "main.py"]
