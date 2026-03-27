FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY sample_data/ sample_data/
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
COPY start_prod.sh /app/start_prod.sh
RUN chmod +x /app/start_prod.sh
CMD ["/app/start_prod.sh"]
