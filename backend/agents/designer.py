"""设计师智能体 — 逐页生成 SVG 排版（顺序执行，禁止并发）
模型: Claude Sonnet 4.6 (anthropic/claude-sonnet-4.6) via OpenRouter

⚠️ 核心约束：
  1. SVG viewBox 必须是 "0 0 960 540"
  2. 必须顺序生成，前一页 SVG 传递给下一页保持风格一致
  3. 跳过 locked 页
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from backend.agents.events import publish_agent_progress, publish_slide_status
from backend.agents.llm_client import EmptyLLMResponse, chat
from backend.config import settings
from backend.models.outline import OutlineDoc, SlideItem, load_outline, save_outline

MODEL = settings.LLM_DESIGNER_MODEL

DESIGNER_SYSTEM = """你是资深 PPT 视觉设计师，输出媲美 Apple Keynote / Gamma.app / Pitch.com 的单页设计。

# 严格技术要求
1. viewBox 必须是 "0 0 960 540"
2. 必须包含 <defs><style> 块和 @font-face 声明
3. 必须有背景矩形（见视觉规则）
4. 中文换行用 <tspan>（SVG <text> 不支持自动换行）
5. 只输出 SVG 代码，不要任何解释文字

# 视觉设计铁律（禁止朴素线框稿）
**每一页必须满足**：
- 背景：禁止纯白 + 零装饰。至少使用以下之一：
  * 主色微调渐变背景（linearGradient）
  * 大色块分区（左右/上下/对角切分）
  * 浅色点/线/几何装饰元素（透明度 0.05-0.15）
- 视觉层次：标题必须有明确装饰（背景色块 / 左侧竖条 / 下划装饰线 / 角标数字）
- 内容区：points 不能是纯 bullet list，用以下之一呈现：
  * 卡片阵列（圆角矩形 + 淡阴影 + 图标）
  * 编号列表（大号数字 + 色块 + 文字）
  * 两栏/三栏布局 + 每项用独立色块区隔
  * 时间轴（横线 + 节点圆 + 文字）
  * 带图标的特性列表
- 配色：每页至少 4 种色彩（主色/辅色/强调色/文字），禁止只黑白灰
- 装饰元素：每页至少 3 个纯装饰性 SVG 形状（如抽象圆、几何线、小图标）

# 色板（默认，除非 DESIGN.md 覆盖）
- 主色 Primary: #1E3A5F（深蓝）
- 辅色 Secondary: #4A90D9（亮蓝）
- 强调色 Accent: #F5A623（橙黄）
- 成功色 Success: #10B981（绿）
- 背景 Surface: #FFFFFF
- 浅色填充 Surface-Alt: #F3F4F6
- 文字深 Text-Primary: #1A1A2E
- 文字浅 Text-Secondary: #6B7280

# 字体
<defs><style>
  @font-face { font-family: 'AlibabaPuHuiTi'; src: url('/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf'); font-weight: 400; }
  @font-face { font-family: 'AlibabaPuHuiTi'; src: url('/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Bold.ttf'); font-weight: 700; }
  @font-face { font-family: 'Inter'; src: url('/fonts/Inter/Inter-Regular.ttf'); font-weight: 400; }
</style></defs>
- 标题字号：封面 52-60pt / 页标题 32-40pt
- 正文 18-22pt / 辅助 12-14pt

# 图片处理（本智能体不生成真图）
当 visual_intent 含配图信号时，生成精美占位框：
<g>
  <rect x="..." y="..." width="..." height="..." rx="12"
        stroke="#9CA3AF" stroke-dasharray="6,4" stroke-width="1.5" fill="#F3F4F6"/>
  <text x="..." y="..." text-anchor="middle" font-size="36" fill="#9CA3AF">🖼️</text>
  <text x="..." y="..." text-anchor="middle" font-size="14" fill="#6B7280">中文描述</text>
  <text x="..." y="..." text-anchor="middle" font-size="10" fill="#9CA3AF" font-style="italic">english prompt</text>
</g>

# 各布局参考结构

