"""规划师智能体 — 三阶段交互式规划 + 路由/诊断
模型: GLM-5.1 (Pro/zai-org/GLM-5.1) via SiliconFlow

Stage 1: 逐题确认 PPT 定位（5 个问题依次提问）
Stage 2: 生成大纲骨架
Stage 3: 完善每页内容详情

⚠️ 诊断模式只读 OUTLINE.md 结构摘要，绝不读 svg_output/
"""
import json
import logging
import re
from pathlib import Path

from sqlalchemy import select

from backend.agents.json_utils import extract_json_array, extract_json_object
from backend.agents.llm_client import chat
from backend.config import settings
from backend.models.outline import OutlineDoc, load_outline
from backend.storage.file_manager import ProjectStorage

logger = logging.getLogger(__name__)
MODEL = settings.LLM_PLANNER_MODEL


# ---------- Knowledge base & case library retrieval ----------

async def _retrieve_knowledge_context(
    user_message: str,
    user_id: str,
) -> str:
    """从知识库检索相关内容作为上下文注入。"""
    from backend.models.knowledge import KnowledgeEntry, KnowledgeBase
    from backend.models.database import async_session
    from backend.parsers.knowledge_ingest import compute_embedding, cosine_similarity

    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeEntry).join(KnowledgeBase).where(
                KnowledgeBase.user_id == user_id,
                KnowledgeEntry.embedding.isnot(None),
            )
        )
        entries = list(result.scalars().all())

    if not entries:
        return ""

    try:
        query_emb = compute_embedding(user_message)
        scored = [(cosine_similarity(query_emb, e.embedding), e) for e in entries if e.embedding]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [e for s, e in scored[:5] if s > 0.3]
    except Exception:
        return ""

    if not top:
        return ""

    lines = ["\n## 知识库参考资料\n"]
    for i, entry in enumerate(top, 1):
        lines.append(f"### 参考{i}: {entry.title}")
        lines.append(f"来源: {entry.source_name}")
        lines.append(entry.content[:600])
        lines.append("")
    return "\n".join(lines)


async def _match_case_context(
    user_message: str,
    scenario_type: str | None,
    user_id: str,
) -> str:
    """从案例库匹配相关历史案例。"""
    from backend.models.slide_library import SlideLibrary
    from backend.models.database import async_session

    async with async_session() as db:
        query = select(SlideLibrary).where(
            SlideLibrary.user_id == user_id,
            SlideLibrary.is_excellent == True,
        )
        if scenario_type:
            query = query.where(SlideLibrary.scenario_type == scenario_type)

        result = await db.execute(query)
        cases = list(result.scalars().all())

    if not cases:
        return ""

    lines = ["\n## 历史案例参考\n"]
    for case in cases[:3]:
        lines.append(f"- **{case.name}** ({case.slide_count}页)")
        if case.tags:
            lines.append(f"  标签: {', '.join(case.tags)}")
    return "\n".join(lines)


def _build_scenario_prompt_section(scenario: dict | None) -> str:
    """构建场景框架 prompt 片段。"""
    if not scenario:
        return ""

    framework = scenario.get("slide_framework", [])
    if not framework:
        return ""

    framework_str = "\n".join(
        f"  {f.get('seq', i+1)}. [{f.get('role', '内容页')}] layout={f.get('layout', 'title-content')} → {f.get('prompt_hint', '')}"
        for i, f in enumerate(framework)
    )

    section = f"""
## 场景框架（必须遵循）
- 场景: {scenario.get('name', '')}
- 说明: {scenario.get('description', '')}
- 页面结构:
{framework_str}

## 数据源指引
{scenario.get('data_source_hints', '请从知识库提取相关数据')}

## 话术参考
开场: {scenario.get('talk_track_templates', {}).get('opening', '')}
结尾: {scenario.get('talk_track_templates', {}).get('closing', '')}
"""
    return section


# ---------- Project source loading ----------

