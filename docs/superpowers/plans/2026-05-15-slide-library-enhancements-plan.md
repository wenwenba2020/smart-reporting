# 企业幻灯片库 · 四项增强 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为企业幻灯片库增加 AI 智能打标签、批量导入、预览增强、智能推荐四项功能。

**Architecture:** A/E 复用现有 `llm_client.py`（OpenRouter OpenAI SDK），B/D 纯前端。四项独立实施，互不阻塞。推荐顺序：B → D → A → E（由简到难）。

**Tech Stack:** Python/FastAPI + OpenRouter (Qwen3.5-9B, text-embedding-3-small) + React/Zustand + numpy

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `backend/parsers/slide_extractor.py` | A: 新增 AI 标签生成函数 |
| Modify | `backend/api/routes/slide_library.py` | A: 上传后调用标签生成 + E: 新增推荐端点 |
| Create | `frontend/src/components/SlideLibrary/SlidePreviewModal.tsx` | D: 大尺寸预览 Modal |
| Modify | `frontend/src/components/SlideLibrary/LibrarySlideCard.tsx` | B: 选中模式 + D: 缩略图点击 |
| Modify | `frontend/src/components/SlideLibrary/DeckCard.tsx` | B: 全选 checkbox |
| Modify | `frontend/src/components/SlideLibrary/index.tsx` | B: 批量导入栏 + E: 推荐区域 |
| Modify | `frontend/src/stores/slideLibraryStore.ts` | B: 多选状态管理 |
| Modify | `frontend/src/api/client.ts` | E: 新增推荐 API 函数 |
| Modify | `frontend/src/types/events.ts` | E: 新增推荐类型 |

---

### Task 1: B · 批量导入 · store + 多选状态

**Files:**
- Modify: `frontend/src/stores/slideLibraryStore.ts:28-29`

- [ ] **Step 1: 在 slideLibraryStore 中添加多选状态**

Edit `frontend/src/stores/slideLibraryStore.ts` — 在 interface 中添加：

```typescript
interface SlideLibraryState {
  // ... existing fields ...
  selectionMode: boolean
  selectedSlideIds: Set<string>

  // ... existing actions ...
  enterSelection: () => void
  exitSelection: () => void
  toggleSelect: (slideId: string) => void
  selectAllInDeck: (slideIds: string[]) => void
  getSelectedCount: () => number
}
```

在 `create` 的初始状态中添加：

```typescript
  selectionMode: false,
  selectedSlideIds: new Set(),
```

在 actions 中添加：

```typescript
  enterSelection: () => set({ selectionMode: true, selectedSlideIds: new Set() }),

  exitSelection: () => set({ selectionMode: false, selectedSlideIds: new Set() }),

  toggleSelect: (slideId: string) => {
    const next = new Set(get().selectedSlideIds)
    if (next.has(slideId)) {
      next.delete(slideId)
    } else {
      next.add(slideId)
    }
    set({ selectedSlideIds: next })
  },

  selectAllInDeck: (slideIds: string[]) => {
    const current = get().selectedSlideIds
    const allSelected = slideIds.every((id) => current.has(id))
    const next = new Set(current)
    if (allSelected) {
      for (const id of slideIds) next.delete(id)
    } else {
      for (const id of slideIds) next.add(id)
    }
    set({ selectedSlideIds: next })
  },

  getSelectedCount: () => get().selectedSlideIds.size,
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/slideLibraryStore.ts
git commit -m "feat: add multi-select state to slideLibrary store"
```

---

### Task 2: B · 批量导入 · LibrarySlideCard checkbox

**Files:**
- Modify: `frontend/src/components/SlideLibrary/LibrarySlideCard.tsx`

- [ ] **Step 1: 添加 checkbox 和选中模式**

Edit `LibrarySlideCard.tsx` — 在 Props 中去掉 `onImport`，改为使用 store：

