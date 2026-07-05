"""效果师智能体 — 图表数据注入 + AI 辅助图表识别
模型: qwen3 (SiliconFlow/OpenRouter) — 轻量数据抽取

职责（双轨）：
- 规则轨：OUTLINE 已有 slide.chart 字段 → 直接走 pyecharts 渲染（不调 LLM）
- LLM 轨：slide.chart 为空但内容暗示需要图表（关键词命中）→ LLM 判断 + 抽数据
- 最终统一产出 chart_{id}.json 供编辑师注入 PPTX
"""
import json
import logging
import re

from backend.agents.events import publish_agent_progress, publish_event
from backend.agents.json_utils import extract_json_object
from backend.agents.llm_client import chat
from backend.config import settings
from backend.models.outline import ChartConfig, load_outline, save_outline
from backend.pipeline.chart_renderer import render_chart

logger = logging.getLogger(__name__)

MODEL = settings.LLM_EFFECTS_MODEL

# Slides matching these keywords are candidates for AI chart suggestion.
CHART_HINT_PATTERN = re.compile(
    r"(图表|趋势|增长|下降|变化|对比|占比|分布|份额|比例|"
    r"排名|top|TOP|榜单|数据|指标|\d+%|\d+\.\d+%|"
    r"同比|环比|增速|增长率|市场占有|市场份额)"
)

SUPPORTED_CHART_TYPES = ("bar", "bar-grouped", "line", "pie", "radar")

EFFECTS_SYSTEM = """你是 PPT 效果师。分析一页幻灯片内容，判断是否需要数据图表。

规则：
1. 只有明确的**数值数据 / 百分比 / 对比 / 时序趋势 / 分类占比**才需要图表
2. 纯文字叙述、概念介绍、流程说明 → 不需要图表
3. 支持类型：
   - bar: 简单对比（如各季度营收）
   - bar-grouped: 多系列对比（如不同产品多季度对比）
   - line: 时间序列趋势（如 12 个月 DAU 变化）
   - pie: 占比/份额（如市场份额分布，5 项以内）
   - radar: 多维度评分（如产品 5 项指标对比）

data 格式：
  - bar/line: [[类别, 数值], [类别, 数值], ...]
  - bar-grouped: [[类别, 系列1值, 系列2值, ...], ...]
  - pie: [[项目, 值], ...]
  - radar: [[维度, 值], ...]

返回 JSON（不要代码块，不要多余文字）：
  不需要: {"needs_chart": false}
  需要:   {"needs_chart": true, "type": "bar|line|pie|bar-grouped|radar",
          "data": [...], "caption": "简短图表标题（≤12字）"}

严格要求：数据必须基于 points 中真实数值，不得虚构。若 points 无明确数值，返回 needs_chart: false。"""


def _needs_chart_analysis(slide) -> bool:
    """Quick keyword filter — only invoke LLM for candidate slides."""
    if slide.chart:
        return False  # Already has chart
    if slide.locked or slide.status == "failed":
        return False
    hint_text = (slide.visual_intent or "") + "\n" + "\n".join(slide.points or [])
    return bool(CHART_HINT_PATTERN.search(hint_text))


def _llm_suggest_chart(slide) -> ChartConfig | None:
    """Ask LLM whether this slide needs a chart and, if so, extract the config."""
    user_content = (
        f"幻灯片 [{slide.slide_id}] · {slide.layout}\n"
        f"标题: {slide.title}\n"
    )
    if slide.points:
        user_content += "要点:\n" + "\n".join(f"  - {p}" for p in slide.points) + "\n"
    if slide.visual_intent:
        user_content += f"视觉意图: {slide.visual_intent}\n"

    try:
        resp = chat(
            MODEL,
            [{"role": "system", "content": EFFECTS_SYSTEM},
             {"role": "user", "content": user_content}],
            temperature=0.3,
            max_tokens=1024,
            extra_body={"enable_thinking": False},  # Qwen3: skip thinking to save tokens
        )
    except Exception as e:
        logger.warning("Effects LLM call failed for slide %s: %s", slide.slide_id, e)
        return None

    data = extract_json_object(resp)
    if not data or not data.get("needs_chart"):
        return None

    chart_type = data.get("type")
    chart_data = data.get("data")
    caption = data.get("caption")

    if chart_type not in SUPPORTED_CHART_TYPES:
        logger.info("Effects: slide %s got unsupported chart type %s", slide.slide_id, chart_type)
        return None
    if not isinstance(chart_data, list) or len(chart_data) == 0:
        return None

    return ChartConfig(
        type=chart_type,
        data_ref="inline",
        data=chart_data,
        caption=caption,
    )


