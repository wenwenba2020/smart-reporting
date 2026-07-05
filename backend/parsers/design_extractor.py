"""从 PPTX 提取配色/字体数据，用 LLM 生成符合 DESIGN.md 规范的模板内容。"""
import re
from pathlib import Path

from backend.parsers.ppt_parser import extract_style_info
from backend.agents.llm_client import chat

PROMPT_TEMPLATE = """你是一位资深 PPT 设计师。根据以下从 PPTX 中提取的设计数据，生成一份完整的 DESIGN.md 设计规范文档。

## 提取的原始数据
- 配色（hex）：{colors}
- 字体：{fonts}
- 字号(pt)：{font_sizes}
- 总页数：{slide_count}

## 输出要求
严格按照以下 7 个 section 输出 Markdown（不要省略任何 section）：

### 标题行
第一行必须是 `# 主题名 · English-Slug`，主题名 2-6 字中文，English-Slug 用英文小写连字符。

### Section 1: Visual Theme & Atmosphere
一行描述整体视觉氛围和适用场景。

### Section 2: Color Palette & Roles
从提取的配色中分配语义角色，至少包含：
- **Primary** `#XXXXXX` — 品牌主色
- **Secondary** `#XXXXXX` — 数据/图表
- **Accent** `#XXXXXX` — CTA/强调
- **Surface** `#XXXXXX` — 背景
- **Text-Primary** `#XXXXXX`
- **Text-Secondary** `#XXXXXX`
如果提取的颜色不够，合理推导补充。

### Section 3: Typography
根据字号推断层级，至少包含 hero/h1/h2/h3/body/caption 六个层级。

### Section 4: Layout Principles
根据配色和字体风格，描述 cover/title-content/data-chart 等常见布局的具体规则。

### Section 5: Depth & Elevation
描述卡片、阴影、圆角、图标底等深度层级规范。

### Section 6: Do's and Don'ts
4-6 条具体的设计约束。

### Section 7: Agent Prompt Guide
给 AI 设计师的提示词，指导如何生成符合此设计的 SVG。

只输出 DESIGN.md 内容，不要任何额外说明。"""


def generate_design_md(
    pptx_path: str | Path,
    custom_name: str | None = None,
) -> tuple[str, str]:
    """Generate a complete DESIGN.md from a PPTX file.

    Returns (slug, markdown_content).
    """
    pptx_path = Path(pptx_path)
    style = extract_style_info(str(pptx_path))

    colors = ", ".join(style["colors"][:12]) if style["colors"] else "未检测到"
    fonts = ", ".join(style["fonts"][:8]) if style["fonts"] else "未检测到"
    font_sizes = ", ".join(str(s) for s in style["font_sizes"][:10]) if style["font_sizes"] else "未检测到"
    slide_count = style["slide_count"]

    prompt = PROMPT_TEMPLATE.format(
        colors=colors,
        fonts=fonts,
        font_sizes=font_sizes,
        slide_count=slide_count,
    )

    raw = chat(
        model="qwen/qwen3.5-9b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
        extra_body={"enable_thinking": False},
    )

    # Extract slug from the first line: "# 主题名 · English-Slug"
    slug = "extracted-template"
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("# "):
            if " · " in line:
                slug = line.split(" · ", 1)[1].strip().lower()
                slug = re.sub(r"[^a-z0-9-]", "", slug.replace(" ", "-"))[:25]
            break

    # If custom_name given, replace the H1
    if custom_name:
        raw = re.sub(r"^# .+$", f"# {custom_name}", raw, count=1, flags=re.MULTILINE)
        slug = re.sub(r"[^a-z0-9-]", "", custom_name.lower().replace(" ", "-"))[:25]

    return slug, raw


def save_user_template(user_id: str, slug: str, content: str) -> Path:
    """Save a user-extracted template to disk. Returns the file path."""
    from backend.config import settings
    templates_dir = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user_id / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    filepath = templates_dir / f"{slug}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath
