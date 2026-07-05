#!/bin/bash
# PPT 智能助手 · 开发环境启动脚本
# 用法: bash dev-setup.sh

set -e

PROJECT_DIR="/Users/wenwenba2020/cc_workspace/ppt_agent"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

cd "$PROJECT_DIR"

echo "======================================"
echo " PPT 智能助手 · 开发环境检查"
echo "======================================"

# 检查 .env 文件
if [ ! -f ".env" ]; then
  echo "❌ .env 文件不存在，请先复制 .env.example 并填写配置"
  exit 1
fi

# 检查 ANTHROPIC_API_KEY
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
  echo "⚠️  .env 中 ANTHROPIC_API_KEY 未填写"
fi

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
  echo "❌ 虚拟环境不存在，请先运行: python3 -m venv .venv"
  exit 1
fi

echo "✅ Python 虚拟环境: $($VENV_PYTHON --version)"

# 检查关键依赖
$VENV_PYTHON -c "import fastapi, langgraph, pptx, fontTools, fitz" 2>/dev/null \
  && echo "✅ 后端依赖完整" \
  || echo "❌ 后端依赖缺失，请运行: .venv/bin/pip install -r backend/requirements.txt"

# 检查字体文件
FONT_COUNT=$(find fonts -name "*.ttf" 2>/dev/null | wc -l | tr -d ' ')
if [ "$FONT_COUNT" -eq "0" ]; then
  echo "⚠️  fonts/ 目录中没有 TTF 字体文件"
  echo "   请下载阿里巴巴普惠体 TTF 版本到 fonts/AlibabaPuHuiTi/"
  echo "   下载地址: https://www.iconfont.cn/fonts/detail?cnid=pOvFIr086ADR"
else
  echo "✅ 字体文件: $FONT_COUNT 个 TTF 文件"
fi

# 启动 Redis
echo ""
echo "======================================"
echo " 启动 Redis"
echo "======================================"

if command -v docker &> /dev/null; then
  if docker ps | grep -q ppt-redis; then
    echo "✅ Redis 已在运行"
  elif docker ps -a | grep -q ppt-redis; then
    docker start ppt-redis
    echo "✅ Redis 已重新启动"
  else
    docker run -d --name ppt-redis -p 6379:6379 redis:alpine
    echo "✅ Redis 已启动（新建容器）"
  fi
  
  # 等待 Redis 就绪
  sleep 1
  if docker exec ppt-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis 连接正常"
  else
    echo "⚠️  Redis 启动了但连接失败，请检查"
  fi
else
  echo "⚠️  Docker 未安装，请手动启动 Redis"
  echo "   安装 Docker Desktop: https://www.docker.com/products/docker-desktop/"
fi

# 检查 ppt-master scripts 依赖
echo ""
echo "======================================"
echo " 检查 ppt-master 依赖"
echo "======================================"

if [ -f "backend/skills/ppt-master/scripts/svg_to_pptx.py" ]; then
  $VENV_PYTHON backend/skills/ppt-master/scripts/svg_to_pptx.py --help > /dev/null 2>&1 \
    && echo "✅ ppt-master scripts 依赖完整" \
    || echo "⚠️  ppt-master scripts 有缺失依赖，请查看 docs/todo.md P0-1"
else
  echo "⚠️  ppt-master scripts 目录不存在"
fi

echo ""
echo "======================================"
echo " 环境就绪，启动命令"
echo "======================================"
echo ""
echo "后端（新终端）:"
echo "  source .venv/bin/activate"
echo "  uvicorn backend.api.main:app --reload --port 8000"
echo ""
echo "前端（新终端）:"
echo "  cd frontend && npm run dev"
echo ""
echo "Celery worker（新终端）:"
echo "  source .venv/bin/activate"
echo "  celery -A backend.tasks worker --loglevel=info"
echo ""
echo "健康检查:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:5173"
echo ""