def load_project_sources(project_id: str) -> str:
    """读取项目 sources/ 目录下所有 .md 文件，合并为参考资料字符串。"""
    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id)
    sources_dir = project_dir / "sources"
    if not sources_dir.exists():
        return ""

    parts: list[str] = []
    for f in sorted(sources_dir.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            if content.strip():
                parts.append(f"### {f.name}\n\n{content}")
        except Exception as e:
            logger.warning(f"Failed to read source file {f}: {e}")

    return "\n\n---\n\n".join(parts)

# ---------- Stage 1: Step-by-step positioning questions ----------

POSITIONING_QUESTIONS = [
    {
        "key": "audience",
        "question": "这份 PPT 给谁看？",
        "options": ["企业决策者/高管", "潜在客户/合作伙伴", "投资人/融资对象", "内部团队/员工"],
    },
    {
        "key": "scenario",
        "question": "在什么场合使用？",
        "options": ["产品推介/销售", "路演/展会", "内部汇报/培训", "品牌宣传/公关"],
    },
    {
        "key": "goal",
        "question": "想达成什么核心目标？",
        "options": ["促成采购/签约", "获取融资/投资", "品牌认知/传播", "信息传达/教育"],
    },
    {
        "key": "style",
        "question": "偏好什么视觉风格？",
        "options": ["科技商务风", "简约专业风", "活泼创意风", "稳重大气风"],
    },
    {
        "key": "pages",
        "question": "PPT 大概需要多少页？",
        "options": ["精简版（6-8 页）", "标准版（10-12 页）", "详尽版（15-20 页）"],
    },
]

SMART_OPTIONS_SYSTEM = """你是 PPT 规划师。根据用户需求和调研资料，为以下问题生成 4 个更精准的建议选项。

问题：{question}
用户原始需求：{user_message}
参考资料摘要：{context_summary}

要求：
1. 选项应基于调研到的真实信息
2. 每个选项简洁有力（10 字以内）
3. 第一个选项是你最推荐的

返回 JSON：{"options": ["选项1", "选项2", "选项3", "选项4"], "recommendation": "推荐理由（一句话）"}"""


def generate_smart_options(question: dict, user_message: str, context: str) -> dict:
    """Generate context-aware options for a positioning question."""
    if not context:
        # No context, use default options
        return {"options": question["options"], "recommendation": ""}

    prompt = SMART_OPTIONS_SYSTEM.replace("{question}", question["question"]) \
        .replace("{user_message}", user_message) \
        .replace("{context_summary}", context[:2000])

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请生成选项"},
    ]

    try:
        resp = chat(MODEL, messages, temperature=0.5, max_tokens=1024)
        data = extract_json_object(resp)
        if data and "options" in data:
            return data
    except Exception:
        pass

    return {"options": question["options"], "recommendation": ""}


def get_positioning_question(step: int, user_message: str = "", context: str = "") -> dict:
    """Get the next positioning question with smart options."""
    if step >= len(POSITIONING_QUESTIONS):
        return {"done": True}

    q = POSITIONING_QUESTIONS[step]

    # For the first question, generate smart options based on context
    if context and step == 0:
        smart = generate_smart_options(q, user_message, context)
        return {
            "step": step,
            "total": len(POSITIONING_QUESTIONS),
            "key": q["key"],
            "question": q["question"],
            "options": smart.get("options", q["options"]),
            "recommendation": smart.get("recommendation", ""),
        }

    return {
        "step": step,
        "total": len(POSITIONING_QUESTIONS),
        "key": q["key"],
        "question": q["question"],
        "options": q["options"],
    }


# ---------- URL Research ----------

def _normalize_url(url: str) -> str:
    """补齐协议头；Tavily extract 对无 scheme 的 URL 会直接失败。"""
    u = url.strip()
    if not u:
        return u
    if not re.match(r'^https?://', u, re.IGNORECASE):
        u = 'https://' + u
    return u


