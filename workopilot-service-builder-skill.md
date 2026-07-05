# workopilot service builder

> 来源：https://www.skillhub.cn/skills/workopilot-service-builder  
> 评分：4.6 优秀（AI 评分）｜版本：v1.0.1  
> 作者：Angus wang

帮助开发者创建和集成喔壳(WorkoPilot) AI 能力到业务系统。涵盖创建 AI 服务、配置数字员工、注册 iframe 技能卡片、生成接入代码、提供集成方案、排查对接问题等完整流程。

---

## 什么是喔壳(WorkoPilot)

喔壳是一个企业级 AI 应用平台，提供两种使用模式：

### 模式 1：作为独立的 AI 应用入口

用户通过喔壳 App 或 Web 端直接使用数字员工。

**数字员工 = Agent 聊天智能体 + 业务菜单**

- **支持 Agent 聊天智能体：**
  - MCP (Model Context Protocol) — 数据操作能力
  - 系统提示词配置 — 定制对话行为
  - 技能卡片(Iframe) — UI 交互扩展
  - 知识库 — 领域知识注入

- **提供业务菜单：**
  - 业务历史记录（如报价单历史）
  - 业务功能入口
  - 可配置为应用菜单 iframe 页面

**示例 — 报价助理数字员工：**

```
┌─────────────────────────────────────┐
│ 对话区: 协助用户生成报价单           │
│ "帮我做一份设备采购的报价单"         │
│ → 触发报价卡片...                    │
└─────────────────────────────────────┘
```

**开发者如何定制数字员工：**

- **UI 层**：开发 Iframe 技能卡片（对话中触发）或应用菜单 iframe（固定业务菜单）
- **数据层**：开发 MCP — 连接 ERP 系统、生成报价、保存记录
- **组合**：Iframe(UI) + MCP(数据) = 个性化业务数字员工

### 模式 2：作为 AI 能力提供平台

第三方系统通过集成喔壳能力，快速实现 AI 化。

**提供两类能力：**

- **AI 服务** — 通过 API 接口调用
  - 封装可复用的 AI 能力（文本提取、内容生成、智能分析等）
  - 类似函数调用：`POST /api/aiagent/run`
  - 适合后端系统集成

- **数字员工** — 通过 Iframe 嵌入
  - 将完整的数字员工界面嵌入第三方系统
  - 用户在第三方系统内直接使用喔壳数字员工
  - 适合快速为现有系统增加 AI 对话能力

**典型场景：**

| 场景 | 说明 |
| --- | --- |
| 改造传统系统 | 在 CRM/ERP 系统中嵌入数字员工，增加智能助手 |
| 新开发 AI 应用 | 直接调用喔壳 AI 服务，无需自建 AI 基础设施 |
| 文档智能化 | 调用附件提取服务，自动从合同/发票/简历等文件中提取结构化数据 |
| 混合模式 | 后端调用 AI 服务处理数据，前端嵌入数字员工提供交互 |

---

## 本技能提供什么

本技能帮助开发者使用喔壳的开放 API 和集成能力：

**配置自动化：**
- Python 脚本快速创建 AI 服务、数字员工、技能卡片、附件分类
- 自动化配置，避免手动操作

**代码生成：**
- 生成完整可运行的接入代码
- API 调用示例、Iframe 嵌入代码、MCP 集成模板、附件提取调用示例

**集成指导：**
- 端到端的对接方案和最佳实践
- 区分不同使用模式的实施路径
- 附件分类和提取场景的完整流程

**问题诊断：**
- 排查鉴权、网络、配置等常见问题
- 提供调试方法和解决方案

---

## 核心能力详解

### 1. AI 服务 — 可复用的 AI 能力封装

**定位：** 类似"AI 函数"，封装提示词和输入参数

**典型场景：**
- 文本分析（合同审查、简历筛选、舆情分析）
- 内容生成（报告生成、文案创作、邮件起草）
- 数据转换（非结构化文本 → 结构化 JSON）

**创建流程：** `scripts/create_ai_service.py`

---

### 2. 数字员工 — Agent 智能体 + 业务菜单

