#!/bin/bash
# =============================================================================
# start-dev.sh — One-command launcher for the ConceptTree development environment
# =============================================================================
# WHAT IT DOES
#   Starts backend (FastAPI, port 8000) and frontend (Vite, port 3000) as
#   background processes, then blocks until Ctrl+C — which cleanly kills both.
#
# PREREQUISITES (complete these once before first run)
#   1. Database running:   docker compose up -d
#   2. Backend deps:       cd ConceptTree/backend && pip install -r requirements.txt
#   3. venv created:       cd ConceptTree/backend && python -m venv venv
#   4. Frontend deps:      cd ConceptTree/frontend && npm install
#   5. Env files copied:   cp ConceptTree/backend/.env.example ConceptTree/backend/.env
#                          cp ConceptTree/frontend/.env.example ConceptTree/frontend/.env
#
# USAGE — run from the PARENT directory of ConceptTree:
#   bash start-dev.sh      (or: chmod +x start-dev.sh && ./start-dev.sh)
#
# ENDPOINTS AFTER STARTUP
#   Frontend app  →  http://localhost:3000
#   Backend API   →  http://localhost:8000
#   API docs      →  http://localhost:8000/docs
#
# Primary reader: Developer running the project locally for the first time.
# =============================================================================

echo "🚀 启动 PathFinder 开发环境..."

# Guard: abort early if the ConceptTree directory is not found.
# This script must be run from the parent of ConceptTree/, not from inside it.
if [ ! -d "ConceptTree" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# ---- Backend ----------------------------------------------------------------
# Activate the Python virtual environment, then start FastAPI with auto-reload.
# `--reload` watches source files and restarts on changes — development only.
# `--host 0.0.0.0` makes the server reachable from other devices on the LAN.
echo "📦 启动后端服务器 (端口 8000)..."
cd ConceptTree/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# Give FastAPI time to fully initialise (run migrations, open DB pool)
# before the frontend dev server starts proxying requests to it.
sleep 3

# ---- Frontend ---------------------------------------------------------------
# Vite dev server with HMR (Hot Module Replacement).
# Requests to /api/* are proxied to the backend — see frontend/.env for config.
echo "🎨 启动前端服务器 (端口 3000)..."
cd ConceptTree/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "✅ 开发环境已启动!"
echo ""
echo "📌 前端地址: http://localhost:3000"
echo "📌 后端地址: http://localhost:8000"
echo "📌 API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务器"
echo ""

# ---- Graceful shutdown ------------------------------------------------------
# Trap Ctrl+C (SIGINT): send SIGTERM to both child processes before exiting.
# Without this trap, the uvicorn and Vite processes would keep running as
# orphaned background jobs after the script terminates.
trap "echo ''; echo '🛑 停止服务器...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Block here, keeping the script alive so the trap above can fire on Ctrl+C.
wait
