import { useState } from 'react';
import { Settings, Server, Cpu, HardDrive, Wrench, BookOpen, Plug, ExternalLink, Copy, Check } from 'lucide-react';
import { LLMConfig } from './LLMConfig';

const CONFIG_ITEMS = [
  { icon: Server, label: 'API 服务', value: 'http://localhost:8080', desc: '智能报告引擎后端 · 端口通过 SERVER_PORT 环境变量配置' },
  { icon: Cpu, label: 'LLM 模型', value: 'OpenRouter (Claude Sonnet 4.6)', desc: '意图识别 / 内容生成 / 校验 · 可在 LLM 配置页切换' },
  { icon: HardDrive, label: '存储', value: '本地文件系统', desc: '数据文件 & 导出结果 · 路径通过 LOCAL_STORAGE_PATH 配置' },
  { icon: Settings, label: '数据源类型', value: '7 种', desc: '文件上传 · 聊天记录 · 企业PPT · REST API · MCP · 数据库 · RAG' },
  { icon: Settings, label: '报告模板', value: '24 个', desc: '5 元模板 + 19 精选模板, 覆盖 5 大业务类别 · 支持自定义' },
  { icon: Settings, label: '输出格式', value: '4 种', desc: 'PPTX (原生可编辑) · DOCX · PDF · HTML 交互脑图' },
];

const MCP_TOOLS = [
  { name: 'report_template_list', desc: '列出所有可用报告模板' },
  { name: 'report_template_detail', desc: '获取模板详情（含章节和 Prompt）' },
  { name: 'report_intent_recognize', desc: '分析用户意图并推荐模板' },
  { name: 'report_generate', desc: '基于模板和数据源生成结构化报告' },
  { name: 'report_export', desc: '导出报告为 DOCX/PDF/PPTX/脑图' },
  { name: 'datasource_types', desc: '列出7种支持的数据源类型' },
  { name: 'rag_search', desc: '在知识库中语义搜索' },
];

const CLAUDE_CODE_CONFIG = `{
  "mcpServers": {
    "smart-reporting": {
      "command": ".venv/bin/python",
      "args": ["backend/mcp_server.py"],
      "cwd": "/path/to/smart_reporting"
    }
  }
}`;

export function SettingsPanel() {
  const [tab, setTab] = useState<'system' | 'llm' | 'mcp'>('system');
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(CLAUDE_CODE_CONFIG);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">系统设置</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-muted p-1 rounded-lg">
        <button onClick={() => setTab('system')}
          className={`flex-1 py-2 text-sm rounded-md transition-colors ${tab === 'system' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
          <Server className="w-3.5 h-3.5 inline mr-1" />系统信息
        </button>
        <button onClick={() => setTab('llm')}
          className={`flex-1 py-2 text-sm rounded-md transition-colors ${tab === 'llm' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
          <Wrench className="w-3.5 h-3.5 inline mr-1" />LLM 配置
        </button>
        <button onClick={() => setTab('mcp')}
          className={`flex-1 py-2 text-sm rounded-md transition-colors ${tab === 'mcp' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
          <Plug className="w-3.5 h-3.5 inline mr-1" />MCP 服务
        </button>
      </div>

      {tab === 'system' && (
        <div className="space-y-4">
          {/* API Documentation — top priority */}
          <div className="p-4 rounded-xl border-2 border-primary/20 bg-primary/5">
            <div className="flex items-start gap-4">
              <BookOpen className="w-6 h-6 text-primary mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold">API 文档</p>
                <p className="text-xs text-muted-foreground mt-0.5 mb-3">完整的接口文档，含请求示例和响应格式（7大模块、30+端点）</p>
                <div className="flex gap-4">
                  <a href="/docs" target="_blank" className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors">
                    <ExternalLink className="w-3.5 h-3.5" />Swagger UI
                  </a>
                  <a href="/redoc" target="_blank" className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-primary/30 text-primary text-xs font-medium hover:bg-primary/5 transition-colors">
                    <ExternalLink className="w-3.5 h-3.5" />ReDoc
                  </a>
                  <a href="https://github.com/wenwenba2020/smart-reporting/blob/master/backend/api/docs.md" target="_blank" className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border/30 text-xs text-muted-foreground hover:text-foreground transition-colors">
                    <ExternalLink className="w-3.5 h-3.5" />Markdown 文档
                  </a>
                </div>
              </div>
            </div>
          </div>

          {CONFIG_ITEMS.map((item, i) => (
            <div key={i} className="flex items-start gap-4 p-4 rounded-xl border border-border/30 bg-card">
              <item.icon className="w-5 h-5 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-sm text-muted-foreground">{item.value}</p>
                <p className="text-xs text-muted-foreground/60 mt-0.5">{item.desc}</p>
              </div>
            </div>
          ))}

        </div>
      )}

      {tab === 'llm' && <LLMConfig />}

      {tab === 'mcp' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl border border-green-200 bg-green-50">
            <p className="text-sm font-medium text-green-800">MCP 服务已就绪</p>
            <p className="text-xs text-green-600 mt-1">
              智能报告引擎已封装为 MCP Server，外部 AI Agent（Claude Code/Cursor 等）可直接调用报告生成能力。
            </p>
          </div>

          {/* Available Tools */}
          <div>
            <h3 className="text-sm font-semibold mb-3">可用工具 ({MCP_TOOLS.length})</h3>
            <div className="space-y-2">
              {MCP_TOOLS.map(t => (
                <div key={t.name} className="flex items-start gap-3 p-3 rounded-lg border border-border/30 bg-card">
                  <Plug className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                  <div>
                    <code className="text-xs font-mono text-primary">{t.name}</code>
                    <p className="text-xs text-muted-foreground mt-0.5">{t.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Claude Code Config */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Claude Code 配置</h3>
            <p className="text-xs text-muted-foreground mb-2">
              在项目根目录的 <code className="bg-muted px-1 rounded">.mcp.json</code> 中添加以下配置即可使用：
            </p>
            <div className="relative">
              <pre className="bg-gray-900 text-green-400 text-xs p-4 rounded-lg overflow-x-auto">{CLAUDE_CODE_CONFIG}</pre>
              <button onClick={handleCopy}
                className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded bg-gray-700 text-gray-300 text-xs hover:bg-gray-600 transition-colors">
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? '已复制' : '复制'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
