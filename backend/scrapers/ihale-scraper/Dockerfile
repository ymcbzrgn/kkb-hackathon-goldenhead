FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers
RUN playwright install chromium

# Application code
COPY main.py .

# Environment
ENV PYTHONUNBUFFERED=1
ENV MAX_DAYS=90
ENV REQUEST_DELAY=1.5
ENV PAGE_TIMEOUT=30000

EXPOSE 8080

CMD ["python", "main.py"]
