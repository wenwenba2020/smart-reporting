"""Smart Reporting MCP Server — expose report engine as MCP tools.

Usage:
    # stdio mode (for Claude Code/Cursor)
    python backend/mcp_server.py

    # or with uv run (recommended in Claude Code config)
    .venv/bin/python backend/mcp_server.py

Configure in Claude Code (.mcp.json):
{
    "mcpServers": {
        "smart-reporting": {
            "command": ".venv/bin/python",
            "args": ["backend/mcp_server.py"],
            "cwd": "/path/to/smart_reporting"
        }
    }
}
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from backend.core.templates import template_store
from backend.core.engine.intent import IntentRecognizer
from backend.core.engine.template_matcher import TemplateMatcher
from backend.core.output import output_engine
from backend.core.engine.summarizer import SourceSummarizer
from backend.core.engine.filler import SectionFiller
from backend.core.datasource.base import registry
from backend.core.models import SourceDocument

server = Server("smart-reporting")

# In-memory store (shared with API server in same process)
_source_store: dict[str, SourceDocument] = {}
_reports: dict = {}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="report_template_list",
            description="列出所有可用的报告模板（24个），包含名称、类别、描述、章节数。可用于让用户选择模板。",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "按类别筛选：指标类/进度类/分析类/总结类/评估类"}
                },
            },
        ),
        Tool(
            name="report_template_detail",
            description="获取指定模板的完整详情，包含所有章节定义和 System Prompt。",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "模板ID，如 curated_weekly_report"}
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="report_intent_recognize",
            description="分析用户的报告需求，识别报告类型、周期、范围等意图，并推荐最匹配的模板。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_query": {"type": "string", "description": "用户的报告需求描述"},
                    "source_ids": {"type": "array", "items": {"type": "string"}, "description": "已上传数据源的ID列表"},
                },
                "required": ["user_query"],
            },
        ),
        Tool(
            name="report_generate",
            description="根据模板和数据源生成结构化报告。返回报告ID和各章节内容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "模板ID"},
                    "source_ids": {"type": "array", "items": {"type": "string"}, "description": "数据源ID列表"},
                    "title": {"type": "string", "description": "报告标题"},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="report_export",
            description="将已生成的报告导出为指定格式。支持 docx/pdf/html_mindmap/pptx。",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {"type": "string", "description": "报告ID"},
                    "formats": {"type": "array", "items": {"type": "string"}, "description": "导出格式列表"},
                },
                "required": ["report_id", "formats"],
            },
        ),
        Tool(
            name="datasource_types",
            description="列出所有支持的数据源类型（7种：文件上传/聊天记录/企业PPT/REST API/MCP/数据库/RAG知识库）。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="rag_search",
            description="在已索引的知识库中进行语义搜索，返回相关文档片段。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "top_k": {"type": "integer", "description": "返回结果数量，默认5"},
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    result = {}

    if name == "report_template_list":
        category = arguments.get("category", "")
        if category:
            templates = template_store.list_by_category(category)
        else:
            templates = template_store.list_all()
        result = {
            "total": len(templates),
            "templates": [{"template_id": t.template_id, "name": t.name, "category": t.category, "description": t.description, "section_count": len(t.sections)} for t in templates],
        }

    elif name == "report_template_detail":
        tmpl = template_store.get(arguments["template_id"])
        if not tmpl:
            return [TextContent(type="text", text=f"错误: 模板 {arguments['template_id']} 不存在")]
        result = {
            "template_id": tmpl.template_id, "name": tmpl.name, "category": tmpl.category,
            "description": tmpl.description, "system_prompt": tmpl.system_prompt,
            "sections": [{"key": s.key, "title": s.title, "required": s.required, "description": s.description, "source": s.source} for s in tmpl.sections],
        }

    elif name == "report_intent_recognize":
        recognizer = IntentRecognizer()
        matcher = TemplateMatcher()
        sources = [_source_store.get(sid) for sid in arguments.get("source_ids", []) if _source_store.get(sid)]
        try:
            intent = await recognizer.recognize(arguments["user_query"], sources)
        except Exception:
            from backend.core.models import ReportIntent
            intent = ReportIntent(report_type="general", category="进度类")
        recommendations = matcher.match(intent)
        result = {
            "intent": {"report_type": intent.report_type, "category": intent.category, "period": intent.period, "scope": intent.scope, "key_themes": intent.key_themes},
            "recommendations": [{"template_id": r.template_id, "name": r.name, "match_score": r.match_score, "match_reason": r.match_reason} for r in recommendations[:5]],
        }

    elif name == "report_generate":
        template_id = arguments["template_id"]
        tmpl = template_store.get(template_id)
        if not tmpl:
            return [TextContent(type="text", text=f"错误: 模板 {template_id} 不存在")]
        source_ids = arguments.get("source_ids", [])
        sources = [_source_store.get(sid) for sid in source_ids if _source_store.get(sid)]
        summarizer = SourceSummarizer()
        filler = SectionFiller()
        merged = await summarizer.summarize(sources)
        title = arguments.get("title", tmpl.name)
        report = await filler.fill(tmpl, merged, sources, title)
        import uuid
        report_id = str(uuid.uuid4())
        report.report_id = report_id
        _reports[report_id] = report
        result = {
            "report_id": report_id, "title": title,
            "sections": [{"key": s.key, "title": s.title, "content": s.content[:500], "confidence": s.confidence} for s in report.sections],
            "section_count": len(report.sections),
        }

    elif name == "report_export":
        report_id = arguments["report_id"]
        report = _reports.get(report_id)
        if not report:
            return [TextContent(type="text", text=f"错误: 报告 {report_id} 不存在")]
        formats = arguments.get("formats", ["docx"])
        results = await output_engine.export(report, formats)
        result = {
            "report_id": report_id,
            "exports": [{"format": r.format, "file_path": r.file_path, "file_size": r.file_size_bytes, "download_url": r.download_url} for r in results],
        }

    elif name == "datasource_types":
        result = {"types": registry.list_types(), "descriptions": {"file_upload": "文件上传(Word/PDF/Excel/TXT)", "chat_export": "聊天记录(微信/企业微信/钉钉)", "enterprise_ppt": "企业PPT库(内容复用+模板)", "rest_api": "REST API端点", "mcp": "喔壳MCP工具", "database": "数据库直连(SQLite/MySQL/PG)", "knowledge_base": "RAG知识库(语义搜索)"}}

    elif name == "rag_search":
        from backend.core.datasource.rag_source import rag_kb
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        doc = await rag_kb.search(query, top_k)
        result = {"query": query, "content": doc.content[:2000], "title": doc.title, "results": doc.metadata.get("results", 0)}

    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ))


if __name__ == "__main__":
    asyncio.run(main())
