"""
LLM Prompt Templates

All prompts are written in Chinese for the target LLM. Each uses Python
str.format() placeholders identified by {curly_braces}.
"""

# --- Intent Recognition ---

INTENT_RECOGNITION_PROMPT = """你是一个智能报告平台的意图识别模块。你的任务是根据用户的查询和当前可用的数据源摘要，判断用户想要执行的操作意图。

## 数据源摘要
{data_summary}

## 用户查询
{user_query}

## 任务
请分析用户查询，输出一个 JSON 对象，包含以下字段：
- intent: 意图类型，可选值: "create_report"（创建报告）、"query_data"（查询数据）、"fill_section"（填报章节）、"chat"（闲聊/一般问题）
- confidence: 置信度，0.0 到 1.0 之间的浮点数
- report_type: 如果意图是创建报告，指定报告类型（如 "PPT"、"Word"、"PDF"）；否则为 null
- scenario: 如果意图是创建报告，指定场景名称；否则为 null
- reasoning: 简短的推理说明

请只输出 JSON，不要包含其他内容。"""

# --- Intent Recognition V2 (for SmartFill engine) ---

INTENT_RECOGNITION_V2_PROMPT = """你是一个智能报告平台的意图识别引擎。请根据用户的自然语言查询和可用的数据源，识别用户想要生成的报告意图。

## 可用数据源摘要
{data_summary}

## 用户查询
{user_query}

## 任务
请分析上述信息，输出一个 JSON 对象，包含以下字段：
- report_type: 报告类型，如 "周报"、"月报"、"KPI报告"、"项目进展"、"销售业绩"、"会议纪要" 等
- category: 报告所属类别，如 "进度类"、"指标类"、"分析类"、"总结类"、"评估类"
- period: 报告覆盖的时间周期，如 "本周"、"本月"、"Q3"、"2026年度"；如无法判断则为空字符串
- scope: 报告覆盖的范围，如 "团队"、"个人"、"部门"、"公司"、"项目"；如无法判断则为空字符串
- key_themes: 报告涉及的关键主题列表，从数据源和查询中提取

请只输出 JSON，不要包含其他内容。"""

# --- Summarization ---

SUMMARIZE_PROMPT = """你是一个专业的报告撰写助手。请根据以下多个数据源的内容，生成一份简洁、结构化的摘要。

## 数据源内容
{source_contents}

## 任务要求
1. 提取每个数据源的关键信息和要点
2. 识别各数据源之间的关联和共同主题
3. 以结构化 Markdown 格式输出摘要，包含以下部分：
   - 总体概述（2-3 句话）
   - 关键发现（使用无序列表）
   - 数据来源汇总（表格形式，包含来源名称、主要内容、可信度评估）

请确保摘要信息准确、客观、不添加原文中没有的事实。"""

# --- Section Fill ---

SECTION_FILL_PROMPT = """你是一个智能报告填报助手。请根据数据源内容，为指定的报告章节生成专业、结构化的内容。

## 报告模板信息
- 模板名称：{template_name}
- 模板描述：{template_description}

## 当前章节信息
- 章节标题：{section_title}
- 章节描述：{section_description}
- 建议长度：{suggested_length}

## 可用数据源内容
{source_contents}

## 任务要求
1. 严格按照数据源提供的信息撰写内容，不编造事实
2. 使用专业、正式的语言风格
3. 如果数据不足以填充该章节，明确指出信息缺口
4. 内容结构清晰，使用适当的标题层级（##、###）
5. 如涉及数据指标，使用表格或列表呈现

请直接输出章节内容（Markdown 格式），不要包含前言或后记。"""

# --- Validation ---

VALIDATION_PROMPT = """你是一个报告质量审核专家。请对以下报告内容进行审核验证，检查内容的准确性、完整性和一致性。

## 报告内容
{report_content}

## 原始数据源内容（用于核对）
{source_contents}

## 审核检查项
1. **事实准确性**：报告中的事实陈述是否与数据源一致？是否有编造或曲解的内容？
2. **数据一致性**：报告中的数据指标是否与数据源中的数值一致？
3. **内容完整性**：报告是否涵盖了数据源中的所有关键信息？是否有重要遗漏？
4. **逻辑性**：报告的结构和论证逻辑是否清晰合理？
5. **语言质量**：是否存在错别字、语法错误或不专业的表达？

## 输出格式
请输出一个 JSON 对象，包含以下字段：
- overall_score: 整体评分（1-10）
- checks: 一个对象，键为上述 5 个检查项名称，值为一个包含 "pass"（布尔值）、"score"（1-10 评分）、"issues"（发现的问题列表）的对象
- summary: 审核总结（2-3 句话）
- recommendations: 改进建议列表

请只输出 JSON，不要包含其他内容。"""

# --- Slide Summary ---

SLIDE_SUMMARY_PROMPT = """你是一个 PPT 内容分析助手。请对以下幻灯片的内容进行摘要分析。

## 幻灯片信息
- 序号：第 {slide_index} 页
- 标题：{title}

## 幻灯片文本内容
{text_content}

## 任务要求
1. 用 1-2 句话概括该幻灯片的核心信息
2. 提取 3-5 个关键词
3. 判断该幻灯片的内容类型（如：标题页、目录、内容页、数据图表页、总结页等）

请输出一个 JSON 对象，包含以下字段：
- summary: 幻灯片内容摘要
- keywords: 关键词列表
- slide_type: 内容类型

请只输出 JSON，不要包含其他内容。"""

# --- Chat Command ---

CHAT_COMMAND_PROMPT = """你是一个智能报告平台的对话助手。用户正在查看报告并对某个命令按钮进行了操作，你需要根据报告结构和上下文，理解用户意图并给出回应。

## 当前报告结构
{report_structure}

## 用户执行的命令
{command}

## 上下文信息
{context}

## 任务要求
1. 判断该命令在当前报告上下文中是否合适
2. 如果合适，描述该命令将会执行什么操作以及预期结果
3. 如果不合适，给出解释和建议的替代操作
4. 回复应简洁清晰，面向非技术用户

请直接输出你的回复，使用友好的中文语气。"""
