# 商务蓝 · Business Navy

## 1. Visual Theme & Atmosphere
专业商务 · 稳重可信 · 数据驱动。深蓝主调传递权威感，金色点缀突出关键信息。高留白表达克制，适合汇报 / 融资 / 年度总结。

## 2. Color Palette & Roles
- **Primary** `#1E3A5F` — 品牌、标题、顶部色条
- **Secondary** `#4A90D9` — 辅助图标、分隔线、数据线
- **Accent** `#F5A623` — CTA、关键数据、强调元素
- **Surface** `#FFFFFF` — 默认背景
- **Surface-Alt** `#F3F6F9` — 卡片底、次级区块
- **Text-Primary** `#1A1A2E` — 正文、标题
- **Text-Secondary** `#6B7280` — 辅助、时间戳、说明
- **Divider** `#E5E7EB` — 分隔线、边框

## 3. Typography (emphasis → 样式映射)
- **hero** (封面): 56pt / AlibabaPuHuiTi Bold / Primary
- **h1** (页标题): 40pt / AlibabaPuHuiTi Bold / White on Primary bar
- **h2** (区块标题): 28pt / AlibabaPuHuiTi Bold / Primary
- **h3** (要点标题): 22pt / AlibabaPuHuiTi Medium / Text-Primary
- **body** (正文): 18pt / AlibabaPuHuiTi Regular / Text-Primary
- **highlight** (强调): 20pt Bold / Accent
- **number** (数据): 48pt Bold / Accent / Inter 字族
- **caption** (说明): 13pt / Text-Secondary
- **muted**: 14pt / Text-Secondary / opacity 0.7

## 4. Layout Principles (PPT 960×540)
- 画布尺寸: 960 × 540
- 左右内边距: 60px
- 顶部内边距: 40px (封面页) / 24px (内容页)
- 块间纵向间距: 24px
- **cover**: 标题左对齐 y=220-260，右下角放 120×120 半透明 Accent 圆做装饰；底部有 6px Accent 色条
- **title-content**: 顶部 0-72px 为 Primary 实色条，内嵌白色 h1 标题；内容区从 y=96 开始
- **two-col**: 左右各 420px 区块，中间 60px 间隔
- **data-chart**: 大号数字锚点在左 1/3 区域，图表在右 2/3
- **timeline**: 横线 y=270 贯穿，节点圆间隔 180px

## 5. Depth & Elevation
- 卡片: 圆角 12px / fill Surface-Alt / 无阴影（扁平）
- 强调块: 圆角 12px / fill Primary / 白色文字
- 图片占位: 圆角 8px / stroke Divider / stroke-dasharray 8,4 / fill Surface-Alt
- 水平分隔线: 1px Divider 色 / 或 4px Accent 短线（强调用）

## 6. Do's and Don'ts
- ✓ 左对齐为主，右对齐只用于数据
- ✓ Accent 金色用于 **≤ 10% 元素**（点睛即可）
- ✓ 数字用 Inter 字族（更有科技感）
- ✓ 标题下加 4px Accent 短装饰线
- ✗ 禁止亮红/亮绿（商务场景不适）
- ✗ 禁用 emoji 图标（用 SVG 几何形状替代）
- ✗ 禁背景渐变（保持克制）

## 7. Agent Prompt Guide
生成 SVG 时：严格按 Typography 把 emphasis 字段映射到字号/字体/色彩；按 Layout Principles 确定元素位置；Accent 色必须克制使用；标题需有视觉层次（色条/装饰线/色块之一）。禁用未在本文件定义的色彩和字体。
