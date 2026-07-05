"""轻量 SVG 文字编辑 — 用户手动改文字，不走 LLM。

- extract_texts: 列出 SVG 里所有 <text>/<tspan> 节点文字（按文档顺序）
- apply_text_edits: 按节点 index 替换文字，保留所有 attributes 和结构
- 换行支持：new_text 含 \n 时自动转 <tspan dy="1.2em"> 序列，沿用原节点 x 属性

对嵌套 <text><tspan>...</tspan></text>：外层 text.text 是 tspan 前的文字，
内层 tspan 单独算一个节点。regex `[^<]*` 自然处理。
"""
import html
import re

# Group 1: opening tag with attrs; Group 2: element name; Group 3: inner text; Group 4: closing tag
TEXT_RE = re.compile(r'(<(text|tspan)(?:\s[^>]*)?>)([^<]*)(</\2>)', re.DOTALL)
_X_ATTR_RE = re.compile(r'\bx\s*=\s*["\']([^"\']+)["\']')


def extract_texts(svg: str) -> list[dict]:
    """Return non-empty text nodes with their absolute index (finditer order)."""
    result = []
    for i, m in enumerate(TEXT_RE.finditer(svg)):
        inner = m.group(3)
        if inner and inner.strip():
            result.append({"index": i, "text": inner, "tag": m.group(2)})
    return result


def _escape_svg_text(s: str) -> str:
    """Escape XML-reserved chars in text content."""
    return html.escape(s, quote=False)


def _build_inner_for_multiline(open_tag: str, new_text: str, tag: str) -> str:
    """Convert multi-line new_text to nested <tspan dy> elements.
    Single-line text returns as-is (escaped).
    Uses the original open tag's x attribute so every line starts at the same x.
    """
    if "\n" not in new_text:
        return _escape_svg_text(new_text)

    x_match = _X_ATTR_RE.search(open_tag)
    x_val = x_match.group(1) if x_match else None
    x_attr = f' x="{x_val}"' if x_val else ""

    lines = new_text.split("\n")
    parts = []
    for i, line in enumerate(lines):
        escaped = _escape_svg_text(line)
        if i == 0:
            # First line stays as the open tag's direct child
            parts.append(escaped)
        else:
            parts.append(f'<tspan{x_attr} dy="1.2em">{escaped}</tspan>')
    return "".join(parts)


def apply_text_edits(svg: str, edits: list[dict]) -> str:
    """Apply {index, new_text} edits in-place, preserving tag and attributes.
    Multi-line new_text auto-converts to <tspan dy="1.2em"> sequence.
    """
    edit_map = {e["index"]: e["new_text"] for e in edits if "index" in e and "new_text" in e}
    if not edit_map:
        return svg

    counter = [0]

    def replace(m: re.Match) -> str:
        idx = counter[0]
        counter[0] += 1
        if idx not in edit_map:
            return m.group(0)
        open_tag = m.group(1)
        tag_name = m.group(2)
        new_text = edit_map[idx]
        inner = _build_inner_for_multiline(open_tag, new_text, tag_name)
        return f"{open_tag}{inner}{m.group(4)}"

    return TEXT_RE.sub(replace, svg)
