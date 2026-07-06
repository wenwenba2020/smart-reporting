# 智能报告引擎 · MCP 服务化评估

## 结论：高度可行 ✅

智能报告引擎的架构天然适合封装为 MCP (Model Context Protocol) 服务。

## MCP 是什么

MCP 是 Anthropic 提出的开放协议，让 AI 模型（如 Claude）可以调用外部工具。一个 MCP Server 暴露若干"工具"（tool），每个工具有名称、描述、JSON Schema 输入参数、执行函数。

AI 模型在需要时自动选择并调用合适的工具，获取结果后继续推理。

## 适合封装为 MCP 工具的核心能力

| MCP Tool | 对应引擎功能 | 输入 | 输出 |
|----------|-------------|------|------|
| `report_intent_recognize` | IntentRecognizer | user_query, source_ids[] | 意图分析 + 模板推荐列表 |
| `report_generate` | SectionFiller + Summarizer | template_id, source_ids[], title | StructuredReport (SSE→完整) |
| `report_export` | ReportOutputEngine | report_id, formats[] | 导出文件 URL 列表 |
| `datasource_list_types` | DataSourceRegistry | — | 7种数据源类型 |
| `datasource_upload` | FileUploadAdapter | file_path | SourceDocument 摘要 |
| `datasource_fetch` | RestApiSource / DatabaseSource | source_type, config | SourceDocument |
| `template_list` | TemplateStore | category? | 24个模板列表 |
| `template_get` | TemplateStore | template_id | 模板详情+sections |
| `rag_search` | RAGKnowledgeBase | query, top_k | 语义搜索结果 |
| `rag_ingest` | RAGKnowledgeBase | source_ids[] | 索引状态 |

## 架构

```
外部 AI Agent (Claude/GPT/...)
        │ MCP Protocol (stdio 或 HTTP)
        ▼
┌─────────────────────────────┐
│     MCP Server (Python)      │
│  ┌─────────────────────────┐│
│  │ Tool: report_intent      ││
│  │ Tool: report_generate    ││
│  │ Tool: report_export      ││
│  │ Tool: datasource_*       ││
│  │ Tool: template_*         ││
│  │ Tool: rag_*              ││
│  └──────────┬──────────────┘│
│             │ 直接调用        │
│             ▼                │
│  ┌─────────────────────────┐│
│  │ Smart Reporting Engine   ││
│  │ (FastAPI backend core)  ││
│  └─────────────────────────┘│
└─────────────────────────────┘
```

## 传输方式

### stdio（推荐用于本地 AI IDE）
- Claude Code / Cursor 等通过 stdin/stdout 与 MCP Server 通信
- 零网络配置，开箱即用
- 适合本地开发调试

### HTTP（推荐用于远程/平台集成）
- 通过 HTTP + SSE 暴露 MCP 端点
- 可部署在服务器上供远程调用
- 适合喔壳平台集成

## 与喔壳平台的互补关系

喔壳的 MCP 是"企业数据连接器"（连 ERP/CRM），智能报告的 MCP 是"报告能力连接器"（生成报告）。

两者互补：
- 喔壳 MCP → 从企业系统拉取数据
- 智能报告 MCP → 将数据转化为结构化报告
- 可串联：AI 先通过喔壳 MCP 获取数据 → 再通过智能报告 MCP 生成报告 → 导出