def _build_chart_config_dict(chart: ChartConfig) -> dict | None:
    """Normalize ChartConfig.data to the format expected by render_chart()."""
    if not chart.data:
        return None

    if chart.type in ("pie", "funnel"):
        return {
            "data": [tuple(d) if isinstance(d, list) else d for d in chart.data],
            "caption": chart.caption or "",
        }

    if chart.type == "scatter":
        return {"data": chart.data, "caption": chart.caption or ""}

    # bar / bar-grouped / line / radar: categories + series
    first = chart.data[0]
    if not (isinstance(first, list) and len(first) >= 2):
        return None

    categories = [str(d[0]) for d in chart.data]

    if len(first) == 2:
        # Single series
        return {
            "categories": categories,
            "series": [{"name": chart.caption or "数据",
                        "values": [d[1] for d in chart.data]}],
            "caption": chart.caption or "",
        }

    # Multi-series (bar-grouped with header row or numeric columns)
    series_count = len(first) - 1
    return {
        "categories": categories,
        "series": [
            {"name": f"系列{i+1}",
             "values": [d[i + 1] for d in chart.data]}
            for i in range(series_count)
        ],
        "caption": chart.caption or "",
    }


def run_effects(project_id: str, outline_path: str) -> dict:
    """Process charts for slides. Pure-rule for existing chart fields,
    LLM-augmented for content that hints at data but lacks chart config."""
    from backend.storage.file_manager import ProjectStorage

    outline = load_outline(outline_path)
    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id)

    # ---------- Phase 1: LLM augmentation ----------
    candidates = [s for s in outline.slides if _needs_chart_analysis(s)]
    if candidates:
        publish_event(project_id, {
            "type": "agent_thinking",
            "agent": "effects",
            "thought": f"扫描到 {len(candidates)} 页可能需要图表，正在 LLM 分析...",
        })
        augmented = 0
        for slide in candidates:
            suggestion = _llm_suggest_chart(slide)
            if suggestion:
                slide.chart = suggestion
                augmented += 1
                logger.info("Effects: LLM suggested %s chart for slide %s",
                            suggestion.type, slide.slide_id)
        if augmented:
            save_outline(outline, outline_path)
            publish_event(project_id, {
                "type": "agent_thinking",
                "agent": "effects",
                "thought": f"✨ LLM 识别并补全 {augmented} 个图表",
            })

    # ---------- Phase 2: Render all charts (rule-based) ----------
    charts_generated: list[str] = []
    total_charts = sum(1 for s in outline.slides if s.chart and not s.locked)
    done = 0

    for slide in outline.slides:
        if not slide.chart or slide.locked:
            continue

        try:
            chart_config = _build_chart_config_dict(slide.chart)
            if not chart_config:
                continue

            defn = render_chart(slide.chart.type, chart_config)

            chart_json_path = project_dir / "data" / f"chart_{slide.slide_id}.json"
            chart_json_path.parent.mkdir(parents=True, exist_ok=True)
            chart_json_path.write_text(json.dumps({
                "slide_id": slide.slide_id,
                "xl_chart_type": defn.xl_chart_type,
                "caption": defn.caption,
                "colors": defn.colors,
                "chart_config": chart_config,
            }, ensure_ascii=False, indent=2))

            charts_generated.append(slide.slide_id)
            done += 1
            publish_agent_progress(
                project_id, "effects",
                done / total_charts if total_charts > 0 else 1.0,
                f"图表 {slide.slide_id}: {slide.chart.type}"
            )

        except Exception as e:
            logger.warning("Effects failed for slide %s: %s", slide.slide_id, e)

    return {"charts_generated": charts_generated}
