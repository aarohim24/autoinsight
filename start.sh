#!/usr/bin/env bash
# start.sh — Launch the FastAPI backend and Next.js frontend for local development.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"

if [ -z "$GROQ_API_KEY" ]; then
  if [ -f "$ROOT/.env" ]; then
    export $(grep -v '^#' "$ROOT/.env" | xargs)
  fi
fi

if [ -z "$GROQ_API_KEY" ]; then
  echo "Error: GROQ_API_KEY is not set. Export it or add it to .env"
  exit 1
fi

echo "Starting FastAPI backend on http://localhost:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Starting Next.js frontend on http://localhost:3000 ..."
cd "$ROOT/frontend-next" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "AutoInsight is running."
echo "  API:      http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
