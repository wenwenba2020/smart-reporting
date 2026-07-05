# 企业幻灯片库 · 设计规格

> 创建于 2026-05-09 · 状态：设计完成

## 概述

在现有 PPT 智能助手中新增"企业幻灯片库"功能。每个用户拥有独立的幻灯片库，上传 PPT 后自动逐页提取并存储（含原始 slide XML + SVG 缩略图 + 文本提取），用户可为每页编号、打标签，后续生成新 PPT 时可通过对话 @ 引用或面板操作复用库中 slide。

## 数据模型

### slide_libraries 表（每个上传的 PPT 一条记录）

| 列 | 类型 | 说明 |
|---|---|---|
| id | String (PK) | UUID hex |
| user_id | String (非空) | 归属用户 |
| name | String (非空) | PPT 名称（用户可修改） |
| original_filename | String (非空) | 上传时的原始文件名 |
| slide_count | Integer (默认 0) | 总页数 |
| created_at | DateTime (tz) | 上传时间 |
| updated_at | DateTime (tz) | 最后更新时间 |

### library_slides 表（每一页一条记录）

| 列 | 类型 | 说明 |
|---|---|---|
| id | String (PK) | UUID hex |
| library_id | String (FK → slide_libraries.id) | 所属 PPT |
| slide_index | Integer | 原始页码（1-based） |
| slide_number | String (可空) | 用户自定义编号 |
| title | String (可空) | 提取的标题文本 |
| text_summary | String (可空) | 提取的全部文本内容 |
| tags | JSON (默认 []) | 用户自由标签 list[str] |
| thumbnail_path | String (可空) | SVG 缩略图相对路径 |
| raw_slide_xml_path | String (可空) | 单页 XML 相对路径 |
| layout_hint | String (可空) | AI 推测的布局类型 |
| created_at | DateTime (tz) | 创建时间 |

### 标签规则
- 自由文本标签，逗号分隔输入
- 存储为 JSON list[str]
- 支持按标签搜索（模糊匹配）

## 存储结构

```
projects/.slide_library/{user_id}/
├── decks/
│   └── {library_id}/
│       ├── original.pptx              # 完整原始 PPTX 文件
│       └── slides/
│           ├── slide_01/
│           │   ├── slide.xml          # 原始 slide XML（从 PPTX ZIP 中提取）
│           │   ├── thumbnail.svg      # SVG 缩略图
│           │   └── images/            # 该页关联图片
│           ├── slide_02/
│           └── ...
```

- 所有路径使用 `user_id` 隔离，复用现有 `LocalStorage` 的路径安全机制
- `thumbnail.svg` 通过现有 `svg_to_pptx.py` 的逆向流程生成（PPTX slide → SVG）
- `slide.xml` 直接从原始 PPTX ZIP 中提取对应的 `ppt/slides/slide{N}.xml`

## API 设计

所有端点使用 JWT 认证，自动从 token 获取 user_id。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/library/upload` | 上传 PPTX 到库，自动解析提取 |
| GET | `/library/decks` | 列出当前用户的所有 PPT |
| GET | `/library/decks/{id}` | 获取单个 PPT 详情（含所有 slides） |
| DELETE | `/library/decks/{id}` | 删除 PPT 及其所有 slides |
| PATCH | `/library/decks/{id}` | 修改 PPT 名称 |
| PATCH | `/library/slides/{id}` | 修改单页标签 / 编号 |
| GET | `/library/slides/search?tag=X&q=Y` | 搜索 slides（按标签/文本模糊匹配） |
| POST | `/projects/{pid}/slides/import-from-library` | 将库中 slide 插入到当前项目 |

### 上传流程

```
[Browser] --POST /library/upload (multipart .pptx)-->
  1. 保存原始 PPTX → .slide_library/{user_id}/decks/{lib_id}/original.pptx
  2. 解压 PPTX ZIP，遍历所有 slide{N}.xml
  3. 每页:
     a. 提取 slide XML → slides/slide_{NN}/slide.xml
     b. 提取关联图片 → slides/slide_{NN}/images/
     c. 通过 pyecharts/现有工具生成 SVG 缩略图
     d. 提取文本（python-pptx 逐 shape 读取）
     e. 写入 library_slides 表
  4. 写 slide_libraries 表
  5. 返回 library_id + slide 列表