**定位：** 完整的对话式 AI 应用

**扩展能力：**
- MCP：数据操作（连接 ERP/CRM/数据库）
- 技能卡片：UI 交互（Iframe 嵌入复杂界面）
- 知识库：领域知识（RAG 检索增强）
- 系统提示词：行为定制

**创建流程：** `scripts/create_digital_employee.py`  
**更新流程：** `scripts/update_digital_employee.py`

---

### 3. 附件分类与提取 — 文档智能化核心能力 ⭐⭐⭐

**定位：** 从文件中自动提取结构化数据，消除手工录入

**核心价值：**
- **使用频率极高** — 90% 的场景使用"直接提取"模式
- **节省人力** — 合同/发票/简历等文件自动提取，不用人工抄写
- **提升准确率** — 避免人工录入的错误和遗漏
- **秒级响应** — 上传即提取，实时填充表单

**两种使用模式：**

| 模式 | 说明 | 使用频率 |
| --- | --- | --- |
| 模式 A：分类 + 提取 | 上传杂乱文件 → 系统识别类型 → 提取数据（文件来源复杂时使用） | 较少 |
| 模式 B：直接提取 | 上传合同 → 指定分类编码 → 提取结构化数据 → 填充表单 | ⭐⭐⭐ 高频 |

**快速示例：**

```javascript
// 合同管理系统 - 用户上传合同后自动填充表单
const result = await fetch(`${BASE_URL}/api/attachment/extract`, {
  method: 'POST',
  // ...
});
```

**两种提取技术：**
- **OCR + LLM** — 扫描件、纯文本（先识别文字再理解）
- **Vision-Language** — 复杂排版、包含表格图表（直接理解）

系统自动选择最优技术，也可手动指定。

**开发流程：**
1. 检查系统是否有目标分类（如"采购合同"）
2. 不存在则创建分类并定义 `ExtractRules`（提取规则）
3. 在业务系统中调用提取接口
4. 获取结构化数据并处理

**关键概念：**
- `AttachmentGroup` — 分组（如"合同"、"财务"、"人力"）
- `AttachmentClassification` — 分类（如"采购合同"、"增值税发票"）
- `ExtractRules` — 提取规则（定义要提取哪些字段，字段的 `description` 决定准确率）

**常见分类：**
- 合同类：采购合同、销售合同、租赁合同
- 财务类：增值税发票、收据、银行流水
- 人力类：简历、身份证、学历证书
- 业务类：订单、报价单、验收单

**创建脚本：** `scripts/create_attachment_classification.py`  
**详细文档：** `references/attachment-classification.md`

---

### 4. Iframe 技能卡片 — UI 扩展

**定位：** 在对话中嵌入自定义 UI，通过 `showCard` 触发。（注意：数字员工旁边的固定业务菜单属于"应用菜单 iframe"，与此不同。）

**使用场景：**
- 在对话中展示复杂界面（报价单预览、表单填写）
- AI 先生成或检索结果，再通过 `showCard` 打开可交互卡片

**注册流程：** `scripts/register_iframe_card.py`

---

### 5. 文档服务 — 文件处理

**定位：** 文档格式转换和处理

**能力：**
- Markdown/HTML 转 PDF
- OCR 识别
- Excel 读写

---

### 6. 计费模块 — 额度管理 ⚠️

**定位：** 数字员工使用额度消耗和校验

**核心概念：**
- 扣费时机由开发者决定（例如创建订单、生成报告、完成审核时）
- 扣费额度由平台售价决定（平台管理员配置每次消耗的单位数）
- 支持 API-KEY 鉴权（服务端集成使用 API-KEY）

**典型场景：**
- 销售助理：生成销售订单时扣费
- 合同审核：生成审核报告时扣费
- HR 助理：生成面试评估报告时扣费

**集成方式：** 在 MCP 工具、iframe 技能卡片或后端 API 中集成  
**详细文档：** `references/billing.md`

> ⚠️ **重要提醒：** 如果数字员工提供生成文档/报告/合同、创建订单/工单、数据导出（PDF/Excel/Word）、复杂计算或分析、批量处理、调用外部付费 API 等高价值服务，**强烈建议集成计费**，否则可能导致成本失控。

