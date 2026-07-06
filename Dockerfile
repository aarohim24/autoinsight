# ── Stage 1: Backend ──────────────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY sample_data/ sample_data/

COPY start_prod.sh /app/start_prod.sh
RUN chmod +x /app/start_prod.sh

CMD ["/app/start_prod.sh"]


# ── Stage 2: Frontend ─────────────────────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /app

COPY frontend-next/package*.json ./
RUN npm ci --prefer-offline

COPY frontend-next/ .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
