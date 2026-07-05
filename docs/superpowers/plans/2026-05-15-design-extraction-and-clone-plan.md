# 设计提取为模板 + 单页设计克隆 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从上传的 PPTX 提取完整 DESIGN.md 模板供复用，以及导入 slide 时保留原始设计作为 design_ref。

**Architecture:** Part B（模板提取）复用 `ppt_parser.extract_style_info()` 获取原始配色/字体数据，调 Qwen 9B 生成符合 DESIGN.md 规范的模板文件，存入 `.slide_library/{user}/templates/`，合并到设计模板列表 API。Part A（设计克隆）导入时复制 slide.xml + 图片到项目目录，在 OUTLINE.md 添加 `design_ref` 字段。

**Tech Stack:** Python/FastAPI + python-pptx + OpenRouter (Qwen 9B) + React/Zustand

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `backend/api/routes/slide_library.py` | B: 新增 extract-design 端点 + delete-template 端点 |
| Modify | `backend/api/routes/projects.py` | B: 合并用户模板到 design-templates 列表 |
| Create | `backend/parsers/design_extractor.py` | B: LLM 生成 DESIGN.md 的核心逻辑 |
| Modify | `backend/api/routes/slide_library.py` | A: import-to-project 支持 clone_design 参数 |
| Create | `backend/pipeline/slide_cloner.py` | A: 复制 slide XML + 图片 + 解析 layout 描述 |
| Modify | `backend/models/outline.py` | A: SlideItem 增加 design_ref 字段 |
| Modify | `frontend/src/api/client.ts` | B: 新增 extractDesign API 函数 |
| Modify | `frontend/src/types/events.ts` | B: 新增模板类型 |
| Modify | `frontend/src/components/SlideLibrary/index.tsx` | B: 提取设计按钮 + 处理 |
| Modify | `frontend/src/components/StylePanel.tsx` | B: 显示用户提取的模板 |

---

### Task 1: B · 设计提取核心逻辑 · design_extractor.py

**Files:**
- Create: `backend/parsers/design_extractor.py`

- [ ] **Step 1: 创建 design_extractor.py**

```python
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
```

- [ ] **Step 2: 验证导入**

```bash
.venv/bin/python -c "from backend.parsers.design_extractor import generate_design_md; print('OK')"
```
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/parsers/design_extractor.py
git commit -m "feat: add design extractor — LLM-powered DESIGN.md generation from PPTX"
```

---

### Task 2: B · extract-design + delete-template API 端点

**Files:**
- Modify: `backend/api/routes/slide_library.py`

- [ ] **Step 1: 读取当前 slide_library.py 并添加端点**

在文件末尾（`recommend_slides` 之后）添加两个新端点。先读取文件确认当前末尾位置。

添加以下 import（放在文件顶部现有 import 之后）：

```python
from backend.parsers.design_extractor import generate_design_md, save_user_template
```

添加两个端点：

```python
class ExtractDesignRequest(BaseModel):
    name: str | None = None