## cover（封面）
大标题左 2/3 区 · 辅以主色色块背景 + 右下角几何装饰 · 右侧可选图片占位
示例骨架：
<rect width="960" height="540" fill="url(#coverGrad)"/>  <!-- 渐变背景 -->
<defs><linearGradient id="coverGrad" x1="0" x2="1"><stop offset="0" stop-color="#1E3A5F"/><stop offset="1" stop-color="#4A90D9"/></linearGradient></defs>
<circle cx="820" cy="480" r="120" fill="#F5A623" opacity="0.15"/>  <!-- 装饰圆 -->
<rect x="60" y="200" width="6" height="60" fill="#F5A623"/>  <!-- 左侧竖条 -->
<text x="80" y="240" font-size="56" font-weight="700" fill="#FFFFFF">标题</text>
<text x="80" y="290" font-size="22" fill="#E5E7EB">副标题</text>

## title-content（标题 + 要点）
顶部色条标题 · 主体区编号卡片阵列或图标列表
示例骨架：
<rect width="960" height="540" fill="#FFFFFF"/>
<rect x="0" y="0" width="960" height="80" fill="#1E3A5F"/>  <!-- 顶部色条 -->
<text x="60" y="55" font-size="32" font-weight="700" fill="#FFFFFF">页标题</text>
<!-- 3 个卡片 -->
<g>
  <rect x="60" y="130" width="270" height="340" rx="12" fill="#F3F4F6"/>
  <circle cx="100" cy="175" r="22" fill="#4A90D9"/>
  <text x="100" y="182" text-anchor="middle" font-size="22" font-weight="700" fill="#FFFFFF">01</text>
  <text x="80" y="230" font-size="20" font-weight="700" fill="#1A1A2E">要点标题</text>
  <text x="80" y="260" font-size="14" fill="#6B7280">详情描述文字...</text>
</g>
(另外两个卡片依次并排)

## two-col（两栏对比 / 左文右图）
左右等分 · 一侧文字一侧图片占位或图表 · 中间细分隔线

## data-chart（数据页）
上部标题 + 关键数字（超大号字体 + 强调色）· 下部图表占位区 · 右上角小图标

**最终输出必须完整 SVG，从 <svg 到 </svg>，不要代码块标记，不要解释。**"""

DEFAULT_DESIGN = """## Color Palette
- Primary: #1E3A5F
- Secondary: #4A90D9
- Accent: #F5A623
- Surface: #FFFFFF
- Text-Primary: #1A1A2E
- Text-Secondary: #6B7280