---

## 能力层次

```
┌──────────────────────────────────────────────┐
│                  应用层                       │
│  ├─ AI 服务（API 调用）                       │
│  ├─ 数字员工（对话 + 菜单）                   │
│  └─ 附件分类与提取（文档智能化）              │
├──────────────────────────────────────────────┤
│                  扩展层                       │
│  ├─ Iframe 技能卡片（UI 扩展）                │
│  ├─ MCP（数据操作）                           │
│  └─ 文档服务（格式转换）                      │
├──────────────────────────────────────────────┤
│                  基础层                       │
│  ├─ 鉴权（API-KEY）                           │
│  └─ 计费模块（额度管理）                      │
└──────────────────────────────────────────────┘
```

---

## 快速开始

### 典型场景识别

#### 场景 1：需要创建配置资源

当用户说"创建 AI 服务"、"配置数字员工"、"注册技能卡片"、"创建附件分类"时，使用对应的 Python 脚本：

| 操作 | 脚本 |
| --- | --- |
| 创建 AI 服务 | `scripts/create_ai_service.py` |
| 创建数字员工 | `scripts/create_digital_employee.py` |
| 更新数字员工 | `scripts/update_digital_employee.py` |
| 配置数字员工应用菜单 | `scripts/configure_app_menu.py` |
| 注册 iframe 卡片 | `scripts/register_iframe_card.py` |
| 创建附件分类 ⭐ | `scripts/create_attachment_classification.py` |

**特别注意 — 附件分类创建：** 创建时要重点设计 `extractRules`：
- 明确需要提取哪些字段（name、label、type）
- 字段描述要详细（帮助 AI 准确定位）
- 考虑字段的格式要求（日期格式、数字精度等）

#### 场景 2：需要调用已有服务

当用户说"如何提取合同数据"、"调用 AI 服务"、"使用附件识别"时，提供调用示例：
- AI 服务调用 → 生成完整的 API 调用代码
- 附件提取调用 → 生成文件上传 + 提取的完整流程 ⭐
- 数字员工聊天 → 生成会话创建和消息发送示例

**附件提取标准流程：**
1. 查询系统是否已有目标分类（如"采购合同"）
2. 如不存在：创建分类并定义提取规则
3. 在业务系统中调用提取接口
4. 将提取的结构化数据填充到表单

#### 场景 3：需要集成代码或方案

| 需求 | 参考文档 |
| --- | --- |
| iframe 嵌入对接 | `references/iframe-embed.md` |
| API 调用示例 | 对应接口文档 |
| 鉴权配置问题 | `references/auth-and-config.md` |

#### 场景 4：需要故障排查

系统性诊断步骤：
1. 检查鉴权配置（API-KEY 格式、请求头设置）
2. 验证接口路径和参数格式
3. 确认必需资源是否已创建（serviceCode、robotId、分类编码等）
4. 对于附件提取问题，检查：
   - 文件格式是否支持
   - 提取规则 description 是否清晰
   - 文件内容是否包含目标字段
5. 提供调试命令或测试脚本

---

## 文档按需加载原则

不要一次性加载所有 reference 文档。根据任务类型按优先级读取：

**第一步：总是先读鉴权配置**
- `references/auth-and-config.md` — 所有任务都需要了解鉴权和配置机制

**第二步：根据任务读取对应文档**

| 用户任务 | 需要读取的文档 |
| --- | --- |
| 创建/调用 AI 服务 | `references/ai-service.md` |
| 创建/使用数字员工 | `references/digital-employee.md` |
| 附件分类场景 | `references/attachment-classification.md` |
| iframe 将数字员工嵌入到当前系统对接 | `references/iframe-embed.md` |
| iframe 技能卡片注册 | `references/iframe-skill-card.md` |
| 数字员工旁边的业务菜单 iframe、菜单 SSO、菜单 runtimeToken 解析 | `references/app-menu-iframe.md` |
| 文档服务对接 | `references/document-service.md` |
| 数字员工计费集成 | `references/billing.md` |

---

