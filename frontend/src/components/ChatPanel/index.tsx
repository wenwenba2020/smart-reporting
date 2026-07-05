import { useState, useRef, useEffect } from 'react'
import { Upload, ArrowRight, RotateCcw, MessageSquare } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import {
  planInteract, planRefine, confirmAndGenerate,
} from '@/api/client'
import { UploadSourceModal } from '@/components/UploadSourceModal'
import { searchLibrarySlides } from '@/api/client'
import type { LibrarySlide } from '@/types/events'
import type { AgentName } from '@/types/events'
import { normalizePoint } from '@/utils/normalizePoint'

const AGENT_LABELS: Record<AgentName, string> = {
  planner: '规划师', copywriter: '文案师', designer: '设计师', effects: '效果师', editor: '编辑师',
}
const AGENT_ICONS: Record<AgentName, string> = {
  planner: '🧠', copywriter: '✍️', designer: '🎨', effects: '📊', editor: '📦',
}
const STAGE_LABELS = ['', '📍 阶段一：明确定位', '📋 阶段二：大纲骨架', '🔍 阶段三：内容详情']

interface SlideData {
  slide_id: string; title: string; layout: string;
  subtitle?: string; points?: string[];
  [key: string]: unknown;
}

// ---------- Agent Activity ----------
const AGENT_WORK_HINTS: Record<AgentName, string[]> = {
  planner: ['分析用户需求...', '调研参考资料...', '生成 PPT 大纲...', '规划页面结构...'],
  copywriter: ['提炼核心内容...', '撰写页面文案...', '生成演讲备注...', '优化措辞表达...'],
  designer: ['设计页面布局...', '生成 SVG 排版...', '调整视觉元素...', '统一页面风格...'],
  effects: ['处理图表数据...', '生成数据图表...', '优化图片资源...'],
  editor: ['SVG 后处理...', '转换为 PPTX...', '嵌入字体文件...', '生成最终文件...'],
}

function AnimatedDots() {
  return <span className="inline-flex gap-0.5 ml-1">{[0, 1, 2].map(i => (
    <span key={i} className="w-1 h-1 bg-primary rounded-full animate-bounce shadow-[0_0_4px_var(--glow-color)]" style={{ animationDelay: `${i * 0.15}s` }} />
  ))}</span>
}

