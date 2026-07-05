import { useEffect } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { useScenarioStore } from '@/stores/scenarioStore'

export function ScenarioSelector() {
  const { scenarios, selectedId, loading, loadScenarios, selectScenario } = useScenarioStore()

  useEffect(() => { loadScenarios() }, [loadScenarios])

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border/30 shrink-0">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          选择方案框架
        </h2>
        <p className="text-[10px] text-muted-foreground/60 mt-1">
          选择场景后 AI 将按对应叙事逻辑生成 PPT
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            <button
              onClick={() => selectScenario(null)}
              className={`w-full text-left p-3 rounded-xl border transition-all ${
                !selectedId
                  ? 'border-primary/40 bg-primary/5 shadow-sm'
                  : 'border-border/20 hover:bg-accent/10'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">✨ 自由生成</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">不限结构，AI 根据你的需求灵活组织</p>
                </div>
                {!selectedId && <Check className="w-4 h-4 text-primary" />}
              </div>
            </button>

            {scenarios.map((s) => (
              <button
                key={s.id}
                onClick={() => selectScenario(s.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedId === s.id
                    ? 'border-primary/40 bg-primary/5 shadow-sm'
                    : 'border-border/20 hover:bg-accent/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{s.icon}</span>
                    <div>
                      <p className="text-sm font-medium">{s.name}</p>
                      <p className="text-[10px] text-muted-foreground">{s.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded-full">
                      {s.slide_count} 页框架
                    </span>
                    {selectedId === s.id && <Check className="w-4 h-4 text-primary" />}
                  </div>
                </div>
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