## 创建配置资源的标准流程

### 1. 理解业务需求

通过对话明确：
- 这个服务/员工/附件分类要解决什么问题？
- 输入是什么？（用户会提供哪些信息）
- 输出期望是什么？（返回什么格式的结果）
- 有没有特殊的业务规则或限制？

### 2. 设计配置参数

对于 AI 服务，设计有意义的 `inputs` 字段，而不是只用通用的 `user_message`。

**不推荐的做法：**

```json
{"inputs": [{"name": "user_message", "label": "请输入", "type": "textarea"}]}
```

**推荐的做法（以合同审查服务为例）：**

```json
{
  "inputs": [
    {"name": "contract_type", "label": "合同类型", "type": "select", "options": ["采购合同", "销售合同"]},
    {"name": "contract_content", "label": "合同内容", "type": "textarea"},
    {"name": "review_focus", "label": "审查重点", "type": "text"}
  ]
}
```

**其他业务场景示例：**
- 简历筛选服务：`job_description`（岗位要求）、`resume_content`（简历内容）、`screening_criteria`（筛选标准）
- 文案生成服务：`product_name`（产品名）、`target_audience`（目标人群）、`tone`（文案风格）、`key_points`（卖点）
- 数据分析服务：`data_source`（数据来源）、`analysis_dimension`（分析维度）、`output_format`（输出格式）

### 2.5 选择合适的模型

创建 AI 服务、数字员工或附件分类时，需要指定大语言模型，不同场景应选择不同的模型。

| 场景 | 推荐优先级 | 原因 |
| --- | --- | --- |
| 附件分类和文档提取 | `qwen` > `deepseek` > `gpt-4` > `gpt-3.5` | qwen/deepseek 在中文文档解析方面表现更优 |
| AI 服务（通用任务） | `gpt-4` > `gpt-3.5` > `qwen` > `deepseek` | GPT 系列在复杂逻辑推理、内容生成方面能力更强 |
| 数字员工（对话交互） | `gpt-4` > `gpt-3.5` > `qwen` > `deepseek` | GPT 系列在多轮对话、上下文理解方面更突出 |

**如何查询可用模型：**

```bash
curl -X GET "${WORKOPILOT_BASE_URL}/api/aiagent/models" \
  -H "API-KEY: ${WORKOPILOT_API_KEY}"
```

**重要提醒：**
- 创建前必须先查询模型，确保租户下已配置
- 根据场景选择模型，不要所有场景都用同一个
- 创建后用真实数据测试，效果不理想可尝试其他模型
- GPT-4 能力强但成本较高，简单任务可用 GPT-3.5 或国产模型

### 3. 创建配置文件

根据设计生成 JSON 配置文件，配置字段直接对应后端接口的字段名。

### 4. 调用脚本创建

运行对应的 Python 脚本。脚本会：
- 自动从环境变量或 `.env` 文件读取鉴权配置
- 自动查询可用模型并根据场景智能选择
- 检查资源是否已存在（根据 code 查询）
- 如果存在则复用，不存在则创建
- 返回关键标识（serviceCode、robotId 等）

### 5. 验证和测试

- 记录返回的关键 ID/Code
- 使用 `scripts/smoke_test.py` 或 curl 命令测试
- 确认功能符合预期
- **特别注意**：如果是附件提取，用真实文档测试提取效果

### 6. 提供使用示例

输出后续使用的代码示例，包括：
- 完整的 API 调用代码（带错误处理）
- 参数说明和来源
- 安全提醒（APIKEY 不要暴露在前端）

---

## AI 服务创建的关键注意事项

### systemPrompt 必须引用所有 inputs

在 systemPrompt 中使用 `{{input_name}}` 引用输入字段。创建前检查：
- 每个 input 是否都在 systemPrompt 中被引用？
- 引用的占位符名称是否与 `input.name` 完全一致？
- 是否有拼写错误或遗漏？

**正确的对应关系示例：**

```json
{
  "inputs": [
    {"name": "job_description", "label": "岗位描述", "type": "textarea"},
    {"name": "resume_content", "label": "简历内容", "type": "textarea"}
  ],
  "systemPrompt": "请根据以下岗位要求：{{job_description}}\n\n分析以下简历：{{resume_content}}\n\n给出筛选建议。"
}
```

