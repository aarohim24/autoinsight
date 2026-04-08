FROM python:3.12-slim
WORKDIR /app

# Ensure clean state
RUN find /app -name "*.pyc" -delete
RUN find /app -name "__pycache__" -type d -delete

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    find /usr/local/lib/python3.12 -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12 -name "__pycache__" -type d -delete

COPY backend/ backend/
COPY sample_data/ sample_data/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

COPY start_prod.sh /app/start_prod.sh
RUN chmod +x /app/start_prod.sh
CMD ["/app/start_prod.sh"]
