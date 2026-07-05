# ppt_agent 项目管理文件清单

> 最后更新：2026-04-29
> 维护人：PM Agent

---

## 📋 文件清单

### 核心配置文件

| 文件 | 用途 | 读写角色 |
|------|------|----------|
| `CLAUDE.md` | Claude Code 工作指引：技术栈、启动、规则 | 所有 Agent |
| `AGENTS.md` | PM Agent 自身指令 | PM Agent |
| `.env` | API Key、JWT Secret 等敏感配置 | 开发者 |
| `.jarvis-status.md` | 运行时心跳状态记录 | PM / Jarvis Agent |

### 开发计划 & 规格文档

| 文件 | 用途 |
|------|------|
| `PPT_ASSISTANT_DEVELOPMENT_PLAN.md` | 总体开发计划（参考用，架构级） |
| `docs/todo.md` | 待办任务清单（按 Phase 组织） |
| `docs/dev-log.md` | 综合进度 + 技术栈 + 已实现功能 + 坑点记录 |
| `docs/known-pitfalls.md` | 关键坑点汇总（每次开工前必读） |

### 专项技术文档

| 文件 | 用途 | 对应开发任务 |
|------|------|-------------|
| `docs/agents-spec.md` | 五智能体规格说明 | 写智能体代码前必读 |
| `docs/data-formats.md` | OUTLINE.md 等数据模型 | 写数据模型前必读 |
| `docs/font-management.md` | 字体管理策略 | 写字体相关代码前必读 |
| `docs/ppt-pipeline.md` | PPT 生成流水线 | 写 PPT 转换代码前必读 |

### 项目进度管理（本目录）

| 文件 | 用途 | 更新频率 |
|------|------|----------|
| `docs/pm/README.md` | **本文件**：文件清单 | 随文件结构变化 |
| `docs/pm/progress-report-template.md` | 进度报告模板 | 每次出报告时引用 |
| `docs/pm/status-summary-template.md` | 状态摘要模板（简洁版） | 日常更新 |

### 运行记录

| 文件 | 用途 |
|------|------|
| `docs/superpowers/plans/` | 超能力开发计划 |
| `docs/superpowers/specs/` | 超能力规格设计 |

### 生成目录（不纳入文件清单）

以下目录为运行时生成，不进行版本管理：

- `projects/` — 用户项目工作区
- `fonts/` — TTF 字体库
- `.venv/` — Python 虚拟环境
- `frontend/node_modules/`

---

## 职责说明

| 角色 | 职责 | 维护的文件 |
|------|------|-----------|
| **PM Agent** | 进度追踪、风险预警、计划编排 | `docs/pm/` 全部 |
| **开发者** | 环境配置、代码实现 | `CLAUDE.md`、`.env` |
| **Jarvis Agent** | 运行时调度、心跳 | `.jarvis-status.md` |

---

## 更新本清单的时机

- 新增项目管理类文件时，立即添加
- 专项文档新增/迁移时，同步更新
- 角色职责变化时，更新职责说明
