# 暖色学术 · Warm Academic

## 1. Visual Theme & Atmosphere
温暖稳重 · 人文厚重 · 适合教育、学术、医疗、文化场景。深棕 + 米色的经典组合传递深度和可信度，金色点缀呼应学术气质。

## 2. Color Palette & Roles
- **Primary** `#3D2817` — 深棕 · 标题、品牌
- **Secondary** `#8B5E3C` — 棕褐 · 分隔线、次级
- **Accent** `#D4A574` — 金驼 · 强调、CTA
- **Surface** `#FDFAF5` — 米白 · 默认背景
- **Surface-Alt** `#F0E8DC` — 浅米 · 卡片底
- **Text-Primary** `#2C1810` — 近黑棕
- **Text-Secondary** `#7A5F4A` — 暖灰棕
- **Divider** `#E0D4C4` — 浅米色边框

## 3. Typography (emphasis → 样式映射)
- **hero**: 60pt / Noto Serif SC Bold / Primary (衬线体彰显庄重)
- **h1**: 36pt / Noto Serif SC Bold / Primary
- **h2**: 26pt / Noto Serif SC Medium / Primary
- **h3**: 22pt / AlibabaPuHuiTi Medium / Secondary
- **body**: 18pt / AlibabaPuHuiTi Regular / Text-Primary
- **highlight**: 18pt Bold / Accent
- **quote**: 20pt Italic / Secondary (衬线)
- **caption**: 14pt / Text-Secondary
- **muted**: 13pt / Text-Secondary opacity 0.7

## 4. Layout Principles (PPT 960×540)
- 画布 960 × 540，左右内边距 72px (比商务蓝更宽的留白)
- 块间间距 28px (比商务蓝更疏朗)
- **cover**: 标题居中或左对齐，上下各加 1px Secondary 色水平装饰线，底部可选拉丁文副标题 muted 色
- **title-content**: 页标题左上角，下方 2px Accent 色装饰线（宽 60px），内容区从 y=120
- **two-col**: 中间用一条细长 Secondary 色竖线分隔（而不是空隙）
- **quote**: 左侧大引号装饰 " (48pt 斜体 Accent 色)，文字右侧

## 5. Depth & Elevation
- 卡片: 圆角 4px (比商务蓝更紧凑) / fill Surface-Alt / 边框 1px Divider
- 图片占位: 圆角 0 (方角更经典) / stroke Divider
- 水平装饰线: 1px Secondary 色 / 宽度 40-60px

## 6. Do's and Don'ts
- ✓ 标题用衬线体（Noto Serif SC），正文用无衬线
- ✓ 装饰线用短细线，不用粗色块
- ✓ 引用/名言用斜体 + 大引号
- ✓ 可以用罗马数字 I II III 做编号（更学术）
- ✗ 禁用高饱和度色彩（亮蓝/亮红/亮绿）
- ✗ 禁用 emoji 和卡通图标
- ✗ 禁用大圆角（>8px）和立体阴影

## 7. Agent Prompt Guide
生成 SVG 时：标题必须用衬线字体；整体保持温暖米色基调；Accent 金驼色极度克制；装饰只用细线条和小圆点，禁粗色块。