如果 systemPrompt 中没有引用某个 input，用户填写的数据就不会被 AI 使用，导致功能失效。

### 避免创建"空壳服务"

每个服务都应该：
- 有明确的业务场景和用途
- inputs 设计体现业务需求
- systemPrompt 包含领域知识和工作流程
- 能给用户带来实际价值

---

## 集成代码的输出要求

### 1. 完整可运行的代码

不要只给代码片段，要给完整示例。用户应该能直接复制使用（修改参数后）。

**AI 服务调用完整示例：**

```javascript
async function callAIService(serviceCode, inputs) {
  const WORKOPILOT_API_KEY = process.env.WORKOPILOT_API_KEY; // 从环境变量读取
  const BASE_URL = process.env.WORKOPILOT_BASE_URL;

  try {
    const response = await fetch(`${BASE_URL}/api/aiagent/run`, {
      method: 'POST',
      headers: {
        'API-KEY': WORKOPILOT_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ serviceCode, inputs })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.code !== 200) {
      throw new Error(`业务错误 ${data.code}: ${data.msg}`);
    }

    return data.data;
  } catch (error) {
    console.error('调用 AI 服务失败:', error.message);
    throw error;
  }
}
```

### 2. 清晰的参数说明

注释说明每个参数的含义、来源、是否必需、格式要求。

### 3. 错误处理

包含 try-catch 和有意义的错误提示：
- HTTP 错误 — 检查网络、URL、鉴权
- 业务错误 — 检查参数、配置、权限
- 超时错误 — 考虑流式返回或增加超时时间

### 4. 安全提醒

- APIKEY 应该放在服务端环境变量，**不要暴露在前端代码**
- **不要**将 APIKEY 提交到 Git 仓库
- 生产环境使用密钥管理服务

### 5. 验证方法

- 提供测试命令或脚本
- 说明预期的返回结果
- 列出常见问题和解决方法

---

## 配置加载机制

所有脚本都支持多种配置方式，优先级从高到低：

### 1. 命令行参数（最高优先级）

```bash
python scripts/create_ai_service.py \
  --base-url https://agent.workopilot.com/net-api \
  --api-key your_api_key \
  --config service.json
```

适用场景：临时测试、CI/CD 环境、覆盖默认配置

### 2. 环境变量

```bash
export WORKOPILOT_BASE_URL="https://agent.workopilot.com/net-api"
export WORKOPILOT_API_KEY="your_api_key"
```

适用场景：服务器部署、容器环境、多项目共享配置

### 3. 本地环境文件（推荐方式）

在项目根目录创建 `.env.workopilot`：

```env
# 生产环境（默认）
WORKOPILOT_BASE_URL=https://agent.workopilot.com/net-api
WORKOPILOT_API_KEY=your_api_key_here

# 测试环境（取消注释使用）
# WORKOPILOT_BASE_URL=https://agenttest.workopilot.com/net-api
# WORKOPILOT_API_KEY=your_test_api_key_here
```

然后直接运行脚本，无需指定参数：

```bash
python scripts/create_ai_service.py --config service.json
```

脚本会自动发现并加载 `.env.workopilot` 或 `.env.local`。

### 4. 默认值（仅 baseUrl）

- 生产环境（默认）：`https://agent.workopilot.com/net-api`
- 测试环境：`https://agenttest.workopilot.com/net-api`

> **注意：** APIKEY 没有默认值，必须配置。生产和测试环境的 APIKEY 不同，需要分别申请。

---

## 安全最佳实践

### 配置文件安全

**应该做的：**
- 使用 `.env.workopilot` 存储本地开发配置
- 检测当前项目是否存在配置文件（`.env`、`appsetting.json`、`config` 等），按照项目规范配置 API Key
- 确保 `.gitignore` 包含 `.env.workopilot` 和 `.env.local`
- 生产环境使用环境变量或密钥管理服务（如 AWS Secrets Manager）
- 可以提交 `.env.workopilot.example` 作为模板，但只包含占位值

