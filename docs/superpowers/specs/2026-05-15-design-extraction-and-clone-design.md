# 设计提取为模板 + 单页设计克隆 · 设计规格

> 创建于 2026-05-15 · 状态：设计完成

## 概述

企业幻灯片库目前只提取文本和标签，设计信息未被利用。本次增加两项能力：
- **B. 设计提取为模板**：从上传的 PPTX 中提取配色/字体/排版特征，LLM 生成完整 DESIGN.md，保存为可复用模板
- **A. 单页设计克隆**：导入库中 slide 到项目时，保留原始 slide XML 和图片作为设计参考

---

## B. 设计提取为模板

### 数据流

```
原始 PPTX (磁盘: .slide_library/{user}/decks/{lib_id}/original.pptx)
  ↓ python-pptx: 逐页遍历所有 text run 的 color/font/size
原始数据: {colors: ["#1A2B3C",...], fonts: ["PingFang SC Bold",...], font_sizes: [12,18,24,...], slide_count: 40}
  ↓ 作为 prompt 输入 LLM (qwen/qwen3.5-9b, $0.05/M tokens)
DESIGN.md 完整内容（主题名、氛围、调色板角色映射、排版层级、布局原则、Do/Don't）
  ↓ 保存为 .md 文件
.slide_library/{user_id}/templates/{slug}.md
```

### 存储

```
projects/.slide_library/{user_id}/
  templates/                    ← 新增目录
    dark-tech-slides.md
    consulting-report.md
```

- 模板文件格式与 `backend/design_templates/*.md` 完全一致
- slug 由 LLM 从主题名推测英文，或用户手动指定
- 按 user_id 隔离

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/library/decks/{id}/extract-design` | 提取设计并保存为模板 |
| GET | `/projects/design-templates` | 现有端点，扩展为返回内置 + 用户模板 |
| DELETE | `/library/templates/{slug}` | 删除用户提取的模板 |

**POST extract-design 请求/响应**：

```
Request:  { name?: string }          // 可选自定义模板名
Response: { slug: string, name: string, path: string }
```

**LLM Prompt 设计**：

输入：colors 列表、fonts 列表、slide_count
输出：符合 DESIGN.md 规范的完整 Markdown（7 个 section），LLM 负责：
1. 根据配色推测主题氛围
2. 给颜色分配语义角色（Primary/Secondary/Accent/Surface/Text-*）
3. 从 font_sizes 推断排版层级（hero/h1/h2/h3/body/caption）
4. 生成布局原则和 Do/Don't

### 模板列表合并

`GET /projects/design-templates` 返回：
```json
{
  "templates": [
    // 内置模板（id 不带前缀）
    {"id": "vibrant-tech", "name": "活力科技", "source": "builtin", ...},
    // 用户模板（id 带 user/ 前缀）
    {"id": "user/dark-tech-slides", "name": "暗黑科技幻灯", "source": "user", ...},
  ]
}
```

### 前端

企业库面板中，每个 PPT 展开后 header 增加「提取设计」按钮（Magic/Wand 图标）。点击后：
1. 显示 loading 状态（LLM 生成中，约 3-5s）
2. 成功后弹出提示「已保存为模板『暗黑科技幻灯』」
3. 切换到风格面板可看到新模板

---

## A. 单页设计克隆

### 数据流

```
POST /library/import-to-project/{project_id}
  body: { slide_ids: [...], clone_design: true }

1. 验证 project 归属 + stage == "idle"
2. 逐 slide:
   a. 从库磁盘复制 slide.xml → projects/{pid}/lib_slides/slide_NN/slide.xml
   b. 复制关联图片 → projects/{pid}/lib_slides/slide_NN/images/
   c. 在 OUTLINE.md SlideItem 中添加 design_ref 字段
3. 返回导入结果
```

### OUTLINE.md 扩展

SlideItem 新增可选字段 `design_ref`：

```yaml
### [03] 营收分析
layout: data-chart
title: 营收同比增长23%
design_ref: lib_slides/slide_03/slide.xml    ← 新增
design_images: lib_slides/slide_03/images/   ← 新增
points:
  - ...
```

### 设计师智能体适配

设计师生成 SVG 时，若 slide 有 `design_ref`：
1. 读取 `lib_slides/slide_NN/slide.xml`（原始 OOXML）
2. 解析出：背景色、形状位置/大小、文本框位置、字体/字号、图片占位区域
3. 在 LLM prompt 中追加结构化的布局参考描述
4. 生成 SVG 时保持原始排版结构，替换文本内容为新内容

```python
# 新增辅助函数
def parse_slide_xml_layout(xml_path: str) -> dict:
    """解析 slide XML 返回结构化布局描述：
    {background_color, text_boxes: [{left, top, width, height, font, size}], images: [...]}
    """
```

### 解耦策略

- 若 `clone_design=false`（默认），行为与现有完全一致（纯文本导入）
- 若项目已进入设计阶段（stage != idle），禁止导入

### 前端

LibrarySlideCard 导入按钮旁边增加一个切换开关/checkbox"克隆设计"，默认开启。关闭时只导文本。

---

## 与现有系统边界

- **不修改** OUTLINE.md 格式（只增加可选字段 design_ref）
- **不修改** LangGraph 状态机（design_ref 在设计师环节消费）
- **复用** `ppt_parser.extract_style_info()` 提取配色/字体
- **复用** `list_design_templates()` 和 `apply-design-template` API
- **共享** LLM 客户端 `backend/agents/llm_client.py` (Qwen 9B)
- **不依赖** Celery — 模板提取为同步操作（单次 LLM 调用 3-5s）

## 约束

- 模板 slug 使用文件名安全字符（a-z0-9-），25 字符内
- slide XML 仅在导入时复制一次，后续不自动同步
- 设计提取仅分析文本样式（颜色/字体/字号），不分析形状几何
