"""Flatten SVG gradient / pattern fills → solid colors.

Required because ppt-master's svg_to_pptx doesn't handle `fill="url(#...)"`
references. We flatten the *final* SVG used for PPTX conversion, but keep
the original SVG in svg_output/ so the browser still renders gradients.

Strategy:
- For each <linearGradient|radialGradient|pattern id="x">...</x>, find its
  first stop-color (attr or style) → that's the fallback color for id 'x'.
- Replace every fill="url(#x)" / stroke="url(#x)" with the fallback.
- Optionally strip the <defs><gradient> blocks themselves (unused after flatten).
"""
import re

# Matches <linearGradient | radialGradient | pattern id="xxx" ...>...</same>
GRADIENT_BLOCK_RE = re.compile(
    r'<(linearGradient|radialGradient|pattern)\b([^>]*?)\bid\s*=\s*["\']([^"\']+)["\']([^>]*)>(.*?)</\1>',
    re.DOTALL,
)
# Attribute-form stop color: <stop ... stop-color="#AAA" ... />
STOP_COLOR_ATTR_RE = re.compile(r'\bstop-color\s*=\s*["\']([^"\']+)["\']')
# Style-form stop color: style="stop-color:#AAA;..."
STOP_COLOR_STYLE_RE = re.compile(r'stop-color\s*:\s*([#\w().,\s-]+?)\s*(?:;|$|\")')
# Matches fill="url(#xxx)" / stroke="url(#xxx)" with either quote style
URL_REF_RE = re.compile(r'(fill|stroke)\s*=\s*(["\'])url\(#([^)]+)\)\2')

DEFAULT_FALLBACK = "#CCCCCC"


def _extract_first_stop_color(gradient_body: str) -> str:
    """Return the first stop-color found in a gradient body, or default."""
    m = STOP_COLOR_ATTR_RE.search(gradient_body)
    if m:
        return m.group(1).strip()
    m = STOP_COLOR_STYLE_RE.search(gradient_body)
    if m:
        return m.group(1).strip()
    return DEFAULT_FALLBACK


def extract_gradient_colors(svg: str) -> dict[str, str]:
    """Build {gradient_id: fallback_color} map."""
    mapping: dict[str, str] = {}
    for m in GRADIENT_BLOCK_RE.finditer(svg):
        grad_id = m.group(3)
        body = m.group(5)
        mapping[grad_id] = _extract_first_stop_color(body)
    return mapping


def flatten_fills(svg: str) -> str:
    """Replace all `fill/stroke="url(#id)"` with the matching gradient's first stop."""
    id_to_color = extract_gradient_colors(svg)
    if not id_to_color:
        return svg

    def replace(m: re.Match) -> str:
        attr = m.group(1)   # 'fill' or 'stroke'
        quote = m.group(2)  # " or '
        grad_id = m.group(3)
        color = id_to_color.get(grad_id, DEFAULT_FALLBACK)
        return f'{attr}={quote}{color}{quote}'

    return URL_REF_RE.sub(replace, svg)


# --- Escape un-encoded '&' inside <text>/<tspan> content ---
#
# LLMs sometimes output literal '&' in text (e.g. "Partnership & Future"),
# which breaks svg_to_pptx's XML parser ("not well-formed, invalid token").
# We selectively escape only '&' that isn't already part of an entity.
TEXT_NODE_RE = re.compile(
    r'(<(?:text|tspan)\b[^>]*>)([^<]*)(</(?:text|tspan)>)',
    re.DOTALL,
)
# Match '&' NOT followed by a named/numeric entity sequence
LONE_AMP_RE = re.compile(r'&(?![a-zA-Z][a-zA-Z0-9]{0,10};|#[0-9]+;|#x[0-9A-Fa-f]+;)')


def escape_text_content(svg: str) -> str:
    """Escape stray '&' chars inside <text>/<tspan> bodies.
    Leaves already-encoded entities (&amp; &#39; etc.) alone.
    """
    def fix(m: re.Match) -> str:
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
        fixed = LONE_AMP_RE.sub("&amp;", body)
        return f"{open_tag}{fixed}{close_tag}"
    return TEXT_NODE_RE.sub(fix, svg)


def sanitize_for_pptx(svg: str) -> str:
    """Full pre-PPTX sanitization: flatten gradient fills + escape stray '&'."""
    return escape_text_content(flatten_fills(svg))
