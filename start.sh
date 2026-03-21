#!/usr/bin/env bash
# start.sh – Launch both the FastAPI backend and Streamlit frontend.

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"

echo "🚀 Starting AutoInsight API on http://localhost:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "🎨 Starting Streamlit frontend on http://localhost:8501 ..."
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "✦ AutoInsight is running!"
echo "  API:      http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
echo "  Frontend: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
