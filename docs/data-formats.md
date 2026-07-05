# 数据格式规范

> 写任何涉及 OUTLINE.md 或 DESIGN.md 的代码前必读。

---

## OUTLINE.md 完整格式

每个项目的核心状态文件，路径：`projects/{project_id}/OUTLINE.md`。

所有智能体共享读写此文件，写入时必须加文件锁（见 `docs/known-pitfalls.md` 坑6）。

```markdown
---
title: 2025年Q4季度汇报
format: ppt169
total_slides: 10
status: in_progress
created_at: 2026-04-15T10:00:00+08:00
updated_at: 2026-04-15T14:30:00+08:00
planner_version: "1.0"
design_ref: ./DESIGN.md
---

## Slides

### [01] 封面
layout: cover
status: done
title: 2025年第四季度业绩汇报
subtitle: 深度赋智科技 · 战略发展部
visual_intent: 全图深色背景，标题居中大字，副标题下方细线分割
notes_speaker: 本次汇报重点聚焦Q4营收增长和明年战略方向，预计30分钟
media:
  background: user://uploads/office-bg.jpg
locked: false

---

### [03] 营收分析
layout: data-chart
status: done
title: 营收同比增长23%
points:
  - Q4总营收¥3,280万，同比+23%
  - 新客贡献率首次超过40%
  - 华南区超额完成目标118%
chart:
  type: bar-grouped
  data_ref: ./data/q4-revenue.csv
  caption: 近五季度营收对比（单位：万元）
visual_intent: 左侧文字+要点列表，右侧柱状图，数字突出显示为强调色
media: ~
notes_speaker: 重点强调华南区的超额表现，这是今年的亮点
locked: false

---

### [05] 市场占有率
layout: two-col
status: generating
title: 市场份额变化
points:
  - 华东市场占比从18%提升至24%
  - 竞争对手A份额下降3个百分点
chart:
  type: pie
  data_ref: inline
  data:
    - ["我方", 24]
    - ["竞品A", 31]
    - ["竞品B", 22]
    - ["其他", 23]
visual_intent: 左栏要点，右栏饼图，配色与主题一致
media: ~
notes_speaker: ""
locked: false
```

---

## status 字段状态机

```
todo → generating → done
                 ↗
         (用户手动)
              ↓
           locked
```

| 值 | 含义 | 谁写入 |
|----|------|--------|
| `todo` | 规划师生成大纲后的初始态 | 规划师 |
| `generating` | 编辑师正在生成 SVG | 编辑师（开始前写入） |
| `done` | SVG 已生成，可预览 | 编辑师（完成后写入） |
| `locked` | 用户手动锁定，AI 不得修改 | 前端用户操作 |

**规则**：AI 智能体发现某页 `locked: true`，必须跳过该页，不做任何修改。

---

## layout 字段完整枚举

必须从此列表选择，不得自造新值：

| 值 | 用途 |
|----|------|
| `cover` | 封面 |
| `title-only` | 章节标题页（大标题居中，无正文） |
| `title-content` | 标题+正文列表（最常用） |
| `two-col` | 两栏并列 |
| `three-col` | 三栏并列 |
| `data-chart` | 文字+图表（左右或上下） |
| `full-image` | 全图背景（文字叠加） |
| `quote` | 大引文（居中大字） |
| `timeline` | 时间线 |
| `comparison` | 对比表格 |
| `team` | 团队介绍（头像+简介） |
| `toc` | 目录页 |
| `blank` | 空白（完全自定义，谨慎使用） |

---

## media 字段 URI 协议

| 前缀 | 含义 | 示例 |
|------|------|------|
| `user://uploads/` | 用户上传的原始文件 | `user://uploads/logo.png` |
| `user://extract/` | 从参考 PPT 中提取的图片 | `user://extract/slide_02_img.png` |
| `ai://generated/` | 效果师 AI 生成的图片 | `ai://generated/slide_03_bg.png` |
| `ai://charts/` | pyecharts 生成的图表 SVG | `ai://charts/slide_03_bar.svg` |
| `~` | 本页无媒体需求 | `media: ~` |

---

## chart 字段规范

```yaml
chart:
  type: bar-grouped      # 图表类型（见下方列表）
  data_ref: inline       # inline = 数据内嵌；或文件路径如 ./data/revenue.csv
  data:                  # data_ref=inline 时必填
    - ["Q1", 1200]
    - ["Q2", 1500]
  caption: 近五季度营收  # 图表标题/说明
```

支持的图表类型：
- `bar` 单系列柱状图
- `bar-grouped` 多系列柱状图
- `line` 折线图
- `pie` 饼图
- `scatter` 散点图
- `radar` 雷达图
- `funnel` 漏斗图

---

## Pydantic 模型参考