def _deep_fetch(client, url: str, limit: int = 10) -> tuple[str | None, str | None, str | None]:
    """深度抓取：先试 Tavily crawl；失败降级 map → 选前 N 个 URL → extract。

    返回 (title, content, error) —— content 非 None 即成功。
    """
    from urllib.parse import urlparse
    domain = urlparse(url).netloc or url
    parts: list[str] = []
    strategy = ""

    # 策略 A: crawl
    try:
        r = client.crawl(
            url,
            limit=limit,
            max_depth=2,
            extract_depth="basic",
            format="markdown",
            timeout=90.0,
        )
        for item in r.get("results") or []:
            raw = item.get("raw_content") or item.get("content", "")
            if raw:
                page_url = item.get("url", "")
                page_title = item.get("title") or page_url
                parts.append(f"## [{page_title}]({page_url})\n\n{raw[:8000]}")
        if parts:
            strategy = f"crawl {len(parts)} 页"
    except Exception as crawl_err:
        # 策略 B: map + extract 降级
        try:
            m = client.map(url, max_depth=2, limit=limit)
            mapped = m.get("results") or []
            urls_to_extract = [x for x in mapped if isinstance(x, str)][:limit]
            if urls_to_extract:
                ext = client.extract(urls=urls_to_extract, format="markdown", extract_depth="basic")
                for item in ext.get("results") or []:
                    raw = item.get("raw_content") or item.get("content", "")
                    if raw:
                        page_url = item.get("url", "")
                        parts.append(f"## [{page_url}]({page_url})\n\n{raw[:8000]}")
                if parts:
                    strategy = f"map+extract {len(parts)} 页"
        except Exception as map_err:
            return None, None, f"crawl 失败（{crawl_err}）；map 降级也失败（{map_err}）"

    if not parts:
        return None, None, "深度抓取未获取到任何内容"

    return f"{domain} 深度抓取（{strategy}）", "\n\n---\n\n".join(parts)[:60000], None


def _fetch_via_exa(urls: list[tuple[str, str]], deep: bool) -> list[dict]:
    """用 Exa SDK 抓取 URL 内容。

    - deep=False：get_contents(url, text=True, livecrawl='always')
    - deep=True：get_contents(url, text=True, livecrawl='always', subpages=10)
      Exa 会自动抓该 URL 的站内子页，合并到一条 result 的 subpages 列表
    """
    exa_key = getattr(settings, 'EXA_API_KEY', '')
    if not exa_key:
        return [{"url": orig, "error": "EXA_API_KEY 未配置"} for orig, _ in urls]

    try:
        from exa_py import Exa
        exa = Exa(api_key=exa_key)
    except Exception as e:
        return [{"url": orig, "error": f"Exa 加载失败: {e}"} for orig, _ in urls]

    from urllib.parse import urlparse
    results: list[dict] = []
    for orig, url in urls:
        try:
            kwargs = {"text": True, "livecrawl": "always"}
            if deep:
                kwargs["subpages"] = 10
            r = exa.get_contents([url], **kwargs)
            items = getattr(r, "results", []) or []
            if not items:
                # 诊断信息：Exa 的 statuses 列表会给出 url 级失败原因
                statuses = getattr(r, "statuses", []) or []
                reason_parts = []
                for s in statuses:
                    sid = getattr(s, "id", "?")
                    sstat = getattr(s, "status", "?")
                    reason_parts.append(f"{sid}: {sstat}")
                detail = " · ".join(reason_parts) if reason_parts else "未知"
                results.append({
                    "url": orig,
                    "error": f"Exa 抓取失败（{detail}）· 该站可能有 Cloudflare/JS SPA 防护，试试更深的具体页面 URL 或切换到 Tavily",
                })
                continue

            item = items[0]
            main_text = getattr(item, "text", "") or ""
            title = getattr(item, "title", None) or url

            if deep:
                subs = getattr(item, "subpages", None) or []
                parts: list[str] = []
                if main_text:
                    parts.append(f"## [{title}]({url})\n\n{main_text[:8000]}")
                for s in subs:
                    s_url = getattr(s, "url", "") or ""
                    s_title = getattr(s, "title", None) or s_url
                    s_text = getattr(s, "text", "") or ""
                    if s_text:
                        parts.append(f"## [{s_title}]({s_url})\n\n{s_text[:8000]}")
                if not parts:
                    results.append({"url": orig, "error": "Exa 返回空内容"})
                    continue
                domain = urlparse(url).netloc or url
                results.append({
                    "url": orig,
                    "title": f"{domain} 深度抓取（Exa · {len(parts)} 页）",
                    "content": "\n\n---\n\n".join(parts)[:60000],
                    "error": None,
                })
            else:
                if not main_text:
                    results.append({"url": orig, "error": "Exa 返回空内容"})
                    continue
                results.append({
                    "url": orig,
                    "title": title,
                    "content": main_text[:20000],
                    "error": None,
                })
        except Exception as e:
            results.append({"url": orig, "error": f"Exa 异常: {e}"})

    return results


