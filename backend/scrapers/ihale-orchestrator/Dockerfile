FROM python:3.11-slim

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY main.py .

# Environment
ENV PYTHONUNBUFFERED=1
ENV GLOBAL_TIMEOUT=600
ENV SCRAPER_TIMEOUT=300
ENV OCR_TIMEOUT=60
ENV SCRAPER_URL=http://ihale-scraper:8080
ENV OCR_URL=http://ihale-ocr:8080
ENV LLM_GATEWAY_URL=http://llm-gateway:8080

EXPOSE 8080

CMD ["python", "main.py"]