## Typography
- 标题字体: AlibabaPuHuiTi Bold
- 正文字体: AlibabaPuHuiTi Regular
- 英文配套: Inter
- 标题字号: 封面 44pt, 页标题 32pt
- 正文字号: 18pt
"""


def _build_slide_prompt(
    slide: SlideItem,
    design_md: str,
    previous_svg: str | None,
    current_svg: str | None = None,
) -> str:
    """Build the user prompt for generating a single slide SVG.

    - previous_svg: 上一页的 SVG（流水线首次生成时用来保持跨页风格一致）
    - current_svg: 本页当前的 SVG（单页修改/回退时，作为"改动基础"完整传入）
    """
    parts = [
        f"## 页面信息",
        f"slide_id: {slide.slide_id}",
        f"layout: {slide.layout}",
        f"title: {slide.title}",
    ]
    if slide.subtitle:
        parts.append(f"subtitle: {slide.subtitle}")
    if slide.points:
        points_lines = ["points:"]
        for p in slide.points:
            points_lines.append(f"  - {p.heading}")
            if p.body:
                for body_line in p.body.splitlines():
                    points_lines.append(f"    {body_line}")
        parts.append("\n".join(points_lines))
    if slide.visual_intent:
        parts.append(f"visual_intent: {slide.visual_intent}")

    parts.append(f"\n## 设计规范\n{design_md}")

    if current_svg:
        # Single-slide revision: base modifications on the current SVG (full, not truncated)
        parts.append(
            "\n## 当前页面 SVG（本次修改的基础 · 完整未截断）"
            "\n⚠️ 关键原则：**外科手术式修改**，不要重新设计整页。\n"
            "\n步骤：\n"
            "1. 仔细阅读 visual_intent 里**最后一条** `[用户修改指令]`（之前的指令**已经生效并固化在下方 SVG 里**，不要再次应用）\n"
            "2. 定位该指令涉及哪些 SVG 元素（例如：'改标题'→只改大标题文字节点；'改背景色'→只改 background rect 的 fill；'删 X'→只删 X 对应的节点）\n"
            "3. 在下方完整 SVG 中**仅修改**这些元素，其余一字一节点**原样保留**\n"
            "4. 不要擅自改字体、字号、位置、色彩、装饰、图片占位，除非指令明确要求\n"
            "5. 不要重排版、不要「顺便优化」、不要加新元素\n"
            "\n返回修改后的**完整 SVG**（包含 <defs><style> 字体声明 + 所有原有元素）。\n"
            f"```svg\n{current_svg}\n```"
        )
    elif previous_svg:
        # Pipeline first-pass: reference previous slide only for cross-slide style consistency
        svg_preview = previous_svg[:2000] + "..." if len(previous_svg) > 2000 else previous_svg
        parts.append(f"\n## 前一页 SVG（仅参考跨页风格一致性，不要照抄结构）\n```svg\n{svg_preview}\n```")

    return "\n".join(parts)


def _extract_svg(response: str) -> str:
    """Extract SVG content from LLM response."""
    if not response:
        return ""

    text = response

    # Strip markdown code fences (```svg / ```xml / ```)
    fence = re.search(r"```(?:svg|xml|html)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)

    # Primary: complete <svg>...</svg>
    match = re.search(r"<svg[^>]*>.*?</svg>", text, re.DOTALL)
    if match:
        return match.group()

    # Fallback: starts with <?xml or <svg (maybe already bare)
    stripped = text.strip()
    if stripped.startswith("<?xml") or stripped.startswith("<svg"):
        return stripped

    return ""


def generate_single_slide(
    slide: SlideItem,
    design_md: str,
    previous_svg: str | None = None,
    current_svg: str | None = None,
) -> str:
    """Generate SVG for a single slide. Returns SVG string.

    Use current_svg for single-slide revise (edit-on-top), previous_svg for
    first-pass cross-slide style consistency. If both are given, current_svg
    takes precedence.
    """
    user_prompt = _build_slide_prompt(slide, design_md, previous_svg, current_svg)

    messages = [
        {"role": "system", "content": DESIGNER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    # Retry up to 2 times if SVG extraction fails
    svg = ""
    for attempt in range(3):
        try:
            response = chat(MODEL, messages, temperature=0.5 + attempt * 0.1, max_tokens=16384)
        except EmptyLLMResponse as e:
            logger.warning("Slide %s attempt %d: %s — retrying with higher temperature",
                           slide.slide_id, attempt + 1, e)
            continue
        svg = _extract_svg(response)
        if svg:
            break
        preview_head = (response or "")[:200].replace("\n", "\\n")
        preview_tail = (response or "")[-200:].replace("\n", "\\n")
        logger.warning(
            "Slide %s attempt %d: SVG extraction failed. "
            "len=%d, has_svg_open=%s, has_svg_close=%s | HEAD=%r | TAIL=%r",
            slide.slide_id, attempt + 1,
            len(response or ""),
            "<svg" in (response or ""),
            "</svg>" in (response or ""),
            preview_head, preview_tail,
        )

    if not svg:
        raise ValueError(f"Designer failed to generate SVG for slide {slide.slide_id} after 3 attempts")

    # Enforce viewBox — replace any existing viewBox or add if missing
    if 'viewBox="0 0 960 540"' not in svg:
        if re.search(r'viewBox\s*=\s*["\'][^"\']*["\']', svg):
            svg = re.sub(r'viewBox\s*=\s*["\'][^"\']*["\']', 'viewBox="0 0 960 540"', svg, count=1)
        else:
            svg = svg.replace("<svg ", '<svg viewBox="0 0 960 540" ', 1)

    return svg


def run_designer(project_id: str, outline_path: str, design_path: str) -> dict:
    """
    Generate SVGs for all non-locked todo slides. SEQUENTIAL, not concurrent.
    Saves each SVG to svg_output/slide_{id}.svg.

    Retry strategy:
      - Inner retry: generate_single_slide() retries 3x with rising temperature
      - Outer retry: failed slides get one more pass without previous_svg context
        (defensive: prior page's SVG may have confused the LLM)
      - Slides still failing after outer pass are marked status="failed"
    """
    from backend.agents.events import publish_agent_start, publish_error
    from backend.storage.file_manager import ProjectStorage

    storage = ProjectStorage.get()
    project_dir = storage.get_project_path(project_id)
    svg_dir = project_dir / "svg_output"
    svg_dir.mkdir(parents=True, exist_ok=True)

    outline = load_outline(outline_path)

    # Load or use default DESIGN.md
    design_md = DEFAULT_DESIGN
    if design_path:
        design_file = Path(design_path)
        if design_file.is_file():
            design_md = design_file.read_text(encoding="utf-8")

    completed: list[str] = []
    failed_first_pass: list[str] = []
    previous_svg: str | None = None

    total = sum(1 for s in outline.slides if s.status == "todo" and not s.locked)
    done_count = 0

    # ---------- First pass ----------
    for slide in outline.slides:
        if slide.locked:
            # Read existing SVG for context continuity
            existing = svg_dir / f"slide_{slide.slide_id}.svg"
            if existing.exists():
                previous_svg = existing.read_text(encoding="utf-8")
            continue

        if slide.status != "todo":
            continue

        try:
            publish_slide_status(project_id, slide.slide_id, "generating")

            svg = generate_single_slide(slide, design_md, previous_svg)

            # Save SVG
            svg_path = svg_dir / f"slide_{slide.slide_id}.svg"
            svg_path.write_text(svg, encoding="utf-8")

            slide.status = "done"
            previous_svg = svg
            completed.append(slide.slide_id)
            done_count += 1

            publish_slide_status(project_id, slide.slide_id, "done")
            publish_agent_progress(project_id, "designer", done_count / total if total > 0 else 1.0,
                                   f"完成 {slide.slide_id}: {slide.title}")

        except Exception as e:
            logger.error("Designer first-pass failed on slide %s: %s", slide.slide_id, e, exc_info=True)
            failed_first_pass.append(slide.slide_id)
            # Keep as "todo" for second pass; don't mark "failed" yet.

    # ---------- Second pass (retry failed slides without previous_svg pollution) ----------
    still_failed: list[str] = []
    if failed_first_pass:
        publish_agent_start(project_id, "designer",
                            f"重试 {len(failed_first_pass)} 个失败页...")
        for slide in outline.slides:
            if slide.slide_id not in failed_first_pass:
                continue
            try:
                publish_slide_status(project_id, slide.slide_id, "generating")
                # Retry WITHOUT previous_svg (clean context)
                svg = generate_single_slide(slide, design_md, previous_svg=None)

                svg_path = svg_dir / f"slide_{slide.slide_id}.svg"
                svg_path.write_text(svg, encoding="utf-8")

                slide.status = "done"
                completed.append(slide.slide_id)
                done_count += 1

                publish_slide_status(project_id, slide.slide_id, "done")
                publish_agent_progress(project_id, "designer", done_count / total if total > 0 else 1.0,
                                       f"重试成功 {slide.slide_id}: {slide.title}")
            except Exception as e:
                logger.error("Designer retry also failed on slide %s: %s", slide.slide_id, e, exc_info=True)
                slide.status = "failed"
                still_failed.append(slide.slide_id)
                publish_slide_status(project_id, slide.slide_id, "failed")
                publish_error(
                    project_id, "designer",
                    f"Slide {slide.slide_id} 自动重试后仍失败 · 可在右栏点击该页手动修改",
                    recoverable=True,
                )

    # Save updated outline
    save_outline(outline, outline_path)

    return {"completed_slides": completed, "failed_slides": still_failed}
