"""智能填报引擎 — 多数据源检索 → LLM 汇总 → 结构化 MD + 报表 JSON"""
import json
from dataclasses import dataclass, field

from backend.agents.llm_client import chat
from backend.agents.json_utils import extract_json_object
from backend.data_source.base import registry

MODEL = "deepseek/deepseek-v3.2"

SMART_FILL_SYSTEM = """你是企业智能报告的数据汇总专家。根据多数据源检索结果，生成两份输出：

## 输出 1: structured_markdown（完整结构化 Markdown 文档）
- 按章节组织：封面信息 → 摘要概述 → 详细分析 → 数据附录
- 所有数据需注明来源
- 使用 Markdown 表格展示对比数据
- 不超过 5000 字

## 输出 2: report_json（报表生成用的 JSON）
- 遵循指定的 JSON schema
- 所有数据字段从知识库检索结果中提取
- 缺失数据用 null，不编造

返回 JSON：
{
  "structured_markdown": "完整的 Markdown 文档...",
  "report_json": { ... }
}"""


@dataclass
class SmartFillResult:
    structured_markdown: str
    report_json: dict
    source_references: list[dict] = field(default_factory=list)


async def run_smart_fill(
    query: str,
    scenario_type: str | None = None,
    selected_sources: list[str] | None = None,
    user_id: str = "",
    report_type: str = "ppt",
) -> SmartFillResult:
    """执行智能填报流程: 检索所有数据源 → LLM 汇总 → 返回结构化内容"""

    all_sources = registry.list_all()
    if selected_sources:
        all_sources = [s for s in all_sources if s.source_type in selected_sources]

    all_docs: list[dict] = []
    source_refs: list[dict] = []
    source_context = ""

    for plugin in all_sources:
        try:
            docs = await plugin.search(
                query, top_k=5, user_id=user_id, scenario_type=scenario_type,
            )
        except Exception:
            continue

        if docs:
            source_refs.append({
                "source_type": plugin.source_type,
                "source_name": plugin.source_name,
                "doc_count": len(docs),
            })
            source_context += f"\n## 数据源: {plugin.source_name}\n"
            for d in docs:
                source_context += f"\n### {d.title}\n{d.content}\n"
                all_docs.append({
                    "source_type": d.source_type, "source_name": d.source_name,
                    "title": d.title, "content": d.content,
                })

    if not all_docs:
        return SmartFillResult(source_references=source_refs)

    json_schema = _get_report_schema(report_type, scenario_type)

    user_prompt = f"""查询主题: {query}
报告类型: {report_type}
场景: {scenario_type or "通用"}

## 数据源检索结果
{source_context[:8000]}

## 报表 JSON Schema
{json.dumps(json_schema, ensure_ascii=False, indent=2)}

请根据以上数据源内容，生成结构化 Markdown 文档和符合 schema 的报表 JSON。"""

    try:
        resp = chat(
            MODEL,
            messages=[
                {"role": "system", "content": SMART_FILL_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        result = extract_json_object(resp) or {}
    except Exception:
        return SmartFillResult(
            structured_markdown=source_context,
            source_references=source_refs,
        )

    return SmartFillResult(
        structured_markdown=result.get("structured_markdown", source_context),
        report_json=result.get("report_json", {}),
        source_references=source_refs,
    )


def _get_report_schema(report_type: str, scenario_type: str | None) -> dict:
    if report_type == "ppt":
        return {
            "title": "string (≤15字)",
            "subtitle": "string",
            "slides": [{
                "slide_id": "string", "layout": "string",
                "title": "string", "points": [{"heading": "string", "body": "string"}],
                "chart": {"type": "string", "data": [], "caption": "string"},
                "notes_speaker": "string", "source_ref": "string",
            }],
        }
    elif report_type == "docx":
        return {
            "title": "string", "abstract": "string",
            "sections": [{
                "heading": "string", "body": "string",
                "tables": [{"caption": "string", "headers": ["string"], "rows": [["string"]]}],
                "source_ref": "string",
            }],
        }
    else:
        return {
            "title": "string",
            "sections": [{"heading": "string", "content": "string"}],
            "tables": [{"caption": "string", "data": []}],
        }
