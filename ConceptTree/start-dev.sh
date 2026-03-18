#!/bin/bash

# 快速启动脚本 - 同时启动前端和后端开发服务器

echo "🚀 启动 PathFinder 开发环境..."

# 检查是否在正确的目录
if [ ! -d "ConceptTree" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 启动后端服务器
echo "📦 启动后端服务器 (端口 8000)..."
cd ConceptTree/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# 等待后端启动
sleep 3

# 启动前端服务器
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

# 等待用户中断
trap "echo ''; echo '🛑 停止服务器...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# 保持脚本运行
wait
