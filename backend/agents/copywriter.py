"""W3-3: 文案师智能体 — 逐页填充 OUTLINE.md 文案内容
模型: DeepSeek V3.2 (deepseek/deepseek-v3.2) via OpenRouter

职责：
- 从源文档提炼内容，生成每页文案
- 填写 title (≤15字)、subtitle、points (每条≤30字, 最多5条)、notes_speaker
- 不负责排版，不生成 SVG
- 写入 OUTLINE.md 时必须加文件锁（由 save_outline 处理）
"""
import logging
from pathlib import Path

from backend.agents.json_utils import extract_json_object
from backend.agents.llm_client import EmptyLLMResponse, chat
from backend.config import settings
from backend.models.outline import PointItem, load_outline, save_outline
from backend.storage.file_manager import ProjectStorage

logger = logging.getLogger(__name__)

MODEL = settings.LLM_COPYWRITER_MODEL


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

COPYWRITER_SYSTEM = """你是 PPT 文案师。根据页面布局和主题，为幻灯片生成精炼的中文文案。

严格遵守：
- title: 不超过 15 个字
- points: 返回一个列表，每项是 {"heading": 短标题（≤30 字）, "body": 段落讲解}
  - layout 为 cover / title-only / toc 时：body 填 null，heading 简短
  - layout 为 title-content / two-col / three-col / comparison / data-chart / timeline / team 时：body **必填**，120-250 字，围绕 heading 展开数据 / 论据 / 案例 / 方法论
  - 不编造数据；无依据时写分析框架或背景
  - 最多 5 条
- notes_speaker: 演讲者备注，50-100 字
- 不做排版决策，不提及字体或颜色

返回 JSON：
{
  "title": "...",
  "subtitle": "...",
  "points": [
    {"heading": "...", "body": "..."},
    {"heading": "...", "body": null}
  ],
  "notes_speaker": "..."
}

## 知识溯源要求
当你使用知识库中的数据（产品参数、客户信息、会议纪要等），请：
1. 确保数据的准确性和时效性
2. 在 notes_speaker 中标注信息来源（如"数据来源：D7020产品规格书"）
3. 不要编造数据。如果知识库中没有相关数据，使用占位符如 [数据待补充]
4. 优先使用知识库中的专业术语和产品正式名称
"""


def _generate_slide_content(
    slide_id: str,
    layout: str,
    visual_intent: str | None,
    existing_title: str,
    source_context: str = "",
) -> dict:
    """Generate content for a single slide."""
    user_prompt = (
        f"幻灯片 [{slide_id}]\n"
        f"布局: {layout}\n"
        f"当前标题: {existing_title}\n"
    )
    if visual_intent:
        user_prompt += f"视觉意图: {visual_intent}\n"
    if source_context:
        user_prompt += f"\n## 参考资料\n{source_context[:4000]}\n"

    messages = [
        {"role": "system", "content": COPYWRITER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = chat(MODEL, messages, temperature=0.7, max_tokens=1024)
    except EmptyLLMResponse as e:
        logger.warning("Copywriter empty response for slide %s: %s", slide_id, e)
        return {}
    return extract_json_object(resp) or {}


def run_copywriter(project_id: str, outline_path: str) -> dict:
    """Fill in content for all todo slides in the outline."""
    outline = load_outline(outline_path)
    completed: list[str] = []
    failed: list[str] = []

    # 加载项目源材料供文案师参考
    source_context = load_project_sources(project_id)

    for slide in outline.slides:
        if slide.status != "todo":
            continue
        if slide.locked:
            continue

        content = _generate_slide_content(
            slide_id=slide.slide_id,
            layout=slide.layout,
            visual_intent=slide.visual_intent,
            existing_title=slide.title,
            source_context=source_context,
        )

        if content:
            if "title" in content:
                slide.title = content["title"][:15]
            if "subtitle" in content:
                slide.subtitle = content.get("subtitle")
            if "points" in content:
                raw_points = content["points"][:5]
                coerced: list[PointItem] = []
                for p in raw_points:
                    if isinstance(p, str):
                        coerced.append(PointItem(heading=p[:30], body=None))
                    elif isinstance(p, dict):
                        coerced.append(PointItem(
                            heading=str(p.get("heading", ""))[:30],
                            body=p.get("body") if p.get("body") else None,
                        ))
                slide.points = coerced
            if "notes_speaker" in content:
                slide.notes_speaker = content["notes_speaker"]
            completed.append(slide.slide_id)
        else:
            failed.append(slide.slide_id)

    # Save with file lock (atomic write)
    save_outline(outline, outline_path)

    return {
        "completed_slides": completed,
        "failed_slides": failed,
    }