function AgentActivityFeed() {
  const agents = useProjectStore((s) => s.agents)
  const [tick, setTick] = useState(0)
  const active = (Object.keys(agents) as AgentName[]).filter((n) => agents[n].status !== 'idle')

  useEffect(() => {
    if (!active.some(n => agents[n].status === 'running')) return
    const t = setInterval(() => setTick(v => v + 1), 2000)
    return () => clearInterval(t)
  }, [active, agents])

  if (!active.length) return null

  return (
    <div className="rounded-xl bg-gradient-to-b from-primary/5 via-muted/20 to-muted/5 border border-border/50 p-3 space-y-2.5 backdrop-blur-sm">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest font-display">智能体工作流</p>
      {active.map((name, idx) => {
        const a = agents[name]
        const isLast = idx === active.length - 1
        const hints = AGENT_WORK_HINTS[name]
        const rotatingHint = a.status === 'running' && !a.message ? hints[tick % hints.length] : null
        return (
          <div key={name} className="flex items-start gap-2.5">
            {/* Timeline dot + connector */}
            <div className="flex flex-col items-center pt-0.5">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm transition-all ${
                a.status === 'running' ? 'bg-primary/20 animate-pulse shadow-[0_0_8px_var(--glow-color)]' :
                a.status === 'complete' ? 'bg-green-500/20' :
                a.status === 'error' ? 'bg-red-500/20' : 'bg-muted'
              }`}>{AGENT_ICONS[name]}</div>
              {!isLast && <div className={`w-px h-6 mt-1 transition-colors ${
                a.status === 'complete' ? 'bg-green-500/40' : 'bg-border/50'
              }`} />}
            </div>
            <div className="flex-1 min-w-0 pb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{AGENT_LABELS[name]}</span>
                {a.status === 'running' && (
                  <span className="text-xs bg-primary/15 text-primary rounded-full px-2 py-0.5 flex items-center shadow-[0_0_6px_var(--glow-color)]">
                    工作中<AnimatedDots />
                  </span>
                )}
                {a.status === 'complete' && <span className="text-xs bg-green-500/15 text-green-600 dark:text-green-400 rounded-full px-2 py-0.5">✓ 完成</span>}
                {a.status === 'error' && <span className="text-xs bg-red-500/15 text-red-600 dark:text-red-400 rounded-full px-2 py-0.5">✗ 出错</span>}
                {a.status === 'running' && a.progress > 0 && (
                  <span className="text-xs text-muted-foreground ml-auto">{Math.round(a.progress * 100)}%</span>
                )}
              </div>
              {/* Real message or rotating hint */}
              {a.message ? (
                <p className="text-xs text-foreground/70 mt-0.5">{a.message}</p>
              ) : rotatingHint ? (
                <p className="text-xs text-muted-foreground/50 mt-0.5 italic transition-opacity duration-500">{rotatingHint}</p>
              ) : null}
              {a.status === 'running' && a.progress > 0 && (
                <div className="w-full bg-muted rounded-full h-1.5 mt-1.5 overflow-hidden">
                  <div className="bg-gradient-to-r from-primary/70 to-primary h-1.5 rounded-full transition-all duration-700 shadow-[0_0_6px_var(--glow-color)]">
                    <div className="h-full bg-white/20 animate-pulse" style={{ width: `${Math.round(a.progress * 100)}%` }} />
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------- Option Buttons ----------
function OptionButtons({ options, onSelect, recommendation }: {
  options: string[]; onSelect: (v: string) => void; recommendation?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {options.map((opt, i) => (
          <button key={i} onClick={() => onSelect(opt)}
            className={`rounded-lg border px-3 py-2 text-sm text-left transition-all ${
              i === 0
                ? 'border-primary/50 bg-primary/5 hover:bg-primary/10 hover:shadow-[0_0_10px_var(--glow-color)]'
                : 'border-border/50 hover:bg-accent hover:border-border'
            }`}>
            {opt}
            {i === 0 && <span className="text-xs text-primary ml-1 font-medium">推荐</span>}
          </button>
        ))}
      </div>
      {recommendation && <p className="text-xs text-muted-foreground">💡 {recommendation}</p>}
    </div>
  )
}

// ---------- Outline View ----------
function OutlineView({ slides }: { slides: SlideData[] }) {
  return (
    <div className="space-y-1 max-h-60 overflow-y-auto rounded-xl border border-border/50 p-3 bg-gradient-to-b from-card to-muted/5 backdrop-blur-sm">
      {slides.map((s) => (
        <div key={s.slide_id} className="flex items-start gap-2 text-sm border-b border-border/30 pb-1 last:border-0">
          <span className="font-mono text-xs text-primary/70 w-6 shrink-0 font-semibold">#{s.slide_id}</span>
          <div className="flex-1 min-w-0">
            <span className="font-medium">{s.title}</span>
            <span className="text-xs text-muted-foreground ml-2">({s.layout})</span>
            {s.subtitle && <p className="text-xs text-muted-foreground">{s.subtitle}</p>}
            {(s.points || []).length > 0 && (
              <ul className="text-xs text-muted-foreground mt-0.5">
                {s.points!.slice(0, 3).map((p, i) => <li key={i}>• {p}</li>)}
                {s.points!.length > 3 && <li>...等 {s.points!.length - 3} 条</li>}
              </ul>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------- Main ChatPanel ----------
export function ChatPanel() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState(0)
  const [step, setStep] = useState(0)  // Stage 1 question step
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentQuestion, setCurrentQuestion] = useState<{question: string; options: string[]; recommendation?: string; key: string} | null>(null)
  const [slides, setSlides] = useState<SlideData[]>([])
  const [urlContext, setUrlContext] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [showSlideSearch, setShowSlideSearch] = useState(false)
  const [slideSearchQuery, setSlideSearchQuery] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, addMessage, currentProject, setSlides: setStoreSlides, setAgentStatus, resetAgents } = useProjectStore()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentQuestion, stage])

  // Detect @ trigger in input for slide library search
  useEffect(() => {
    const lastAt = input.lastIndexOf('@')
    if (lastAt >= 0 && lastAt === input.length - 1) {
      setShowSlideSearch(true)
      setSlideSearchQuery('')
    }
  }, [input])

  // Fetch next question for stage 1
  const fetchQuestion = async (stepNum: number, ctx: string) => {
    if (!currentProject) return
    setLoading(true)
    try {
      const result = await planInteract(currentProject.id, {
        message: '', stage: 1, step: stepNum, url_context: ctx,
      })
      if (result.done) {
        // All questions answered, move to stage 2
        return true
      }
      if (result.url_context) setUrlContext(result.url_context)
      setCurrentQuestion({
        question: result.question,
        options: result.options || [],
        recommendation: result.recommendation,
        key: result.key,
      })
      return false
    } catch {
      addMessage('assistant', '❌ 加载问题失败')
      return false
    } finally {
      setLoading(false)
    }
  }

  const handleOptionSelect = async (value: string) => {
    if (!currentQuestion) return
    const newAnswers = { ...answers, [currentQuestion.key]: value }
    setAnswers(newAnswers)
    addMessage('user', value)
    setCurrentQuestion(null)

    const nextStep = step + 1
    setStep(nextStep)
    setAgentStatus('planner', 'running', `定位确认中 (${nextStep + 1}/5)`)

    const done = await fetchQuestion(nextStep, urlContext)
    if (done) {
      // All 5 questions answered → auto-generate outline
      const positioning = Object.entries(newAnswers).map(([k, v]) => `${k}: ${v}`).join('\n')
      addMessage('assistant', `✅ 定位已确认！正在生成大纲骨架...`)
      setAgentStatus('planner', 'running', '生成大纲骨架...')
      setStage(2)
      setLoading(true)
      try {
        const result = await planInteract(currentProject!.id, {
          message: '', stage: 2, positioning, url_context: urlContext,
        })
        setSlides(result.slides || [])
        addMessage('assistant', `${STAGE_LABELS[2]}\n\n已生成 ${result.slides?.length || 0} 页大纲\n\n💡 可以用自然语言修改，或输入"确认"进入下一阶段`)
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } }; message?: string }
        const detail = e.response?.data?.detail || e.message || '大纲生成失败'
        addMessage('assistant', `❌ ${detail}`)
        setAgentStatus('planner', 'error', detail)
      } finally {
        setLoading(false)
      }
    }
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || !currentProject) return
    addMessage('user', text)
    setInput('')
    setLoading(true)

    try {
      if (stage === 0) {
        // New request → start stage 1
        resetAgents()
        setAgentStatus('planner', 'running', '正在调研和分析需求...')
        addMessage('assistant', '🔍 正在调研和分析...')
        const result = await planInteract(currentProject.id, {
          message: text, stage: 1, step: 0,
        })
        const ctx = result.url_context || ''
        setUrlContext(ctx)
        setStage(1)
        setStep(0)
        setAgentStatus('planner', 'running', '定位确认中 (1/5)')

        if (ctx) {
          addMessage('assistant', '✅ 已获取网页资料，开始确认 PPT 定位')
        }

        // Show first question
        setCurrentQuestion({
          question: result.question,
          options: result.options || [],
          recommendation: result.recommendation,
          key: result.key,
        })

      } else if (stage === 1 && currentQuestion) {
        // Stage 1: User typed custom answer instead of clicking option
        handleOptionSelect(text)

      } else if (stage === 2 || stage === 3) {
        const isConfirm = /^(确认|可以|好的|没问题|下一步|ok|OK|开始生成|生成)$/i.test(text)

        if (isConfirm && stage === 2) {
          setAgentStatus('planner', 'running', '完善每页内容详情...')
          addMessage('assistant', '⏳ 正在完善每页内容...')
          const result = await planInteract(currentProject.id, {
            message: text, stage: 3, outline_skeleton: slides, url_context: urlContext,
          })
          setSlides(result.slides || [])
          setStage(3)
          setAgentStatus('planner', 'running', '等待用户确认内容详情')
          addMessage('assistant', `${STAGE_LABELS[3]}\n\n已完善 ${result.slides?.length || 0} 页内容\n\n💡 输入"确认"开始生成 PPT，或继续修改`)

        } else if (isConfirm && stage === 3) {
          setAgentStatus('planner', 'complete', '规划完成')
          addMessage('assistant', '🚀 大纲已确认，开始生成 PPT...')
          setStoreSlides(slides.map(s => ({
            slide_id: s.slide_id, title: s.title, layout: s.layout,
            status: 'todo' as const,
            points: Array.isArray(s.points) ? (s.points as unknown[]).map(normalizePoint) : [],
            locked: false,
          })))
          const result = await confirmAndGenerate(currentProject.id, { message: 'confirmed', outline_skeleton: slides })
          setStage(0)
          addMessage('assistant', `✅ 已提交 ${result.slides_count} 页 PPT 生成任务`)

        } else {
          // Natural language refinement
          const result = await planRefine(currentProject.id, { message: text, outline_skeleton: slides, url_context: urlContext })
          if (!result.unchanged) {
            setSlides(result.slides || [])
            addMessage('assistant', `✏️ ${result.message}`)
          } else {
            addMessage('assistant', result.message)
          }
        }
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const detail = e.response?.data?.detail || e.message || '请求失败'
      addMessage('assistant', `❌ ${detail}`)
      setAgentStatus('planner', 'error', detail)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setStage(0); setStep(0); setSlides([]); setAnswers({}); setCurrentQuestion(null); setUrlContext('')
  }

  function SlideSearchPopup({
    query,
    onSelect,
    onClose,
    onQueryChange,
  }: {
    query: string
    onSelect: (slide: LibrarySlide) => void
    onClose: () => void
    onQueryChange: (q: string) => void
  }) {
    const [results, setResults] = useState<LibrarySlide[]>([])
    const [searchLoading, setSearchLoading] = useState(false)

    useEffect(() => {
      if (!query) {
        setResults([])
        return
      }
      const timer = setTimeout(async () => {
        setSearchLoading(true)
        try {
          const data = await searchLibrarySlides(query)
          setResults(data)
        } catch { setResults([]) }
        setSearchLoading(false)
      }, 200)
      return () => clearTimeout(timer)
    }, [query])

    return (
      <div className="absolute bottom-full mb-2 left-0 right-0 bg-card border border-border rounded-xl shadow-xl z-50 max-h-64 overflow-y-auto">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/30 sticky top-0 bg-card">
          <span className="w-3.5 h-3.5 text-muted-foreground">@</span>
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="搜索企业库 slide..."
            className="flex-1 text-xs bg-transparent outline-none"
            autoFocus
          />
          <button onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">✕</button>
        </div>
        {searchLoading ? (
          <div className="px-3 py-4 text-center">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : results.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground text-center">
            {query ? '无匹配结果' : '输入关键词搜索企业库'}
          </p>
        ) : (
          results.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelect(s)}
              className="w-full text-left px-3 py-2 hover:bg-accent/30 transition-colors flex items-center gap-2 border-b border-border/10 last:border-0"
            >
              <span className="text-xs font-mono text-muted-foreground shrink-0">
                {s.slide_number || `#${s.slide_index}`}
              </span>
              <span className="text-xs truncate flex-1">{s.title}</span>
              <span className="text-[10px] text-muted-foreground capitalize">{s.layout_hint || 'slide'}</span>
            </button>
          ))
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center mt-12 space-y-3">
            <div className="text-4xl animate-float">🎯</div>
            <p className="text-lg font-medium gradient-text font-display">开始创建你的 PPT</p>
            <p className="text-sm text-muted-foreground max-w-xs mx-auto">输入需求开始生成，支持网址调研或上传 PDF/DOCX 源材料</p>
          </div>
        )}

        {messages.map((msg) => {
          // A-1 schema: only text cards render for now; other kinds ship in A-2
          if (msg.kind !== 'text') return null
          return (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm whitespace-pre-wrap transition-all ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground shadow-[0_0_15px_var(--glow-color)]'
                  : 'bg-muted/50 border border-border/30'
              }`}>{msg.content}</div>
            </div>
          )
        })}

        {/* Stage 1: Option buttons for current question */}
        {currentQuestion && (
          <div className="rounded-xl border border-border/50 p-4 bg-gradient-to-br from-primary/5 via-muted/20 to-transparent space-y-3">
            <p className="text-sm font-medium">❓ {currentQuestion.question}</p>
            <OptionButtons options={currentQuestion.options} onSelect={handleOptionSelect} recommendation={currentQuestion.recommendation} />
            <p className="text-xs text-muted-foreground">或在下方输入自定义答案</p>
          </div>
        )}

        {/* Stage 2/3: Outline display */}
        {slides.length > 0 && stage >= 2 && <OutlineView slides={slides} />}

        <AgentActivityFeed />

        {/* Stage indicator */}
        {stage > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground border-t border-border/30 pt-2">
            <MessageSquare className="w-3.5 h-3.5 text-primary" />
            <span>{STAGE_LABELS[stage]}{stage === 1 ? ` (${step + 1}/5)` : ''}</span>
            {stage < 3 && <><ArrowRight className="w-3 h-3" /><span className="opacity-50">{STAGE_LABELS[stage + 1]}</span></>}
            <button onClick={handleReset} className="ml-auto flex items-center gap-1 hover:text-primary transition-colors">
              <RotateCcw className="w-3 h-3" /> 重新开始
            </button>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="relative border-t border-border/50 p-3 space-y-2 bg-gradient-to-t from-card/30 to-transparent">
        {showSlideSearch && (
          <SlideSearchPopup
            query={slideSearchQuery}
            onSelect={(slide) => {
              const ref = `@slide:${slide.library_id}/${slide.slide_index} 「${slide.title}」`
              setInput((prev) => prev.replace(/@$/, ref))
              setShowSlideSearch(false)
            }}
            onClose={() => setShowSlideSearch(false)}
            onQueryChange={setSlideSearchQuery}
          />
        )}
        <div className="flex gap-2">
          <button
            onClick={() => setUploadOpen(true)}
            disabled={!currentProject}
            className="flex items-center gap-1.5 rounded-lg border border-border/50 px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent hover:border-primary/30 disabled:opacity-50 transition-all"
          >
            <Upload className="w-3.5 h-3.5" /> 添加源材料
          </button>
        </div>
        {uploadOpen && <UploadSourceModal onClose={() => setUploadOpen(false)} />}
        <div className="flex gap-2">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={currentQuestion ? '或输入自定义答案...' : stage === 0 ? '描述你的 PPT 需求...' : '输入修改意见或"确认"...'}
            disabled={!currentProject || loading}
            className="flex-1 rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 disabled:opacity-50 transition-all placeholder:text-muted-foreground/50" />
          <button onClick={handleSend} disabled={!currentProject || !input.trim() || loading}
            className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-50 transition-all font-medium">
            {loading ? '...' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