def _fetch_via_tavily(urls: list[tuple[str, str]], deep: bool) -> list[dict]:
    """Tavily 路径（原有实现，作为备选）。"""
    tavily_key = getattr(settings, 'TAVILY_API_KEY', '')
    if not tavily_key:
        return [{"url": orig, "error": "TAVILY_API_KEY 未配置"} for orig, _ in urls]

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
    except Exception as e:
        return [{"url": orig, "error": f"Tavily 加载失败: {e}"} for orig, _ in urls]

    results: list[dict] = []
    for orig, url in urls:
        title = None
        content = None
        error = None

        if deep:
            title, content, error = _deep_fetch(client, url, limit=10)
        else:
            try:
                r = client.extract(urls=[url])
                extracted = (r.get("results") or [None])[0]
                if extracted and extracted.get("raw_content"):
                    title = extracted.get("title") or url
                    content = extracted["raw_content"][:20000]
                else:
                    failed = (r.get("failed_results") or [None])[0]
                    error = (failed or {}).get("error") if failed else "extract 无内容"
            except Exception as e:
                error = f"extract 异常: {e}"

        if content:
            results.append({
                "url": orig, "title": title, "content": content, "error": None,
            })
        else:
            results.append({
                "url": orig,
                "error": error or "无法抓取内容（网站可能有反爬或需要登录）",
            })
    return results


def fetch_urls_content(urls: list[str], deep: bool = False, provider: str = "exa") -> list[dict]:
    """抓取指定 URL 列表的原始内容。

    - provider='exa'（默认）：用 Exa get_contents，livecrawl=always
    - provider='tavily'：用 Tavily extract / crawl
    - deep=True：两个 provider 都尝试抓取站内多页
    返回 list[{url, title, content, error}]，error 非空表示失败。
    """
    normalized = [(u, _normalize_url(u)) for u in urls if u and u.strip()]
    if not normalized:
        return []

    provider = (provider or "exa").lower().strip()
    if provider == "tavily":
        return _fetch_via_tavily(normalized, deep)
    # 默认 exa
    return _fetch_via_exa(normalized, deep)


def _fetch_urls_in_message(message: str) -> str:
    urls = re.findall(r'https?://[^\s,，。、]+|(?:[\w-]+\.)+(?:com|cn|net|org|io|ai|dev)(?:/[^\s,，。、]*)?', message)
    if not urls:
        return ""

    tavily_key = getattr(settings, 'TAVILY_API_KEY', '')
    if not tavily_key:
        return ""

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
    except Exception:
        return ""

    fetched_parts: list[str] = []
    for url in urls:
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        try:
            result = client.search(f"{domain} site:{domain}", include_raw_content=True, max_results=5)
            for r in result.get("results", []):
                content = r.get("raw_content") or r.get("content", "")
                if content:
                    fetched_parts.append(f"### {r.get('title','')}\n{content[:3000]}")
        except Exception as e:
            fetched_parts.append(f"## {url} 搜索失败：{e}")

    return "\n\n".join(fetched_parts)


# ---------- Stage 2: Outline Skeleton ----------

STAGE2_SYSTEM = """你是 PPT 规划师。根据已确认的定位和参考资料，生成大纲骨架。

要求：
- 每页只需要：slide_id、标题（title）和副标题/概要（subtitle）
- layout 从以下选择：cover, title-only, title-content, two-col, three-col, data-chart, full-image, quote, timeline, comparison, team, toc, blank
- 基于真实参考资料生成，不要编造信息

返回 JSON 数组：
[{"slide_id": "01", "layout": "cover", "title": "...", "subtitle": "..."}, ...]"""


def run_stage2_outline(
    positioning: str,
    user_message: str,
    context: str = "",
    scenario: dict | None = None,
    knowledge_context: str = "",
    case_context: str = "",
) -> dict:
    # Build augmented system prompt with scenario framework and data sources
    scenario_section = _build_scenario_prompt_section(scenario)
    augmented_system = STAGE2_SYSTEM + scenario_section + knowledge_context + case_context

    user_content = f"## 已确认的定位\n{positioning}\n\n## 用户需求\n{user_message}"
    if context:
        user_content += f"\n\n## 参考资料\n{context[:6000]}"

    messages = [{"role": "system", "content": augmented_system}, {"role": "user", "content": user_content}]
    resp = chat(MODEL, messages, temperature=0.7, max_tokens=4096)
    slides = extract_json_array(resp)
    return {"slides": slides or [], "raw_response": resp}


# ---------- Stage 3: Detail Enrichment ----------

