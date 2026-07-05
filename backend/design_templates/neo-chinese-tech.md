# 新中式科技 · Neo-Chinese Tech

## 1. Visual Theme & Atmosphere
新中式极简 · 山水意境 · 科技克制。以水墨山水为灵感，深蓝夜空为底，青绿色呼应自然，金色点缀不超过5%。避免传统装饰元素（龙纹、祥云），追求抽象留白而非具象符号。适合高端科技品牌发布、文化科技公司路演、艺术品数字化展示。

## 2. Color Palette & Roles
- **Primary** `#0F172A` — 深夜蓝 · 科技底色、标题、背景
- **Secondary** `#1F2937` — 深灰蓝 · 次级区块、卡片底
- **Accent** `#22C55E` — 青绿 · 山水意象、CTA、关键数据
- **Accent-Soft** `#4ADE80` — 浅青绿 · 渐变终点、高亮
- **Gold** `#C6A75E` — 金色点缀 · 不超过5%元素
- **Ink-Strong** `#E5E7EB` — 浓墨 · 主要正文
- **Ink-Medium** `#9CA3AF` — 中墨 · 辅助说明
- **Ink-Light** `#6B7280` — 淡墨 · 时间戳、muted
- **Surface** `#111827` — 卡片底色
- **Divider** `rgba(255,255,255,0.06)` — 细线分隔

## 3. Typography (emphasis → 样式映射)
- **hero** (封面): 64pt / Noto Sans SC Bold / 渐变填充（Primary→透明）或纯白
- **h1** (页标题): 32pt / Noto Sans SC Medium / Ink-Strong
- **h2** (区块标题): 24pt / Noto Sans SC Medium / Ink-Medium
- **h3** (要点标题): 20pt / Noto Sans SC Regular / Ink-Strong
- **body** (正文): 16pt / Noto Sans SC Regular / Ink-Strong
- **highlight** (强调): 18pt Medium / Accent
- **number** (数据): 56pt Bold / Accent / Inter 字族 + 可选渐变
- **caption** (说明): 13pt / Ink-Light
- **muted**: 14pt / Ink-Light / opacity 0.7
- **quote** (引言): 20pt Italic / Ink-Medium / 衬线体可选

## 4. Layout Principles (PPT 960×540)
- 画布尺寸: 960 × 540
- 左右内边距: 72px（比商务蓝更宽，强调留白）
- 块间纵向间距: 32px（疏朗透气）
- **cover**: 标题居中偏左，背景使用 Primary→Secondary 渐变或纯色；右下角可放抽象山形波纹装饰（低透明度 Accent）；无底部色条，改用极细 Divider 线
- **title-content**: 标题左上角，下方 40px 处 1px Divider 短线（宽 80px）；内容区从 y=120 开始，大量留白
- **two-col**: 左右区块用 80px 间隔，不用竖线分隔（以空白代线条）
- **data-chart**: 数据居中偏左，右侧留大面积空白形成"山水"构图感
- **quote**: 左侧大引号装饰 " 或 "（36pt Ink-Light），文字右对，底部留白

## 5. Depth & Elevation
- 卡片: 圆角 12px / fill Surface / 边框 1px rgba(255,255,255,0.05) / 无阴影（扁平浮悬感）
- 强调块: 圆角 12px / fill 渐变 Primary→透明 / 白色文字 + glow 效果
- 图片占位: 圆角 8px / 无边框 / fill 透明 / 可用极淡 Accent 色蒙版
- 水平分隔线: 1px Divider 色 / 宽度 60-120px（短而克制）
- 装饰元素: 抽象山形/波纹（path）使用 Accent 或 Ink-Light 色带透明度 0.05-0.15

## 6. Do's and Don'ts
- ✓ 以留白代边框，避免密集元素
- ✓ 使用渐变过渡（Primary→透明），模拟水墨晕染
- ✓ 装饰元素用抽象几何（山、波、雾），禁具象传统图案
- ✓ 金色 Gold 仅用于 ≤5% 元素点缀
- ✓ 数字用 Inter 字族 +Accent 色或渐变
- ✓ 动画用 fade-in + 向上轻移（ mist 效果）
- ✗ 禁用高饱和红色（破坏宁静感）
- ✗ 禁用粗-bold 大块文字
- ✗ 禁用重度阴影（保持轻浮悬感）
- ✗ 禁用 emoji 和卡通图标
- ✗ 禁用传统装饰纹样（龙、云、回纹等）

## 7. Agent Prompt Guide
生成 SVG 时：cover 页背景**必用渐变**（linearGradient Primary→Secondary 或 Primary→透明）；装饰只用抽象山形波纹（<path d="M0,..."/>）带极低透明度；整体留白占比 ≥40%；字体全用 Noto Sans SC（思源黑体）无衬线；数字可用 Inter；禁用实心重阴影，改用透明度分层；Gold 金色极度克制，仅点缀标题装饰线或 CTA。