```python
# backend/models/outline.py

from typing import Optional, Literal, List, Any
from pydantic import BaseModel, Field

class ChartConfig(BaseModel):
    type: str
    data_ref: str = "inline"
    data: Optional[List[Any]] = None
    caption: Optional[str] = None

class MediaConfig(BaseModel):
    background: Optional[str] = None
    image: Optional[str] = None

SlideStatus = Literal["todo", "generating", "done", "locked"]

LayoutType = Literal[
    "cover", "title-only", "title-content", "two-col", "three-col",
    "data-chart", "full-image", "quote", "timeline", "comparison",
    "team", "toc", "blank"
]

class SlideItem(BaseModel):
    slide_id: str                           # "01", "02", ...
    layout: LayoutType
    status: SlideStatus = "todo"
    title: str
    subtitle: Optional[str] = None
    points: List[str] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    visual_intent: Optional[str] = None
    notes_speaker: str = ""
    media: Optional[MediaConfig] = None
    locked: bool = False

class OutlineMeta(BaseModel):
    title: str
    format: str = "ppt169"
    total_slides: int
    status: str = "draft"
    created_at: str
    updated_at: str
    planner_version: str = "1.0"
    design_ref: str = "./DESIGN.md"

class OutlineDoc(BaseModel):
    meta: OutlineMeta
    slides: List[SlideItem]
    
    def get_slide(self, slide_id: str) -> Optional[SlideItem]:
        for s in self.slides:
            if s.slide_id == slide_id:
                return s
        return None
    
    def get_summary(self) -> List[dict]:
        """规划师诊断模式用，只返回结构摘要，不含 SVG"""
        return [{
            "slide_id": s.slide_id,
            "title": s.title,
            "layout": s.layout,
            "status": s.status,
            "points_count": len(s.points),
            "has_chart": s.chart is not None,
            "has_media": s.media is not None,
            "locked": s.locked,
        } for s in self.slides]
```

---

## DESIGN.md 完整格式

路径：`projects/{project_id}/DESIGN.md`，由设计师智能体在初始化时生成。

```markdown
---
template_name: 商务蓝
template_id: business-blue
version: "1.0"
---

## Visual Theme & Atmosphere
严谨商务风格。深蓝主色，留白充足，数据驱动。适合季报、战略汇报、投资路演。

## Color Palette & Roles
- Primary: #1E3A5F（深蓝，标题、强调）
- Secondary: #4A90D9（中蓝，图表主色）
- Accent: #F5A623（橙金，重要数字、CTA）
- Surface: #FFFFFF（白色，页面背景）
- Surface-Alt: #F4F7FA（浅灰，卡片背景）
- Text-Primary: #1A1A2E（深色，正文）
- Text-Secondary: #6B7280（中灰，辅助说明）
- Border: #E5E7EB（浅灰边框）

## Typography Rules
- 标题字体: 阿里巴巴普惠体 Bold（TTF）
- 正文字体: 阿里巴巴普惠体 Regular（TTF）
- 英文配套: Inter Regular/Bold（TTF）
- 标题字号（PPT pt）: 封面主标题 44pt，页标题 32pt，节标题 24pt
- 正文字号: 正文 18pt，说明 14pt，标注 11pt
- 行距: 1.4

## Layout Principles
- 页面边距: 上下 1.5cm，左右 2cm
- 内容区: 21.33cm 宽（16:9 减去边距）
- 元素间距基准: 0.5cm

## Component Stylings
- 要点列表: 圆点用 Secondary 色，首行缩进 0，行间距 1.2
- 数据卡片: Surface-Alt 背景，1px Border 描边，圆角 4pt
- 图表配色序列: Secondary > Accent > #5DCAA5 > #F0997B

## SVG Canvas Size
- viewBox: 0 0 960 540（PPT 16:9 标准，单位 px）
- 所有 SVG 页面必须使用此尺寸

## Do's and Don'ts
- DO: 每页不超过 5 个视觉元素
- DO: 大数字用 Accent 色放大强调
- DON'T: 不使用超过 3 种颜色
- DON'T: 标题不超过 15 个字
```

---

## 项目工作区目录结构

```
projects/{project_id}/
├── DESIGN.md              # 设计语言（设计师初始化时生成）
├── OUTLINE.md             # 内容结构（规划师维护）
├── sources/               # 用户上传的原始文件
│   ├── document.pdf
│   └── reference.pptx
├── assets/                # 处理后的媒体资产
│   ├── uploads/           # 用户上传图片（原始）
│   ├── extracted/         # 从参考 PPT 提取的图片
│   └── ai_generated/      # AI 生成的图片
├── data/                  # 图表数据文件
│   └── revenue.csv
├── svg_output/            # 每页 SVG 中间产物
│   ├── slide_01.svg
│   └── slide_02.svg
├── fonts/                 # 该项目的子集化字体（按实际用字裁剪）
│   └── AlibabaPuHuiTi-Regular-subset.ttf
├── snapshots/             # 版本快照
│   ├── v001_outline_confirmed.json
│   └── v002_generation_complete.json
└── exports/               # 最终输出
    ├── native.pptx        # DrawingML 原生可编辑版
    └── reference_svg.pptx # SVG 图片参考版
```
