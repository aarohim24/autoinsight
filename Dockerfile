# ── Stage 1: Frontend (for Docker Compose / local dev only) ──────────────────
# Vercel handles the production frontend deployment.
# This stage is only used locally via docker-compose.
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


# ── Stage 2: Backend (default stage — used by Render) ────────────────────────
# Render builds this Dockerfile and runs the last stage.
# The backend serves the FastAPI app on $PORT.
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