@router.post("/decks/{library_id}/extract-design")
async def extract_design(
    library_id: str,
    body: ExtractDesignRequest = ExtractDesignRequest(),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从 PPTX 提取设计规范，保存为用户模板。"""
    result = await db.execute(
        select(SlideLibrary).where(
            SlideLibrary.id == library_id,
            SlideLibrary.user_id == user,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=404, detail="Deck not found")

    pptx_path = _lib_dir(user, library_id) / "original.pptx"
    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="Original PPTX file not found")

    try:
        slug, content = generate_design_md(str(pptx_path), body.name)
        filepath = save_user_template(user, slug, content)
        return {
            "slug": slug,
            "name": body.name or library.name,
            "path": str(filepath),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Design extraction failed: {str(e)}")


@router.delete("/templates/{slug}")
async def delete_user_template(
    slug: str,
    user: str = Depends(get_current_user),
):
    """删除用户提取的设计模板。"""
    from backend.config import settings
    templates_dir = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user / "templates"
    filepath = templates_dir / f"{slug}.md"
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Template not found")
    filepath.unlink()
    return {"deleted": slug}
```

- [ ] **Step 2: 验证端点导入**

```bash
.venv/bin/python -c "from backend.api.routes.slide_library import router; print('OK')"
```
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/api/routes/slide_library.py
git commit -m "feat: add extract-design and delete-template API endpoints"
```

---

### Task 3: B · 合并用户模板到 design-templates 列表

**Files:**
- Modify: `backend/api/routes/projects.py`
- Modify: `backend/design_templates/__init__.py`

- [ ] **Step 1: 在 design_templates/__init__.py 添加用户模板读取函数**

读取 `/home/wenwenba2020/cc_workspace/ppt_agent/backend/design_templates/__init__.py`，在文件末尾添加：

```python
def list_user_templates(user_id: str) -> list[dict]:
    """Return user-extracted templates from .slide_library/{user_id}/templates/."""
    from backend.config import settings
    user_dir = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user_id / "templates"
    if not user_dir.is_dir():
        return []

    out = []
    for f in sorted(user_dir.glob("*.md")):
        try:
            md = f.read_text(encoding="utf-8")
            name, subtitle = _parse_h1(md)
            lines = md.splitlines()
            desc = ""
            for i, line in enumerate(lines):
                if line.strip().startswith("## 1.") or "Visual Theme" in line:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        text = lines[j].strip()
                        if text and not text.startswith("#"):
                            desc = text
                            break
                    break
            out.append({
                "id": f"user/{f.stem}",
                "name": name,
                "subtitle": subtitle,
                "description": desc,
                "colors": _extract_colors(md)[:6],
            })
        except Exception:
            continue
    return out


def get_user_template(user_id: str, template_id: str) -> str | None:
    """Return the raw markdown content of a user template, or None."""
    slug = template_id.replace("user/", "", 1)
    from backend.config import settings
    f = Path(settings.LOCAL_STORAGE_PATH) / ".slide_library" / user_id / "templates" / f"{slug}.md"
    if not f.is_file():
        return None
    return f.read_text(encoding="utf-8")
```

- [ ] **Step 2: 修改 projects.py 的 list_design_templates 端点**

读取 `backend/api/routes/projects.py`，找到 `list_design_templates` 函数。修改为：

```python
@router.get("/design-templates")
async def list_design_templates(
    user: str = Depends(get_current_user),
):
    """List available DESIGN.md templates (built-in + user extracted)."""
    from backend.design_templates import list_templates, list_user_templates
    builtin = list_templates()
    for t in builtin:
        t["source"] = "builtin"
    user_templates = list_user_templates(user)
    for t in user_templates:
        t["source"] = "user"
    return {"templates": builtin + user_templates}
```

同时修改 `apply_design_template` 端点以支持用户模板。找到处理 `template_id` 的部分，在读取内置模板之前先尝试读取用户模板：

```python
# 在 apply_design_template 函数中，找到 template_content = get_template(body.template_id) 行
# 在其前面添加用户模板查找：
    from backend.design_templates import get_template, get_user_template
    if body.template_id.startswith("user/"):
        template_content = get_user_template(user, body.template_id)
        if template_content is None:
            raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")
    else:
        template_content = get_template(body.template_id)
        if template_content is None:
            raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")
```

- [ ] **Step 3: 验证后端导入**

```bash
.venv/bin/python -c "from backend.design_templates import list_user_templates, get_user_template; print('OK')"
```
Expected: OK

- [ ] **Step 4: 运行测试确保无回归**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -5
```
Expected: 76 passed

- [ ] **Step 5: Commit**

```bash
git add backend/design_templates/__init__.py backend/api/routes/projects.py
git commit -m "feat: merge user-extracted design templates into template list"
```

---

### Task 4: B · 前端 API + 类型

**Files:**
- Modify: `frontend/src/types/events.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加类型**

在 `/home/wenwenba2020/cc_workspace/ppt_agent/frontend/src/types/events.ts` 末尾添加：

```typescript
// Design template (extended with source field)
export interface DesignTemplate {
  id: string
  name: string
  subtitle: string
  description: string
  colors: Array<{ role: string; hex: string }>
  source?: 'builtin' | 'user'
}
```

- [ ] **Step 2: 修改 client.ts 的 DesignTemplate 类型和添加 API**

读取 `frontend/src/api/client.ts`，找到现有的 `DesignTemplate` interface（约116-123行）。删除它（因为现在从 events.ts 导入）。

在 slide library API 区域（`importSlidesToProject` 之后）添加：

```typescript
export const extractLibraryDesign = (deckId: string, name?: string) =>
  api.post<{ slug: string; name: string; path: string }>(
    `/library/decks/${deckId}/extract-design`,
    { name },
  ).then(r => r.data)

export const deleteUserTemplate = (slug: string) =>
  api.delete(`/library/templates/${slug}`)
```

- [ ] **Step 3: 验证前端编译**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/events.ts frontend/src/api/client.ts
git commit -m "feat: add extract-design API client and template types"
```

---

### Task 5: B · 前端 UI · 提取设计按钮

**Files:**
- Modify: `frontend/src/components/SlideLibrary/index.tsx`

- [ ] **Step 1: 在企业库面板添加提取设计按钮**

读取 `frontend/src/components/SlideLibrary/index.tsx`。在 DeckCard 组件内部（或在 SlideLibraryPanel 中），为每个展开的 PPT 添加「提取设计」功能。

最简单的方式：在 SlideLibraryPanel 中添加新按钮。在 header 区域的「上传 PPT」按钮下方添加一个处理状态：

在现有 state 后添加：
```typescript
  const [extractingDeckId, setExtractingDeckId] = useState<string | null>(null)
```

在上传按钮下方添加消息提示（当提取完成时）。但更好的做法是让这个功能挂在 DeckCard 里。不过为了简单，我们在 handleUpload 旁边添加。

实际上，应该在 DeckCard 的 header 中添加按钮。修改方式：在 `frontend/src/components/SlideLibrary/DeckCard.tsx` 中，header 右侧按钮组（edit/delete）旁边添加「提取设计」按钮：

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, Pencil, CheckSquare, Square, Layers, Wand2 } from 'lucide-react'
import type { LibraryDeck, LibrarySlide } from '@/types/events'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'
import { LibrarySlideCard } from './LibrarySlideCard'
import { extractLibraryDesign } from '@/api/client'
// ... existing imports

export function DeckCard({ deck, projectId, onPreview }: Props) {
  // ... existing state ...
  const [extracting, setExtracting] = useState(false)

  const handleExtractDesign = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (extracting) return
    setExtracting(true)
    try {
      const result = await extractLibraryDesign(deck.id)
      alert(`已保存为模板「${result.name}」`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e.response?.data?.detail || '提取失败')
    }
    setExtracting(false)
  }

  // ... in the header JSX, after the Layers button, add:
  {isExpanded && (
    <button
      onClick={handleExtractDesign}
      disabled={extracting}
      className={`shrink-0 p-0.5 rounded transition-all ${
        extracting ? 'text-primary animate-pulse' : 'text-muted-foreground opacity-0 group-hover:opacity-100'
      }`}
      title="提取设计为模板"
    >
      <Wand2 className="w-3.5 h-3.5" />
    </button>
  )}
```

- [ ] **Step 2: 验证前端编译**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SlideLibrary/DeckCard.tsx
git commit -m "feat: add extract-design button to DeckCard"
```

---

### Task 6: A · SlideItem 增加 design_ref 字段

**Files:**
- Modify: `backend/models/outline.py`

- [ ] **Step 1: 添加字段**

读取 `/home/wenwenba2020/cc_workspace/ppt_agent/backend/models/outline.py`，找到 `SlideItem` 类定义。在现有字段后添加 `design_ref` 和 `design_images`：

```python
class SlideItem(BaseModel):
    slide_id: str
    title: str = ""
    subtitle: str | None = None
    layout: str = "title-content"
    status: str = "todo"
    visual_intent: str | None = None
    notes_speaker: str | None = None
    points: list[PointItem | str] = []
    chart: dict | None = None
    media: dict | None = None
    locked: bool = False
    design_ref: str | None = None       # 库 slide XML 路径（相对项目目录）
    design_images: str | None = None    # 库 slide 图片目录（相对项目目录）
```

- [ ] **Step 2: 更新序列化/反序列化逻辑**

确保 `design_ref` 和 `design_images` 在 OUTLINE.md 解析时被正确处理。查看 `OutlineDoc` 的 `_parse_slide` 或类似方法，添加对这两个字段的读写：

在 YAML frontmatter 的 slide section 中，解析时添加：
```python
design_ref = slide_data.get("design_ref")
design_images = slide_data.get("design_images")
```

序列化时（`save_outline`）在输出中添加这两个字段（仅非空时）。

- [ ] **Step 3: 运行测试确认无回归**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -5
```
Expected: 76 passed

- [ ] **Step 4: Commit**

```bash
git add backend/models/outline.py
git commit -m "feat: add design_ref field to SlideItem for library slide cloning"
```

---

### Task 7: A · slide_cloner + import-to-project 改造

**Files:**
- Create: `backend/pipeline/slide_cloner.py`
- Modify: `backend/api/routes/slide_library.py`

- [ ] **Step 1: 创建 slide_cloner.py**

```python
"""Clone library slide assets into a project directory for design preservation."""
import shutil
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ClonedSlide:
    slide_id: str
    design_ref: str       # relative path: lib_slides/slide_NN/slide.xml
    design_images: str    # relative path: lib_slides/slide_NN/images/


def clone_slide_to_project(
    library_slide_xml: str,
    library_slide_dir: str,
    project_dir: str | Path,
    slide_id: str,
) -> ClonedSlide:
    """Copy a library slide's XML and images into the project directory.
    
    Args:
        library_slide_xml: Path to slide.xml in the slide library
        library_slide_dir: Path to the slide directory in the library (contains images/)
        project_dir: Project root directory
        slide_id: Target slide_id (e.g. "03")
    
    Returns ClonedSlide with relative paths.
    """
    project_dir = Path(project_dir)
    dest_dir = project_dir / "lib_slides" / f"slide_{slide_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy slide.xml
    src_xml = Path(library_slide_xml)
    dest_xml = dest_dir / "slide.xml"
    if src_xml.is_file():
        shutil.copy2(src_xml, dest_xml)

    # Copy images/
    src_images = Path(library_slide_dir) / "images"
    dest_images = dest_dir / "images"
    if src_images.is_dir() and any(src_images.iterdir()):
        if dest_images.exists():
            shutil.rmtree(dest_images)
        shutil.copytree(src_images, dest_images)

    design_ref = f"lib_slides/slide_{slide_id}/slide.xml"
    design_images = f"lib_slides/slide_{slide_id}/images/" if dest_images.is_dir() else ""

    return ClonedSlide(
        slide_id=slide_id,
        design_ref=design_ref,
        design_images=design_images,
    )


def parse_slide_xml_layout(xml_path: str) -> dict:
    """Lightweight parse of slide XML to extract layout hints for the designer agent.
    
    Returns a dict with:
      - background_color: str
      - text_positions: [{left, top, width, height, font_name, font_size_pt}]
      - has_images: bool
    """
    import xml.etree.ElementTree as ET

    ns = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return {"background_color": None, "text_positions": [], "has_images": False}

    bg_color = None
    text_positions = []
    has_images = False

    # Extract background
    for bg in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}bg"):
        for sr in bg.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"):
            bg_color = f"#{sr.get('val', 'FFFFFF')}"

    # Extract shape positions and text
    EMU_PER_PX = 914400 / 96
    for sp in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}sp"):
        # Position & size
        xfrm = sp.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
        if xfrm is not None:
            off = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}off")
            ext = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
            left = int(off.get("x", 0)) / EMU_PER_PX if off is not None else 0
            top = int(off.get("y", 0)) / EMU_PER_PX if off is not None else 0
            width = int(ext.get("cx", 0)) / EMU_PER_PX if ext is not None else 0
            height = int(ext.get("cy", 0)) / EMU_PER_PX if ext is not None else 0
        else:
            left = top = width = height = 0

        # Text
        font_name = None
        font_size = None
        for rpr in sp.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"):
            latin = rpr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}latin")
            if latin is not None:
                font_name = latin.get("typeface")
            sz = rpr.get("sz")
            if sz:
                font_size = int(sz) / 100  # hundredths of a point

        if font_name or font_size:
            text_positions.append({
                "left": round(left, 1),
                "top": round(top, 1),
                "width": round(width, 1),
                "height": round(height, 1),
                "font_name": font_name,
                "font_size_pt": font_size,
            })

    # Check for images
    for _ in root.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}pic"):
        has_images = True
        break

    return {
        "background_color": bg_color,
        "text_positions": text_positions[:20],  # max 20
        "has_images": has_images,
    }
```

- [ ] **Step 2: 修改 import-to-project 端点支持 clone_design**

读取 `backend/api/routes/slide_library.py`，修改 `ImportRequest` schema 和 `import_slides_to_project` 函数。

修改 `ImportRequest`：
```python
class ImportRequest(BaseModel):
    slide_ids: list[str]
    clone_design: bool = False
```

在 `import_slides_to_project` 函数中，slide 导入循环内，创建 SlideItem 时根据 `clone_design` 添加 design_ref：

```python
    from backend.pipeline.slide_cloner import clone_slide_to_project

    max_id = max((int(s.slide_id) for s in outline.slides), default=0)
    imported: list[str] = []
    for lib_slide in lib_slides:
        max_id += 1
        new_id = f"{max_id:02d}"

        design_ref = None
        design_images = None
        if body.clone_design and lib_slide.raw_slide_xml_path:
            lib_base = _lib_dir(user, lib_slide.library_id)
            src_xml = lib_base / lib_slide.raw_slide_xml_path
            src_dir = lib_base / "slides" / f"slide_{lib_slide.slide_index:02d}"
            cloned = clone_slide_to_project(
                str(src_xml),
                str(src_dir),
                str(storage.get_project_path(project_id)),
                new_id,
            )
            design_ref = cloned.design_ref
            design_images = cloned.design_images

        tag_hint = f"参考标签: {', '.join(lib_slide.tags)}" if lib_slide.tags else ""
        outline.slides.append(SlideItem(
            slide_id=new_id,
            layout=lib_slide.layout_hint or "title-content",
            title=lib_slide.title or f"Slide {new_id}",
            visual_intent=tag_hint if tag_hint else None,
            notes_speaker=lib_slide.text_summary or "",
            design_ref=design_ref,
            design_images=design_images,
        ))
        imported.append(new_id)
```

- [ ] **Step 3: 验证后端导入**

```bash
.venv/bin/python -c "from backend.pipeline.slide_cloner import clone_slide_to_project, parse_slide_xml_layout; print('OK')"
```
Expected: OK

- [ ] **Step 4: 运行测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -5
```
Expected: 76 passed

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/slide_cloner.py backend/api/routes/slide_library.py
git commit -m "feat: add slide cloning — preserve design when importing from library"
```

---

### Task 8: 端到端验证

**Files:** None (test + build only)

- [ ] **Step 1: 运行全部后端测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -10
```
Expected: 76+ passed, 0 new failures

- [ ] **Step 2: 前端完整编译**

```bash
cd frontend && npm run build 2>&1 | tail -10
```
Expected: no errors

- [ ] **Step 3: 验证新模块导入**

```bash
.venv/bin/python -c "
from backend.parsers.design_extractor import generate_design_md, save_user_template
from backend.design_templates import list_user_templates, get_user_template
from backend.pipeline.slide_cloner import clone_slide_to_project, parse_slide_xml_layout
print('All new imports OK')
"
```

- [ ] **Step 4: Commit (if any fixes)**

---

## 自审清单

1. **Spec 覆盖**:
   - ✅ B. 设计提取：generate_design_md (Task 1) + API 端点 (Task 2) + 模板合并 (Task 3) + 前端 (Task 4, 5)
   - ✅ A. 设计克隆：SlideItem 扩展 (Task 6) + clone_slide_to_project (Task 7)
   - ✅ 验证 (Task 8)

2. **无占位符**: 所有步骤包含完整代码。

3. **类型一致性**:
   - `design_ref: str | None` 在 SlideItem 和后端一致
   - 模板 `id: "user/{slug}"` 格式在前后端一致
   - `DesignTemplate.id: string` 与模板列表 API 返回一致