```

### 导入到项目流程

```
POST /projects/{pid}/slides/import-from-library
  body: { slide_ids: ["uuid1", "uuid2"] }

  1. 验证 project 和 library_slide 归属（同 user_id）
  2. 读取每个 slide 的 slide.xml + 关联素材
  3. 在目标 PPTX 中创建新 slide（python-pptx slide.export / clone）
  4. 更新 OUTLINE.md，添加对应 SlideItem（layout 设为 slide 的 layout_hint）
  5. 返回新 slide 的 slide_id 列表
```

## 前端组件

### App.tsx 修改
- `RightTab` 类型从 `'slides' | 'style'` 扩展为 `'slides' | 'style' | 'library'`
- 新增 tab：`{rightTab === 'library' && <SlideLibraryPanel />}`

### SlideLibraryPanel 组件树

```
<SlideLibraryPanel>
  ├── 顶部操作栏
  │   ├── "上传 PPT" 按钮（虚线边框拖拽区 + 隐藏 file input）
  │   └── 搜索框（按标题/标签过滤）
  ├── PPT 列表（ScrollArea）
  │   └── <DeckCard> × N
  │        ├── 展开/折叠箭头
  │        ├── PPT 名称（可编辑）
  │        ├── slide_count 标签
  │        └── 展开后：
  │             └── <LibrarySlideCard> × slide_count
  │                  ├── SVG 缩略图
  │                  ├── 编号（可编辑）
  │                  ├── 标签区（点击编辑，逗号分隔）
  │                  └── "插入到项目" 按钮
  └── 空状态：提示"上传你的第一个企业 PPT"
```

### 对话 @ 引用交互
- 输入框中输入 `@` 触发 `SlideSearch` 弹出面板
- 搜索/浏览库中 slides，选中后生成引用 token（如 `@slide:lib_id/slide_index`）
- AI 收到引用后自动读取对应 slide 的结构化内容，融入生成上下文

### Zustand Store（slideLibraryStore）

```typescript
interface SlideLibraryStore {
  decks: LibraryDeck[];
  selectedDeckId: string | null;
  searchQuery: string;
  selectedSlideIds: Set<string>;
  // actions
  loadDecks: () => Promise<void>;
  uploadDeck: (file: File) => Promise<void>;
  deleteDeck: (id: string) => Promise<void>;
  updateSlide: (id: string, data: Partial<LibrarySlide>) => Promise<void>;
  importSlides: (slideIds: string[]) => Promise<void>;
}
```

## 解析器：slide_extractor.py

新增 `backend/parsers/slide_extractor.py`，核心功能：

```python
def extract_slides_from_pptx(pptx_path: str, output_dir: str) -> list[ExtractedSlide]:
    """
    从 PPTX 文件逐页提取：
    - 文本内容（所有 text_frame 的文本）
    - slide XML（从 ZIP 中提取原始 slide{N}.xml）
    - 关联图片（复制到 images/ 子目录）
    - SVG 缩略图（python-pptx slide → SVG 近似渲染）
    返回 list[ExtractedSlide]
    """

def generate_thumbnail(slide_xml_path: str, output_svg_path: str):
    """基于现有 ppt-master 工具生成 SVG 缩略图"""
```

## 与现有系统的边界

- **不修改** OUTLINE.md 格式，导入时 lib slide → SlideItem 是单向转换
- **共用** LocalStorage 的安全路径机制（`_safe_resolve`）
- **复用** `ppt_parser.py` 的图片提取逻辑，但不修改其 API
- **不依赖** Celery — 上传提取为同步操作（单 PPT 通常 < 50 页，秒级完成）
- **不修改** LangGraph 状态机 — @ 引用通过 `user_message` 文本透传，AI 在规划阶段自行解析

## 约束与取舍

- 上传限制：单个 PPTX ≤ 50MB，复用现有 `MAX_FILE_SIZE`
- 标签不设预设值，完全自由文本，逗号分隔输入即存储
- 搜索为本地模糊匹配（SQLite LIKE + JSON 字段），不引入向量数据库
- SVG 缩略图生成依赖现有 python-pptx 渲染能力，复杂效果可能有损失（在面板中仅作预览用）
- slide 导入到项目时，如果目标项目尚在 `idle` 阶段，直接插入 OUTLINE.md；如果已在设计阶段，不支持插入（需要警告）