**不应该做的：**
- 不要将 APIKEY 硬编码在代码中
- 不要将 APIKEY 提交到 Git 仓库
- 不要将 APIKEY 暴露在前端代码或浏览器中
- 不要在示例文件中使用真实 APIKEY

**.env.workopilot.example 示例：**

```env
# 复制此文件为 .env.workopilot 并填入真实值
# 生产环境（默认）
WORKOPILOT_BASE_URL=https://agent.workopilot.com/net-api
WORKOPILOT_API_KEY=<your-production-api-key>

# 测试环境
# WORKOPILOT_BASE_URL=https://agenttest.workopilot.com/net-api
# WORKOPILOT_API_KEY=<your-test-api-key>
```

### iframe 技能卡片安全

iframe 技能卡片在测试时可以使用本地 URL，但发布到生产前必须：
1. 将 iframe URL 更新为正式域名（HTTPS）
2. 在正式域名部署并测试
3. 重新注册技能卡片或更新配置

> 本地测试 URL 只能在开发者本机访问，其他用户无法加载，会导致卡片空白。

---

## 脚本使用指南

### 推荐的使用方式

在开发者项目根目录运行脚本，脚本会自动发现 `.env.workopilot`：

```bash
# 在项目根目录
python path/to/scripts/smoke_test.py
python path/to/scripts/create_ai_service.py --config ai_service.json
python path/to/scripts/create_attachment_classification.py --config classification.json
```

### 通用参数

所有脚本都支持：

```
--base-url <API_BASE_URL>  # API 基础 URL
--api-key <API_KEY>        # API 密钥
--env-file <FILE>          # 指定环境配置文件路径
```

### 幂等性说明

脚本实现轻量级幂等，避免重复创建：

| 脚本 | 幂等逻辑 |
| --- | --- |
| `create_ai_service.py` | 按 `serviceCode` 查询，存在则复用 |
| `create_digital_employee.py` | 按 `robotCode` 查询，存在则复用 |
| `configure_app_menu.py` | create 遇到相同 `menuKey` 会提示改用 update；update 按 `employeeId + menuKey` 定位 |
| `create_attachment_classification.py` | 按 `GroupCode + CategoryCode` 查询，存在时默认编辑覆盖（可用 `--no-edit-existing` 只复用不覆盖） |
| `register_iframe_card.py` | 直接创建（当前开放接口只提供注册，不提供查询） |

幂等性让脚本可以安全重复运行，适合自动化场景。

---

## 本技能核心流程与要求

1. **每次工作必须先检查是否有喔壳的 APIKEY**，如果不存在要先引导用户配置后再进行下一步，不要着急动手
2. **每次工作必须检查相关服务配置是否存在**，比如在当前项目内接入喔壳的 AI 服务、附件取数、数字员工，必须先通过脚本查询喔壳是否已配置，没有配置协助用户配置
3. **计费检查**：如果用户开发的数字员工包含高价值操作（生成文档、创建订单、数据导出、复杂分析、批量处理等），必须提醒用户集成计费模块，否则可能导致成本失控
4. 必须严格遵守以上原则，通过喔壳脚本协助用户配置喔壳，通过接口文档将喔壳服务对接到当前系统，集成喔壳的任何服务或要开发喔壳的卡片、嵌入员工时要遵照喔壳的开发规范来开发相关的业务

---

## 输出检查清单

帮助开发者完成任务后，确保输出包含：

- **鉴权配置说明** — 如何设置 `WORKOPILOT_API_KEY`，请求头格式（`API-KEY`）
- **接口路径** — 精确的 API 端点（注意 Document 服务的特殊路由）
- **关键标识** — 记录已创建资源的 `serviceCode`、`robotId`、`robotCode`、`skillRegistryId`
- **使用示例** — 完整的代码示例，包含参数说明和错误处理
- **验证方法** — 提供 smoke test 命令或 curl 示例
- **后续步骤** — 告诉用户接下来可以做什么
- **常见问题** — 预警可能遇到的问题和解决方法
- **安全提醒** — APIKEY 保管和使用的注意事项