STAGE3_SYSTEM = """你是 PPT 规划师。为每页补充具体内容元素。

对每页补充：
- points: 每条≤30字, 最多5条（基于真实资料）
- visual_intent: 视觉意图描述
  * 若需配图（人物/团队/产品/场景），明确指出：
    - 图片主体（如"多元化团队在白板前讨论"）
    - 建议风格（摄影/插画/扁平化/写实等）
    - 英文生图 prompt（6-12 字，给用户带去 Midjourney 用）
  * 格式示例：
    "[需要配图] 类型: 摄影 | 主体: 团队协作合照 | Prompt: diverse team brainstorming office"
- chart: 如需数据图表，指定 type 和 data（不用配图，效果师处理）

注意：系统不生成/嵌入真实图片，只画 SVG 占位框。
图片最终由用户在 PowerPoint 中替换。

返回完整 JSON 数组。"""


def run_stage3_details(
    outline_skeleton: list,
    user_message: str,
    context: str = "",
    scenario: dict | None = None,
    knowledge_context: str = "",
    case_context: str = "",
) -> dict:
    # Build augmented system prompt with scenario framework and data sources
    scenario_section = _build_scenario_prompt_section(scenario)
    augmented_system = STAGE3_SYSTEM + scenario_section + knowledge_context + case_context

    user_content = f"## 大纲骨架\n{json.dumps(outline_skeleton, ensure_ascii=False, indent=2)}"
    if context:
        user_content += f"\n\n## 参考资料\n{context[:6000]}"

    messages = [{"role": "system", "content": augmented_system}, {"role": "user", "content": user_content}]
    resp = chat(MODEL, messages, temperature=0.7, max_tokens=8192)
    slides = extract_json_array(resp)
    return {"slides": slides or [], "raw_response": resp}


# ---------- Conversational Refinement ----------

def refine_outline(current_slides: list, user_feedback: str, context: str = "") -> dict:
    system = f"""你是 PPT 规划师。用户对大纲有修改意见。
当前大纲：{json.dumps(current_slides, ensure_ascii=False, indent=2)}
如果是修改请求，返回修改后的完整 JSON 数组。
如果只是讨论/提问，用自然语言回复。"""

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_feedback}]
    resp = chat(MODEL, messages, temperature=0.7, max_tokens=4096)
    slides = extract_json_array(resp)
    if slides:
        return {"slides": slides, "message": "大纲已更新", "raw_response": resp}
    return {"slides": current_slides, "message": resp, "unchanged": True}


# ---------- Intent Classification ----------

def classify_intent(user_message: str, outline_path: str) -> tuple[str, list[str]]:
    messages = [
        {"role": "system", "content": '判断模式：global/route/diagnose。返回 JSON：{"mode":"...","target_slide_ids":[]}'},
        {"role": "user", "content": user_message},
    ]
    resp = chat(MODEL, messages, temperature=0.1, max_tokens=1024)
    data = extract_json_object(resp)
    if data:
        mode = data.get("mode", "global")
        if mode not in ("global", "route", "diagnose"):
            mode = "global"
        return mode, data.get("target_slide_ids", [])
    return "global", []


# ---------- Global Mode ----------

def run_global_mode(user_message: str, project_id: str, outline_path: str) -> dict:
    url_context = _fetch_urls_in_message(user_message)
    source_context = load_project_sources(project_id)
    # 合并：URL 实时抓取 + 已保存的源材料
    combined = ""
    if url_context:
        combined += url_context[:5000]
    if source_context:
        if combined:
            combined += "\n\n---\n\n"
        combined += source_context[:8000]
    return {
        "stage": 1,
        "url_context": combined,
        "user_message": user_message,
    }


# ---------- Diagnose Mode ----------

def run_diagnose_mode(user_message: str, outline_path: str) -> dict:
    outline = load_outline(outline_path)
    summary = outline.get_summary()
    messages = [
        {"role": "system", "content": "诊断 PPT 问题，返回 JSON: {\"issues\": [{\"dimension\":\"...\",\"description\":\"...\",\"affected_slides\":[...],\"fix_proposal\":\"...\"}]}"},
        {"role": "user", "content": f"反馈: {user_message}\n摘要:\n{json.dumps(summary, ensure_ascii=False)}"},
    ]
    resp = chat(MODEL, messages, temperature=0.5, max_tokens=2048)
    result = extract_json_object(resp)
    return result if result and "issues" in result else {"issues": [], "raw_response": resp}
