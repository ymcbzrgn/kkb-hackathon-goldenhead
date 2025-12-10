FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Environment
ENV KKB_API_URL=https://mia.csp.kloudeks.com/api/v1
ENV MAX_CONCURRENT_REQUESTS=10
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
