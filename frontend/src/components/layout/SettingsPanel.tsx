import { useState } from 'react';
import { Settings, Server, Cpu, HardDrive, Wrench } from 'lucide-react';
import { LLMConfig } from './LLMConfig';

const CONFIG_ITEMS = [
  { icon: Server, label: 'API 服务', value: 'http://localhost:8080', desc: '智能报告引擎后端' },
  { icon: Cpu, label: 'LLM 模型', value: 'OpenRouter (Claude Sonnet 4.6)', desc: '意图识别 / 内容生成 / 校验' },
  { icon: HardDrive, label: '存储', value: '本地文件系统', desc: '数据文件 & 导出结果' },
  { icon: Settings, label: '数据源类型', value: '7 种', desc: '文件上传 · 聊天记录 · 企业PPT · REST API · MCP · 数据库 · RAG' },
  { icon: Settings, label: '报告模板', value: '24 个', desc: '5 元模板 + 19 精选模板, 覆盖 5 大业务类别' },
  { icon: Settings, label: '输出格式', value: '4 种', desc: 'PPTX (原生可编辑) · DOCX · PDF · HTML 交互脑图' },
];

export function SettingsPanel() {
  const [tab, setTab] = useState<'system' | 'llm'>('system');

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">系统设置</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-muted p-1 rounded-lg">
        <button
          onClick={() => setTab('system')}
          className={`flex-1 py-2 text-sm rounded-md transition-colors ${
            tab === 'system' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Server className="w-3.5 h-3.5 inline mr-1" />系统信息
        </button>
        <button
          onClick={() => setTab('llm')}
          className={`flex-1 py-2 text-sm rounded-md transition-colors ${
            tab === 'llm' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Wrench className="w-3.5 h-3.5 inline mr-1" />LLM 配置
        </button>
      </div>

      {tab === 'system' ? (
        <div className="space-y-4">
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
      ) : (
        <LLMConfig />
      )}
    </div>
  );
}
