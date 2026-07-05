# 企业幻灯片库 · 四项增强 · 设计规格

> 创建于 2026-05-15 · 状态：设计完成

## 概述

在已合并的企业幻灯片库基础上，增加 A) AI 智能打标签、B) 批量导入、D) 预览增强、E) 智能推荐 四项功能。

## A. AI 智能打标签

**流程**：上传完成后，逐页调 Qwen 3.5 9B（最便宜）分析标题+文本，返回 2-4 个标签。

**实现方式**：同步逐页串行，复用 `backend/agents/llm_client.py`。标签生成函数放在 `slide_extractor.py` 中，与文本提取同步执行。20 页约 4-6 秒。

**Prompt 设计**：
```
根据以下幻灯片内容，生成 2-4 个中文标签（逗号分隔）。
标签应简短（2-6 字），描述页面类型和主题。
常见标签：封面、目录、团队介绍、数据图表、时间线、对比分析、引用名言、总结、产品介绍、流程图

标题：{title}
内容：{text_summary[:500]}
```

**标签后处理**：AI 返回的标签合并到 `SIMPLE_LAYOUT_RULES` 推测结果中，去重后写入 `LibrarySlide.tags`。

## B. 批量导入

**前端改动**：
- `slideLibraryStore` 新增 `selectionMode: boolean`、`selectedSlideIds: Set<string>`、`toggleSelect(slideId)`、`selectAll()`、`clearSelection()`
- `LibrarySlideCard` 选中模式下显示 checkbox，点击卡片切换选中
- `DeckCard` 展开时 header 显示"全选"checkbox
- `SlideLibraryPanel` 底部固定栏：选中 N 页时显示"导入 N 页到项目"按钮

**后端**：无需修改，`POST /library/import-to-project/{project_id}` 已支持 `slide_ids: list[str]`。

## D. Slide 预览增强

**新建组件** `SlidePreviewModal.tsx`：
- 点击缩略图打开 Dialog/Modal
- 左侧：SVG 缩略图 2x 渲染（宽 720px）
- 右侧：完整 text_summary、标签、编号、布局类型
- 支持键盘 Esc 关闭、点击遮罩关闭

**LibrarySlideCard 改动**：缩略图添加 `onClick → openPreview(slide)`，光标改为 pointer。

## E. 智能推荐

**后端**：新增 `GET /library/recommend/{project_id}` 端点

**实现**：
- 读取项目 `OUTLINE.md`，提取所有 slide 的 title 拼接为项目摘要
- 对库中所有 slides，调 embedding API（OpenRouter 的 `text-embedding-3-small`）计算向量
- 计算项目摘要与每个库 slide 的余弦相似度（本地 numpy）
- 返回 top 10，附带相似度分数

若 embedding API 不可用，降级为 LLM prompt 打分（Qwen，逐 slide 评估相关性 1-5 分）。

**前端**：`SlideLibraryPanel` 顶部新增"为你推荐"折叠区，显示推荐 slide 卡片（简化版，带"导入"按钮）。

## 与现有系统边界

- A 复用 `llm_client.py`，不影响其他智能体
- B 纯前端，后端无改动
- D 纯前端新组件
- E 新增 1 个端点，不修改现有 API
- 四项均不修改 OUTLINE.md 格式、LangGraph 状态机、数据库 schema
