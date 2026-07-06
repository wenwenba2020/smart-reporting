# 智能报告引擎 · API 文档

> Base URL: `http://{host}:{port}/api/v1`  
> Content-Type: `application/json`  
> Auth: Bearer Token (JWT) 或 API-KEY Header

## 通用响应格式

```json
{"code": 200, "msg": "ok", "data": { ... }}
```

| code | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

---

## 1. 健康检查

### GET /health
```bash
curl http://localhost:8080/api/v1/health
```
→ `{"code":200, "msg":"ok", "data":{"status":"healthy"}}`

---

## 2. 数据源管理

### GET /datasources/source-types
列出所有已注册的数据源类型。
```bash
curl http://localhost:8080/api/v1/datasources/source-types
```
→ `{"data": ["file_upload","chat_export","enterprise_ppt","rest_api","mcp","database","knowledge_base"]}`

### POST /datasources/upload
上传文件并自动解析。
- FormData: `file` (required), `metadata` (optional JSON string)
```bash
curl -F "file=@sales.csv" http://localhost:8080/api/v1/datasources/upload
```

### GET /datasources
列出所有已上传数据源。

### GET /datasources/{source_id}
获取单个数据源详情（含完整内容）。

### DELETE /datasources/{source_id}
删除数据源。

### POST /datasources/fetch
从非文件数据源拉取数据。
```json
// REST API 源
{"source_type":"rest_api", "config":{"url":"https://api.example.com/data","method":"GET","auth_type":"bearer","auth_token":"xxx","jsonpath_expr":"$"}}

// 数据库源
{"source_type":"database", "config":{"connection_string":"sqlite:///data.db","query":"SELECT * FROM sales","db_type":"sqlite"}}

// MCP 源
{"source_type":"mcp", "config":{"robot_id":12345,"user_id":"user1","tool_prompt":"Get sales data from ERP"}}
```

### POST /datasources/rag/ingest
将已有数据源索引到 RAG 知识库。
```json
{"source_ids": ["src_001", "src_002"]}
```

### POST /datasources/rag/search
语义搜索知识库。
```json
{"query": "华南区Q3销售情况", "top_k": 5}
```

---

## 3. 企业 PPT 库

### POST /enterprise-ppt/upload
上传 PPTX，自动解析为 Slide 索引。
- FormData: `file` (required), `deck_type` (content/template), `name`, `category`, `tags`

### GET /enterprise-ppt/decks
列出所有 PPT Deck。

### GET /enterprise-ppt/decks/{deck_id}
Deck 详情含 Slide 列表。

### DELETE /enterprise-ppt/decks/{deck_id}
删除 Deck。

### GET /enterprise-ppt/slides/search?q=&section_type=
搜索 Slide（关键词匹配标题/摘要/标签）。

### GET /enterprise-ppt/templates
列出模板型 PPT Deck。

---

## 4. 报告模板

### GET /templates?category=
列出所有模板（支持按类别筛选）。
```
→ {"code":200, "data": [{template_id, name, category, description, section_count, is_custom}, ...]}
```

### GET /templates/{template_id}
模板详情（含完整 sections 定义和 system_prompt）。

### POST /templates
创建自定义模板。
```json
{"name":"客户分析报告","category":"分析类","description":"...","sections":[...],"system_prompt":"..."}
```

### PUT /templates/{template_id}
更新自定义模板（仅 custom_ 前缀模板可修改）。

### DELETE /templates/{template_id}
删除自定义模板。

---

## 5. 报告生成

### POST /reports/intent
意图识别 + 模板推荐。
```json
{"user_query": "生成华南区Q3销售周报", "source_ids": ["src_001"]}
```
→ `{intent: {report_type, category, period, scope, key_themes}, recommendations: [{template_id, name, match_score}]}`

### POST /reports/generate (SSE)
流式生成报告（Server-Sent Events）。
```
event: progress  → {"phase":"summarize", "message":"..."}
event: section   → {"key":"s1", "title":"...", "content":"...", "index":1}
event: done      → {"report_id":"xxx", "title":"...", "section_count":6}
```
Request:
```json
{"template_id":"curated_weekly_report", "source_ids":["src_001"], "title":"Q3周报"}
```

### GET /reports/{report_id}
获取已生成报告详情。

### PATCH /reports/{report_id}/section/{section_key}
更新单个章节内容。
```json
{"content": "新的章节内容..."}
```

### POST /reports/{report_id}/chat-command
自然语言编辑指令。
```json
{"command": "在数据概览后面加一段竞品分析", "target_context": ""}
```

### POST /reports/{report_id}/confirm
确认报告（标记所有章节为 confirmed）。

---

## 6. 导出

### POST /export/{report_id}/export
多格式导出。
```json
{"formats": ["docx", "pdf", "html_mindmap", "pptx"]}
```
→ `[{file_path, file_size, format, download_url}, ...]`

### GET /export/download/{file_name}
下载导出文件。

---

## 7. WorkoPilot 桥接

### POST /workopilot/run
WorkoPilot AI 服务桥接端点。
```json
// 意图识别
{"serviceCode": "report_intent", "inputs": {"user_query": "...", "source_ids": [...]}}

// 报告生成
{"serviceCode": "report_generate", "inputs": {"template_id": "...", "source_ids": [...], "title": "..."}}
```

---

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SERVER_PORT` | 8080 | API 服务端口 |
| `OPENROUTER_API_KEY` | — | LLM API Key（必填） |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | LLM 网关 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/smart_reporting.db` | 数据库 |
| `WORKOPILOT_BASE_URL` | `https://agent.workopilot.com/net-api` | 喔壳平台 |
| `WORKOPILOT_API_KEY` | — | 喔壳 API Key |
| `JWT_SECRET` | 自动生成 | JWT 签名密钥 |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery 任务队列 |