```tsx
import { useState } from 'react'
import { Plus, Check, Square, CheckSquare } from 'lucide-react'
import type { LibrarySlide } from '@/types/events'
import { TagEditor } from './TagEditor'
import { useSlideLibraryStore } from '@/stores/slideLibraryStore'

interface Props {
  slide: LibrarySlide
  onImport?: (slideId: string) => void
  onPreview?: (slide: LibrarySlide) => void
}

export function LibrarySlideCard({ slide, onImport, onPreview }: Props) {
  const patchSlide = useSlideLibraryStore((s) => s.patchSlide)
  const selectionMode = useSlideLibraryStore((s) => s.selectionMode)
  const selectedSlideIds = useSlideLibraryStore((s) => s.selectedSlideIds)
  const toggleSelect = useSlideLibraryStore((s) => s.toggleSelect)
  const [imported, setImported] = useState(false)
  const [localNumber, setLocalNumber] = useState(slide.slide_number || '')

  const isSelected = selectedSlideIds.has(slide.id)

  const handleNumberBlur = () => {
    if (localNumber !== (slide.slide_number || '')) {
      patchSlide(slide.id, { slide_number: localNumber || null })
    }
  }

  const handleTagsChange = (tags: string[]) => {
    patchSlide(slide.id, { tags })
  }

  const handleImport = () => {
    if (imported) return
    onImport?.(slide.id)
    setImported(true)
    setTimeout(() => setImported(false), 2000)
  }

  const handleCardClick = () => {
    if (selectionMode) {
      toggleSelect(slide.id)
    }
  }

  const handleThumbnailClick = (e: React.MouseEvent) => {
    if (selectionMode) {
      toggleSelect(slide.id)
    } else {
      e.stopPropagation()
      onPreview?.(slide)
    }
  }

  return (
    <div
      onClick={handleCardClick}
      className={`group flex gap-2 p-2 rounded-lg transition-all border ${
        isSelected
          ? 'bg-primary/5 border-primary/30'
          : 'hover:bg-accent/30 border-transparent hover:border-border/30'
      } ${selectionMode ? 'cursor-pointer' : ''}`}
    >
      {/* Checkbox in selection mode */}
      {selectionMode && (
        <div className="shrink-0 self-center">
          {isSelected ? (
            <CheckSquare className="w-4 h-4 text-primary" />
          ) : (
            <Square className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      )}

      {/* Thumbnail — click opens preview */}
      <div
        className="w-28 h-[63px] shrink-0 bg-muted/30 rounded-md overflow-hidden border border-border/20 cursor-pointer hover:ring-1 hover:ring-primary/30 transition-all"
        onClick={handleThumbnailClick}
      >
        {slide.thumbnail_url ? (
          <img
            src={slide.thumbnail_url}
            alt={slide.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-muted-foreground">
            {slide.slide_index}
          </div>
        )}
      </div>

      {/* Info (same as before) */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div className="flex items-center gap-1.5">
          <input
            value={localNumber}
            onChange={(e) => setLocalNumber(e.target.value)}
            onBlur={handleNumberBlur}
            placeholder={`#${slide.slide_index}`}
            className="text-[10px] font-mono bg-transparent border-b border-transparent hover:border-border/30 focus:border-primary/30 outline-none w-12 text-muted-foreground"
          />
          <p className="text-xs font-medium truncate flex-1">{slide.title}</p>
        </div>

        <TagEditor tags={slide.tags} onTagsChange={handleTagsChange} />

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground capitalize">{slide.layout_hint || 'slide'}</span>
          <span className="text-[10px] text-muted-foreground/50">
            {(slide.text_summary || '').slice(0, 40)}...
          </span>
        </div>
      </div>

      {/* Import button (hidden in selection mode) */}
      {!selectionMode && (
        <button
          onClick={handleImport}
          disabled={imported}
          className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-all p-1 rounded-md hover:bg-primary/10 text-primary disabled:opacity-100 disabled:text-green-500"
          title="插入到项目"
        >
          {imported ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SlideLibrary/LibrarySlideCard.tsx
git commit -m "feat: add multi-select and preview click to LibrarySlideCard"
```

---

### Task 3: B · 批量导入 · DeckCard 全选 + 批量导入栏

**Files:**
- Modify: `frontend/src/components/SlideLibrary/DeckCard.tsx`
- Modify: `frontend/src/components/SlideLibrary/index.tsx`

- [ ] **Step 1: DeckCard 添加全选 checkbox 和选中模式入口**

Edit `DeckCard.tsx` — 在 header 区域的 `ChevronDown/ChevronRight` 旁边添加：

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, Pencil, CheckSquare, Square, Layers } from 'lucide-react'
// ... existing imports ...

export function DeckCard({ deck, projectId }: Props) {
  // ... existing state ...
  const selectionMode = useSlideLibraryStore((s) => s.selectionMode)
  const selectedSlideIds = useSlideLibraryStore((s) => s.selectedSlideIds)
  const toggleSelect = useSlideLibraryStore((s) => s.toggleSelect)
  const selectAllInDeck = useSlideLibraryStore((s) => s.selectAllInDeck)
  const enterSelection = useSlideLibraryStore((s) => s.enterSelection)
  const exitSelection = useSlideLibraryStore((s) => s.exitSelection)

  const isExpanded = expandedDeckId === deck.id
  const slideIds = expandedSlides.map((s) => s.id)
  const allSelected = slideIds.length > 0 && slideIds.every((id) => selectedSlideIds.has(id))

  // ... existing handlers ...

  return (
    <div className="group border border-border/20 rounded-xl overflow-hidden bg-card/30 transition-all">
      {/* Header */}
      <div className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-accent/20 transition-colors">
        {/* Expand/collapse button */}
        <button onClick={handleToggle} className="text-muted-foreground shrink-0">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Select all checkbox (visible when expanded and in selection mode) */}
        {isExpanded && selectionMode && (
          <button
            onClick={(e) => { e.stopPropagation(); selectAllInDeck(slideIds) }}
            className="shrink-0 text-muted-foreground hover:text-primary transition-colors"
          >
            {allSelected ? <CheckSquare className="w-4 h-4 text-primary" /> : <Square className="w-4 h-4" />}
          </button>
        )}

        {/* ... rest of header (name, slide count, edit, delete) same as before ... */}

        {/* Enter/exit selection mode button (visible when expanded) */}
        {isExpanded && (
          <button
            onClick={(e) => { e.stopPropagation(); selectionMode ? exitSelection() : enterSelection() }}
            className={`shrink-0 p-0.5 rounded transition-all ${
              selectionMode ? 'text-primary bg-primary/10' : 'text-muted-foreground opacity-0 group-hover:opacity-100'
            }`}
            title={selectionMode ? '退出选择' : '批量选择'}
          >
            <Layers className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Expanded slides */}
      {isExpanded && (
        <div className="border-t border-border/10 divide-y divide-border/10">
          {expandedSlides.length === 0 ? (
            <p className="text-xs text-muted-foreground p-4 text-center">加载中...</p>
          ) : (
            expandedSlides.map((slide) => (
              <LibrarySlideCard
                key={slide.id}
                slide={slide}
                onImport={handleImportSlide}
                onPreview={onPreview}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
```

注意：DeckCard 需要接收 `onPreview` prop 并传递给 `LibrarySlideCard`。在 Props 中添加：

```typescript
interface Props {
  deck: LibraryDeck
  projectId: string | null
  onPreview?: (slide: LibrarySlide) => void
}
```

然后将 `onPreview` 传给每个 `LibrarySlideCard`：
```tsx
<LibrarySlideCard
  key={slide.id}
  slide={slide}
  onImport={handleImportSlide}
  onPreview={onPreview}
/>
```

- [ ] **Step 2: SlideLibraryPanel 添加批量导入操作栏**

Edit `index.tsx` — 在搜索栏下方、列表上方添加，并在 store 中导入新 actions：

```tsx
import { useState } from 'react'
// ... existing imports ...
import { CheckSquare, X } from 'lucide-react'

export function SlideLibraryPanel({ onPreview }: { onPreview?: (slide: LibrarySlide) => void }) {
  // ... existing state and refs ...

  const {
    // ... existing destructure ...
    selectionMode,
    selectedSlideIds,
    enterSelection,
    exitSelection,
    importToProject,
    setSearchQuery,
  } = useSlideLibraryStore()

  const selectedCount = selectedSlideIds.size

  const handleBatchImport = async () => {
    if (!currentProject?.id || selectedCount === 0) return
    const ids = Array.from(selectedSlideIds)
    await importToProject(currentProject.id, ids)
    exitSelection()
    addMessage?.('system', `已从企业库导入 ${ids.length} 页到项目`)
  }
```

在搜索框下方（Upload button 上方）添加选择模式下的操作栏：

```tsx
        {/* Selection mode bar */}
        {selectionMode && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-primary/5 border border-primary/20">
            <span className="text-xs text-primary font-medium">
              已选 {selectedCount} 页
            </span>
            <div className="flex-1" />
            <button
              onClick={exitSelection}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 px-2 py-1 rounded-md hover:bg-accent/30 transition-colors"
            >
              <X className="w-3 h-3" />
              取消
            </button>
            <button
              onClick={handleBatchImport}
              disabled={selectedCount === 0 || !currentProject}
              className="text-xs bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1 px-3 py-1 rounded-md transition-colors disabled:opacity-50"
            >
              <CheckSquare className="w-3 h-3" />
              导入 {selectedCount} 页
            </button>
          </div>
        )}
```

- [ ] **Step 3: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SlideLibrary/DeckCard.tsx frontend/src/components/SlideLibrary/index.tsx
git commit -m "feat: add batch select and import UI to slide library panel"
```

---

### Task 4: D · 预览增强 · SlidePreviewModal

**Files:**
- Create: `frontend/src/components/SlideLibrary/SlidePreviewModal.tsx`

- [ ] **Step 1: 创建 SlidePreviewModal 组件**

```tsx
import { useEffect, useCallback } from 'react'
import { X, Tag, Hash, Layout } from 'lucide-react'
import type { LibrarySlide } from '@/types/events'

interface Props {
  slide: LibrarySlide | null
  onClose: () => void
}

export function SlidePreviewModal({ slide, onClose }: Props) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (slide) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = ''
      }
    }
  }, [slide, handleKeyDown])

  if (!slide) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border/30 rounded-2xl shadow-2xl max-w-4xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-border/30 shrink-0">
          <h3 className="text-base font-semibold flex-1 truncate">{slide.title}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-accent/30 text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-[1fr_300px] gap-6">
            {/* Large thumbnail */}
            <div className="bg-muted/20 rounded-xl border border-border/20 overflow-hidden">
              {slide.thumbnail_url ? (
                <img
                  src={slide.thumbnail_url}
                  alt={slide.title}
                  className="w-full h-auto"
                />
              ) : (
                <div className="aspect-video flex items-center justify-center text-muted-foreground text-sm">
                  (无缩略图)
                </div>
              )}
            </div>

            {/* Meta panel */}
            <div className="space-y-4">
              {/* Slide number */}
              <div className="flex items-center gap-2 text-sm">
                <Hash className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-muted-foreground">编号</span>
                <span className="font-mono font-medium">
                  {slide.slide_number || `#${slide.slide_index}`}
                </span>
              </div>

              {/* Layout hint */}
              <div className="flex items-center gap-2 text-sm">
                <Layout className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-muted-foreground">布局</span>
                <span className="capitalize">{slide.layout_hint || '通用'}</span>
              </div>

              {/* Tags */}
              <div className="flex items-start gap-2 text-sm">
                <Tag className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                <span className="text-muted-foreground">标签</span>
                <div className="flex flex-wrap gap-1">
                  {slide.tags.length > 0 ? slide.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full"
                    >
                      {tag}
                    </span>
                  )) : (
                    <span className="text-[10px] text-muted-foreground/50">无标签</span>
                  )}
                </div>
              </div>

              {/* Full text content */}
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  文本内容
                </h4>
                <div className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto bg-muted/10 rounded-lg p-3 border border-border/20">
                  {slide.text_summary || '(无文本内容)'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 在 SlideLibraryPanel 中集成预览**

Edit `index.tsx` — 添加预览状态和 Modal 渲染：

```tsx
import { SlidePreviewModal } from './SlidePreviewModal'
// ...

export function SlideLibraryPanel() {
  // ... existing state ...
  const [previewSlide, setPreviewSlide] = useState<LibrarySlide | null>(null)

  // ... existing handlers ...

  // In the return JSX, add after the closing div of slide list:
  return (
    <div className="flex flex-col h-full">
      {/* ... existing content ... */}

      {/* Preview Modal */}
      {previewSlide && (
        <SlidePreviewModal
          slide={previewSlide}
          onClose={() => setPreviewSlide(null)}
        />
      )}
    </div>
  )
}
```

然后将 `onPreview={setPreviewSlide}` 传给每个 `DeckCard`：

```tsx
filtered.map((deck) => (
  <DeckCard
    key={deck.id}
    deck={deck}
    projectId={currentProject?.id ?? null}
    onPreview={setPreviewSlide}
  />
))
```

- [ ] **Step 3: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SlideLibrary/SlidePreviewModal.tsx frontend/src/components/SlideLibrary/index.tsx
git commit -m "feat: add slide preview modal with full text and meta"
```

---

### Task 5: A · AI 智能打标签 · 后端

**Files:**
- Modify: `backend/parsers/slide_extractor.py`
- Modify: `backend/api/routes/slide_library.py`

- [ ] **Step 1: 在 slide_extractor.py 中添加 AI 标签生成函数**

在 `slide_extractor.py` 末尾追加：

```python
def generate_ai_tags(title: str, text_summary: str, existing_hint: str = "") -> list[str]:
    """用轻量 LLM 为单页幻灯片生成 2-4 个中文标签。失败时降级为空列表。"""
    prompt = f"""根据以下幻灯片内容，生成 2-4 个中文标签（逗号分隔）。
标签应简短（2-6 字），描述页面类型和主题。
常见标签：封面、目录、团队介绍、数据图表、时间线、对比分析、引用名言、总结、产品介绍、流程图、SWOT分析、用户画像、商业模式、路线图、KPI指标

标题：{title or '(无)'}
内容：{(text_summary or '')[:500]}

只返回逗号分隔的标签，不要其他文字。"""

    try:
        # 延迟导入避免循环引用
        from backend.agents.llm_client import chat
        result = chat(
            model="qwen/qwen3.5-9b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=64,
            extra_body={"enable_thinking": False},
        )
        # 解析：按逗号/顿号/中文逗号分割
        tags = [t.strip() for t in re.split(r"[,，、]", result) if t.strip()]
        # 合并 regex 推测的 layout hint
        if existing_hint and existing_hint not in tags:
            tags.append(existing_hint)
        return tags[:6]  # 最多 6 个标签
    except Exception:
        return [existing_hint] if existing_hint else []
```

在 `extract_slides_from_pptx` 函数中，`layout_hint` 计算之后、构造 `ExtractedSlide` 之前添加：

```python
        layout_hint = _guess_layout(title, text_summary, idx, total)

        # AI 标签生成
        tags = generate_ai_tags(title, text_summary, layout_hint)
```

修改 `ExtractedSlide` dataclass 添加 `tags` 字段：

```python
@dataclass
class ExtractedSlide:
    slide_index: int
    title: str
    text_summary: str
    slide_xml_rel: str
    thumbnail_rel: str
    layout_hint: str
    tags: list[str] = field(default_factory=list)  # AI generated tags
```

并在 `extract_slides_from_pptx` 返回的 `ExtractedSlide` 构造中添加 `tags=tags`。

- [ ] **Step 2: 在 slide_library.py 上传端点中传入 tags**

Edit `backend/api/routes/slide_library.py:70-80` — 在构造 `LibrarySlide` 时添加 `tags`：

```python
        lib_slide = LibrarySlide(
            library_id=library.id,
            slide_index=e.slide_index,
            title=e.title,
            text_summary=e.text_summary,
            tags=e.tags,  # AI generated
            thumbnail_path=e.thumbnail_rel,
            raw_slide_xml_path=e.slide_xml_rel,
            layout_hint=e.layout_hint,
        )
```

- [ ] **Step 3: 验证后端导入和基础测试**

Run: `.venv/bin/python -c "
from backend.parsers.slide_extractor import generate_ai_tags, ExtractedSlide
print('Import OK')
print(f'ExtractedSlide fields: {[f for f in ExtractedSlide.__dataclass_fields__]}')
"`

Expected: Import OK + shows `tags` in field list

- [ ] **Step 4: 运行后端测试确保无回归**

Run: `.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -5`
Expected: 76 passed, 3 skipped

- [ ] **Step 5: Commit**

```bash
git add backend/parsers/slide_extractor.py backend/api/routes/slide_library.py
git commit -m "feat: add AI auto-tagging for uploaded slide library decks"
```

---

### Task 6: E · 智能推荐 · 后端端点

**Files:**
- Modify: `backend/api/routes/slide_library.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/events.ts`

- [ ] **Step 1: 添加推荐端点**

在 `backend/api/routes/slide_library.py` 的 import 区域添加：

```python
import numpy as np
from backend.agents.llm_client import chat, get_client
from backend.models.outline import load_outline
from backend.storage.file_manager import ProjectStorage
```

在文件末尾（`import-to-project` 端点之后）添加：

```python
def _embed(text: str) -> list[float]:
    """用 OpenRouter embedding API 将文本转为向量。"""
    client = get_client()
    text = text[:8000]  # embedding model max input ~8K tokens
    resp = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=[text],
        timeout=30,
    )
    return resp.data[0].embedding


def _cosine(a: list[float], b: list[float]) -> float:
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-10))


@router.get("/recommend/{project_id}")
async def recommend_slides(
    project_id: str,
    limit: int = 10,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于项目上下文，推荐库中最匹配的 slides。"""
    # 验证 project 归属
    project = await db.get(Project, project_id)
    if not project or project.user_id != user:
        raise HTTPException(status_code=404, detail="Project not found")

    # 读取项目 OUTLINE 提取所有标题
    storage = ProjectStorage.get()
    outline_path = storage.get_project_path(project_id) / "OUTLINE.md"
    project_summary = project.name or ""
    if outline_path.exists():
        try:
            outline = load_outline(str(outline_path))
            titles = [s.title for s in outline.slides if s.title]
            if titles:
                project_summary = f"{project.name}: {', '.join(titles[:10])}"
        except Exception:
            pass

    # 获取库中所有 slides
    result = await db.execute(
        select(LibrarySlide).join(SlideLibrary).where(
            SlideLibrary.user_id == user
        )
    )
    all_slides = list(result.scalars().all())
    if not all_slides:
        return {"project_id": project_id, "recommendations": []}

    # 用项目摘要做 embedding，然后计算与每个 slide 的相似度
    try:
        proj_embed = _embed(project_summary)
        scored: list[tuple[float, dict]] = []
        for s in all_slides:
            slide_text = f"{s.title or ''} {s.text_summary or ''}"[:2000]
            slide_embed = _embed(slide_text)
            score = _cosine(proj_embed, slide_embed)
            scored.append((score, {
                "id": s.id,
                "library_id": s.library_id,
                "slide_index": s.slide_index,
                "slide_number": s.slide_number,
                "title": s.title,
                "text_summary": (s.text_summary or "")[:200],
                "tags": s.tags or [],
                "thumbnail_url": f"/project-files/.slide_library/{user}/decks/{s.library_id}/slides/slide_{s.slide_index:02d}/thumbnail.svg",
                "layout_hint": s.layout_hint,
                "score": round(score, 3),
            }))

        scored.sort(key=lambda x: x[0], reverse=True)
        recommendations = [item for _, item in scored[:limit] if item["score"] > 0.3]
        return {"project_id": project_id, "recommendations": recommendations}

    except Exception as e:
        # 降级：返回空推荐列表，不阻塞其他功能
        return {
            "project_id": project_id,
            "recommendations": [],
            "error": f"Recommendation unavailable: {str(e)}",
        }
```

- [ ] **Step 2: 添加 numpy 依赖检查**

Run: `.venv/bin/python -c "import numpy; print(numpy.__version__)"`

如果 numpy 未安装：
```bash
.venv/bin/pip install numpy
```

- [ ] **Step 3: 验证端点导入**

Run: `.venv/bin/python -c "from backend.api.routes.slide_library import router; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/slide_library.py
git commit -m "feat: add slide recommendation endpoint via embedding similarity"
```

---

### Task 7: E · 智能推荐 · 前端类型 + API

**Files:**
- Modify: `frontend/src/types/events.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加推荐类型**

Edit `frontend/src/types/events.ts` — 在文件末尾追加：

```typescript
// Slide recommendation
export interface RecommendedSlide extends LibrarySlide {
  score: number
}

export interface RecommendationResult {
  project_id: string
  recommendations: RecommendedSlide[]
  error?: string
}
```

- [ ] **Step 2: 添加推荐 API 函数**

Edit `frontend/src/api/client.ts` — 在末尾 `export default api` 之前追加：

```typescript
import type { RecommendationResult } from '@/types/events'

export const getRecommendedSlides = (projectId: string, limit?: number) => {
  const params = new URLSearchParams()
  if (limit) params.set('limit', String(limit))
  const qs = params.toString()
  return api.get<RecommendationResult>(
    `/library/recommend/${projectId}${qs ? '?' + qs : ''}`,
    { timeout: 30000 },
  ).then(r => r.data)
}
```

- [ ] **Step 3: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/events.ts frontend/src/api/client.ts
git commit -m "feat: add recommendation types and API client"
```

---

### Task 8: E · 智能推荐 · 前端 UI

**Files:**
- Modify: `frontend/src/components/SlideLibrary/index.tsx`

- [ ] **Step 1: 在 SlideLibraryPanel 顶部添加推荐区域**

在 `index.tsx` 中添加推荐数据加载和展示：

```tsx
import { useState, useEffect } from 'react'
import { Sparkles, Plus } from 'lucide-react'
import type { LibrarySlide, RecommendedSlide } from '@/types/events'
import { getRecommendedSlides } from '@/api/client'
// ...

export function SlideLibraryPanel() {
  // ... existing state ...
  const [recommendations, setRecommendations] = useState<RecommendedSlide[]>([])
  const [recsLoading, setRecsLoading] = useState(false)
  const [recsExpanded, setRecsExpanded] = useState(true)

  // Load recommendations when project changes
  useEffect(() => {
    if (!currentProject?.id) return
    setRecsLoading(true)
    getRecommendedSlides(currentProject.id, 5)
      .then((res) => {
        setRecommendations(res.recommendations || [])
        setRecsLoading(false)
      })
      .catch(() => setRecsLoading(false))
  }, [currentProject?.id])

  const handleRecImport = async (slideId: string) => {
    if (!currentProject?.id) return
    await importToProject(currentProject.id, [slideId])
    // Remove from recommendations after import
    setRecommendations((prev) => prev.filter((r) => r.id !== slideId))
  }
```

在搜索框之前（Header 下面）添加推荐区域：

```tsx
      {/* Smart Recommendations */}
      {recommendations.length > 0 && (
        <div className="px-3 pb-2">
          <button
            onClick={() => setRecsExpanded(!recsExpanded)}
            className="flex items-center gap-1.5 text-[10px] font-semibold text-primary/80 uppercase tracking-wider mb-1.5 hover:text-primary transition-colors"
          >
            <Sparkles className="w-3 h-3" />
            为你推荐
            <span className="text-[10px] text-muted-foreground normal-case">
              ({recommendations.length})
            </span>
          </button>
          {recsExpanded && (
            <div className="space-y-1">
              {recommendations.slice(0, 5).map((rec) => (
                <div
                  key={rec.id}
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-accent/20 transition-colors group border border-border/10"
                >
                  <div className="w-16 h-9 shrink-0 bg-muted/20 rounded overflow-hidden border border-border/10">
                    {rec.thumbnail_url ? (
                      <img src={rec.thumbnail_url} alt={rec.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[8px] text-muted-foreground">
                        {rec.slide_index}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-medium truncate">{rec.title}</p>
                    <p className="text-[9px] text-muted-foreground">
                      {rec.layout_hint} · 匹配 {(rec.score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <button
                    onClick={() => handleRecImport(rec.id)}
                    className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-primary/10 text-primary transition-all"
                    title="导入"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
```

- [ ] **Step 2: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -10`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SlideLibrary/index.tsx
git commit -m "feat: add smart recommendation panel to slide library"
```

---

### Task 9: 端到端验证

**Files:** None (test + build)

- [ ] **Step 1: 运行后端测试**

```bash
.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
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
from backend.parsers.slide_extractor import generate_ai_tags
from backend.api.routes.slide_library import router
import numpy
print('All new imports OK')
"
```
Expected: All new imports OK

---

## 自审清单

1. **Spec 覆盖**: 逐条对照 spec：
   - ✅ A: AI 标签生成 → Task 5
   - ✅ B: 批量导入 → Tasks 1-3
   - ✅ D: 预览增强 → Task 4
   - ✅ E: 智能推荐 → Tasks 6-8

2. **无占位符**: 所有步骤包含完整代码。

3. **类型一致性**:
   - `RecommendedSlide extends LibrarySlide` — 前端类型兼容
   - `generate_ai_tags` 返回 `list[str]`，与 `LibrarySlide.tags: JSON` → `list[str]` 一致
   - `onPreview` prop 类型 `LibrarySlide | null` 在所有组件间一致
   - store 中 `selectedSlideIds: Set<string>` 与 `LibrarySlide.id: string` 类型一致

4. **独立性**: 四项功能可单独交付，互不阻塞。
