# PPT 智能助手 · 部署指南

> 适用于：本地开发 / 新服务器部署 / 迁移到其他机器

---

## 目录

1. [系统要求](#1-系统要求)
2. [克隆项目](#2-克隆项目)
3. [字体文件（必须手动下载）](#3-字体文件必须手动下载)
4. [Python 环境与依赖](#4-python-环境与依赖)
5. [前端依赖](#5-前端依赖)
6. [配置环境变量](#6-配置环境变量)
7. [启动开发服务](#7-启动开发服务)
8. [服务器生产部署](#8-服务器生产部署)
9. [Nginx 反向代理](#9-nginx-反向代理)
10. [验证部署](#10-验证部署)
11. [常见问题](#11-常见问题)

---

## 1. 系统要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| OS | Ubuntu 20.04 / macOS 12 | Ubuntu 22.04 |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB（含字体） | 20 GB |
| Python | 3.11+ | 3.12 |
| Node.js | 18+ | 20 LTS |
| Docker | 20+ | 最新 |

---

## 2. 克隆项目

```bash
git clone https://github.com/wenwenba2020/ppt_agent.git
cd ppt_agent
```

---

## 3. 字体文件（必须手动下载）

字体体积较大，未提交到 Git。**不下载字体 → PPTX 中文显示乱码。**

项目使用 **TTF 格式**（重要：OTF 无法嵌入 PPTX）。

### 推荐字体

| 字体 | 目标路径 | 下载地址 |
|------|----------|----------|
| 阿里巴巴普惠体 3.0 | `fonts/AlibabaPuHuiTi/` | [iconfont](https://www.iconfont.cn/fonts/detail?cnid=pOvFIr086ADR) |
| 思源黑体 TTF | `fonts/SourceHanSans-TTF/` | [GitHub Release](https://github.com/adobe-fonts/source-han-sans/releases) |
| 思源宋体 TTF | `fonts/SourceHanSerif-TTF/` | [GitHub Release](https://github.com/adobe-fonts/source-han-serif/releases) |
| HarmonyOS Sans | `fonts/HarmonyOSSans/` | [华为开发者](https://developer.huawei.com/consumer/cn/design/harmonyos-font/) |
| Inter | `fonts/Inter/` | [Google Fonts](https://fonts.google.com/specimen/Inter) 或 npm: `npx fontsource-cli inter` |

### 下载后验证

```bash
find fonts -name "*.ttf" | wc -l
# 预期：>= 10 个 TTF 文件
```

### 快速下载（Linux 服务器 · 思源黑体）

```bash
mkdir -p fonts/SourceHanSans-TTF
# 只下载简体中文版（SC）
wget -P fonts/SourceHanSans-TTF \
  https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansSC.zip
cd fonts/SourceHanSans-TTF && unzip SourceHanSansSC.zip && cd -
```

---

## 4. Python 环境与依赖

```bash
# 创建虚拟环境
python3.12 -m venv .venv      # 或 python3 -m venv .venv

# 激活
source .venv/bin/activate     # Linux/macOS
# .venv\Scripts\activate      # Windows

# 安装依赖
pip install -r backend/requirements.txt

# 验证
python -c "import fastapi, langgraph, pptx, fontTools, fitz, pyecharts; print('✅ 后端依赖 OK')"
```

---

## 5. 前端依赖

```bash
cd frontend
npm install
cd ..
```

---

## 6. 配置环境变量

```bash
cp .env.example .env   # 若不存在则手动创建
```

编辑 `.env`，填写以下配置：

```bash
# ── LLM API ──────────────────────────────────────────────────────────────────
# OpenRouter（统一 API 网关，支持多模型）
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_API_PROVIDER=openrouter
LLM_API_BASE_URL=https://openrouter.ai/api/v1

# 各智能体绑定的模型
LLM_PLANNER_MODEL=z-ai/glm-5.1          # 规划师（也可换 google/gemini-2.0-flash）
LLM_COPYWRITER_MODEL=deepseek/deepseek-v3.2  # 文案师
LLM_DESIGNER_MODEL=z-ai/glm-5.1         # 设计师
LLM_EFFECTS_MODEL=qwen/qwen3.5-9b       # 效果师

# ── 网页调研 API（二选一或都填）────────────────────────────────────────────
TAVILY_API_KEY=tvly-dev-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EXA_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ── 安全配置 ──────────────────────────────────────────────────────────────────
ADMIN_PASSWORD=your_secure_password_here   # 登录密码（不要用 admin123）
JWT_SECRET=your_random_jwt_secret_here     # 随机长字符串
# 生成 JWT_SECRET: python3 -c "import secrets; print(secrets.token_hex(32))"

# ── 服务配置 ──────────────────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./ppt_agent.db
REDIS_URL=redis://localhost:6379/0

# 前端访问的后端地址（服务器部署时改为公网 IP/域名）
# BACKEND_URL=http://your-server-ip:8000
```

### 获取 API Key

| 服务 | 注册地址 | 用途 |
|------|----------|------|
| OpenRouter | https://openrouter.ai | 所有 LLM 调用（必填） |
| Tavily | https://tavily.com | URL 调研（选填） |
| Exa | https://exa.ai | URL 调研（选填，默认 provider） |

---

## 7. 启动开发服务

需要 **4 个终端**（或使用 tmux）：

```bash
# 终端 1：Redis
docker run -d --name ppt-redis -p 6379:6379 redis:alpine
# 已有容器时：docker start ppt-redis

# 终端 2：后端（--reload 开发模式）
source .venv/bin/activate
uvicorn backend.api.main:app \
  --reload \
  --port 8000 \
  --reload-exclude '.venv/*' \
  --reload-exclude 'projects/*' \
  --reload-exclude '__pycache__/*'

# 终端 3：Celery worker
source .venv/bin/activate
celery -A backend.tasks worker --loglevel=info --pool=solo

# 终端 4：前端
cd frontend && npm run dev
```

访问 http://localhost:5173 · 默认账号 `admin` / `.env` 中的 `ADMIN_PASSWORD`

---

## 8. 服务器生产部署

### 8.1 环境准备

```bash
# Ubuntu 22.04
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip nodejs npm nginx

# 安装 Docker（Redis 用）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER  # 重新登录生效
```

### 8.2 项目安装

```bash
cd /opt
sudo git clone https://github.com/wenwenba2020/ppt_agent.git
sudo chown -R $USER:$USER /opt/ppt_agent
cd /opt/ppt_agent

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && npm install && npm run build && cd ..
```

### 8.3 Systemd 服务（后端）

```ini
# /etc/systemd/system/ppt-backend.service
[Unit]
Description=PPT Agent Backend
After=network.target redis.service

[Service]
User=ubuntu
WorkingDirectory=/opt/ppt_agent
EnvironmentFile=/opt/ppt_agent/.env
ExecStart=/opt/ppt_agent/.venv/bin/uvicorn backend.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8.4 Systemd 服务（Celery）

```ini
# /etc/systemd/system/ppt-celery.service
[Unit]
Description=PPT Agent Celery Worker
After=network.target redis.service

[Service]
User=ubuntu
WorkingDirectory=/opt/ppt_agent
EnvironmentFile=/opt/ppt_agent/.env
ExecStart=/opt/ppt_agent/.venv/bin/celery \
    -A backend.tasks worker \
    --loglevel=info \
    --pool=solo
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable ppt-backend ppt-celery
sudo systemctl start ppt-backend ppt-celery

# 查看状态
sudo systemctl status ppt-backend
sudo journalctl -u ppt-backend -f
```

---

## 9. Nginx 反向代理

```nginx
# /etc/nginx/sites-available/ppt_agent
server {
    listen 80;
    server_name your-domain.com;  # 或公网 IP

    # 前端静态文件
    root /opt/ppt_agent/frontend/dist;
    index index.html;

    # 前端 SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;  # 长时任务超时
    }

    # 项目文件（SVG 预览直链）
    location /project-files/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # SSE 实时推送（禁用缓冲）
    location /api/projects/events {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Accel-Buffering no;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ppt_agent /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 10. 验证部署

```bash
# 后端健康检查
curl http://localhost:8000/health

# 测试登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_admin_password"}'

# 验证字体（后端启动后）
python -c "
from backend.pipeline.font_manager import FontManager
fm = FontManager()
print('可用字体:', fm.list_available_fonts()[:3])
"

# 运行后端测试
.venv/bin/pytest backend/tests/ -q
# 预期：77 passed, 1 pre-existing failure (test_run_global_mode)
```

---

## 11. 常见问题

### Q: PPTX 打开报"一般错误"
**原因**：字体 OTF 格式不支持嵌入。  
**修复**：确保 `fonts/` 下全部是 `.ttf` 文件，删除所有 `.otf`。

### Q: SVG 生成卡住不动
**原因**：Celery worker 未启动，或 Redis 连接失败。  
**修复**：
```bash
redis-cli ping          # 应返回 PONG
celery -A backend.tasks inspect active  # 查看活跃任务
```

### Q: URL 调研失败（Exa/Tavily 返回空）
**原因**：国内站点境外机房无法访问，或 API Key 无效。  
**修复**：检查 `.env` 中的 `EXA_API_KEY`/`TAVILY_API_KEY`，国内站点建议改用境内服务器部署。

### Q: SSE 连接断开（Nginx 后）
**原因**：Nginx 默认缓冲 proxy 响应。  
**修复**：确保 SSE location 配置了 `proxy_buffering off`（见第9节）。

### Q: 前端 401 自动跳转登录失效
**原因**：JWT_SECRET 变更导致旧 token 失效。  
**修复**：浏览器 localStorage 清除 token，重新登录。

### Q: Celery worker 代码改了不生效
**原因**：Celery worker 不热重载。  
**修复**：每次修改 task 代码后 `systemctl restart ppt-celery`。

### Q: 端口被占用
```bash
lsof -i :8000   # 查看占用进程
lsof -i :5173
```

---

## 目录结构说明

```
ppt_agent/
├── backend/
│   ├── agents/          # 五个智能体（规划师/文案师/设计师/效果师/编辑师）
│   ├── api/             # FastAPI 路由
│   ├── graph/           # LangGraph 状态机
│   ├── pipeline/        # SVG/PPTX 处理流水线
│   ├── parsers/         # 文档解析（PDF/DOCX/PPTX）
│   ├── models/          # Pydantic 数据模型
│   ├── storage/         # 文件存储抽象
│   ├── tasks/           # Celery 任务
│   ├── design_templates/ # DESIGN.md 设计风格模板
│   ├── skills/ppt-master/ # SVG→PPTX 转换脚本（只读参考）
│   └── requirements.txt
├── frontend/            # React 19 + Vite + shadcn/ui
├── fonts/               # ⚠️ TTF 字体（未提交 git，需手动下载）
├── projects/            # ⚠️ 用户项目数据（未提交 git）
├── docs/                # 技术文档（agents-spec / data-formats 等）
├── .env                 # ⚠️ 环境变量（未提交 git，需手动创建）
├── dev-setup.sh         # 开发环境检查脚本
└── DEPLOY.md            # 本文件
```

---

*最后更新：2026-04-22 · 对应开发阶段 Phase 3 W12*
