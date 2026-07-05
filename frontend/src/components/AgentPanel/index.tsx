import { useProjectStore } from '@/stores/projectStore'
import type { AgentName } from '@/types/events'

interface AgentMeta {
  label: string
  role: string
  model: string
  icon: string
}

const AGENT_META: Record<AgentName, AgentMeta> = {
  planner: { label: '规划师', role: '三阶段交互式规划 / 诊断', model: 'GLM-5.1 (OpenRouter)', icon: '🧠' },
  copywriter: { label: '文案师', role: '逐页文案 / 演讲备注', model: 'DeepSeek V3.2', icon: '✍️' },
  designer: { label: '设计师', role: 'SVG 排版生成', model: 'GLM-5.1', icon: '🎨' },
  effects: { label: '效果师', role: '图表 / AI 图片', model: 'Qwen3.5-9B', icon: '📊' },
  editor: { label: '编辑师', role: 'SVG→PPTX / 字体嵌入', model: 'ppt-master 脚本', icon: '📦' },
}

const STATUS_STYLES = {
  idle: 'border-border/30 bg-card/30',
  running: 'border-primary/50 bg-primary/10 shadow-[0_0_12px_var(--glow-color)]',
  complete: 'border-green-500/40 bg-green-500/10',
  error: 'border-red-500/40 bg-red-500/10',
}

const STATUS_DOT = {
  idle: 'bg-muted-foreground/40',
  running: 'bg-primary animate-pulse shadow-[0_0_6px_var(--glow-color)]',
  complete: 'bg-green-500',
  error: 'bg-red-500',
}

export function AgentPanel({ compact = false }: { compact?: boolean }) {
  const agents = useProjectStore((s) => s.agents)
  const names = Object.keys(agents) as AgentName[]

  if (compact) {
    return (
      <div className="flex flex-col gap-2 p-2 overflow-y-auto">
        {names.map((name) => {
          const agent = agents[name]
          const meta = AGENT_META[name]
          return (
            <div
              key={name}
              title={`${meta.label} · ${agent.status}${agent.message ? ' · ' + agent.message : ''}`}
              className={`relative w-10 h-10 rounded-xl border flex items-center justify-center text-lg transition-all ${STATUS_STYLES[agent.status]}`}
            >
              <span>{meta.icon}</span>
              <span className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-background ${STATUS_DOT[agent.status]}`} />
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-3 overflow-y-auto">
      <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1 font-display">智能体</h2>
      {names.map((name) => {
        const agent = agents[name]
        const meta = AGENT_META[name]
        return (
          <div
            key={name}
            className={`rounded-xl border px-3 py-2.5 transition-all ${STATUS_STYLES[agent.status]}`}
          >
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[agent.status]}`} />
              <span className="text-sm font-medium">{meta.label}</span>
              {agent.status === 'running' && agent.progress > 0 && (
                <span className="text-xs text-muted-foreground ml-auto">{Math.round(agent.progress * 100)}%</span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 leading-tight">{meta.role}</p>
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">{meta.model}</p>
            {agent.message && (
              <p className="text-xs mt-1.5 text-foreground/80 truncate">{agent.message}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
