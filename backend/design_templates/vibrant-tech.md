# 活力科技 · Vibrant Tech

## 1. Visual Theme & Atmosphere
未来科技 · 活力鲜明 · 有朝气。紫蓝渐变 + 霓虹强调色，适合 SaaS 产品发布、创业路演、前沿技术介绍。视觉冲击力强但不过于花哨。

## 2. Color Palette & Roles
- **Primary** `#6366F1` — 靛紫 · 品牌、渐变起点
- **Primary-Dark** `#3730A3` — 深靛 · 渐变终点
- **Secondary** `#06B6D4` — 青蓝 · 数据、图表
- **Accent** `#F59E0B` — 琥珀 · CTA、关键数据
- **Success** `#10B981` — 翠绿 · 成功/正向指标
- **Surface** `#FFFFFF` — 默认背景
- **Surface-Dark** `#0F172A` — 深色主题备选
- **Surface-Alt** `#F1F5F9` — 浅灰蓝 · 卡片底
- **Text-Primary** `#0F172A`
- **Text-Secondary** `#64748B`
- **Text-On-Dark** `#F8FAFC`

## 3. Typography (emphasis → 样式映射)
- **hero**: 64pt / AlibabaPuHuiTi Bold / 可选渐变填充（Primary→Primary-Dark）
- **h1**: 40pt / AlibabaPuHuiTi Bold / Primary
- **h2**: 28pt / AlibabaPuHuiTi Bold / Text-Primary
- **h3**: 22pt / AlibabaPuHuiTi Medium / Primary
- **body**: 18pt / AlibabaPuHuiTi Regular / Text-Primary
- **highlight**: 20pt Bold / Accent
- **number**: 56pt Bold / Inter / 渐变填充（Primary→Secondary）
- **tag**: 12pt Bold / White on Primary pill
- **caption**: 13pt / Text-Secondary
- **muted**: 14pt / Text-Secondary opacity 0.8

## 4. Layout Principles (PPT 960×540)
- 画布 960 × 540，左右内边距 60px
- **cover**: 使用全幅渐变背景 (linearGradient Primary→Primary-Dark)，白色标题；右侧点缀几何装饰（圆环/三角/圆点）
- **title-content**: 标题左上 + 右侧大号数字/图标；每个要点用独立圆角卡片（Surface-Alt 底 + 1px Divider 边）
- **data-chart**: 超大号数据（60pt+）+ 下方 secondary 色趋势线
- **feature-grid**: 3x1 或 2x2 卡片网格，每卡片左上角 32px 圆形图标底色
- 装饰元素: 圆环、三角、折线、圆点阵列（透明度 0.1-0.3）

## 5. Depth & Elevation
- 卡片: 圆角 16px (现代大圆角) / fill Surface-Alt / 阴影 0 4px 12px rgba(99,102,241,0.08)
- 强调卡: 圆角 16px / fill linear Primary→Primary-Dark / 白色文字
- 图标底: 圆角 12px / fill Primary opacity 0.1 / 内含 Primary 色 SVG path
- 图片占位: 圆角 12px / 虚线 Primary 色 / fill Surface-Alt

## 6. Do's and Don'ts
- ✓ 大胆使用渐变（但限于标题和封面背景）
- ✓ 每页至少 2 个几何装饰元素（圆/三角/折线）
- ✓ 数字用 Inter + 加粗 + 可选渐变
- ✓ 按钮/tag 用 pill shape（大圆角胶囊）
- ✓ 阴影使用 Primary 色带透明度（不用纯灰阴影）
- ✗ 禁用大面积纯黑（用 Surface-Dark 深靛代替）
- ✗ 禁用 Times New Roman 或其他衬线字体
- ✗ 禁用单调中性色（必须有至少 1 处彩色点缀）

## 7. Agent Prompt Guide
生成 SVG 时：cover 页**必用渐变背景**；每页保证至少 2 个几何装饰（圆/三角/折线）；数据和大号数字必须用 Primary 或 Accent 色强调；圆角一律 ≥ 12px（偏大圆角）；字体都用无衬线 AlibabaPuHuiTi / Inter。
