#!/bin/bash

# Run both backend and frontend for the Agent Builder Platform

trap 'kill 0; exit' SIGINT SIGTERM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Agent Builder Platform..."
echo ""

# Start backend
echo "[backend] Starting FastAPI on http://localhost:8000"
cd "$SCRIPT_DIR"
python3 -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "[frontend] Starting Next.js on http://localhost:3000"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

wait
