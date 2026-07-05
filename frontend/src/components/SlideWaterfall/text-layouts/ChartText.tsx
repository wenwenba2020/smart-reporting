import type { SlideItem } from '@/types/events'

export function ChartText({ slide }: { slide: SlideItem }) {
  const shown = slide.points.slice(0, 3)
  return (
    <div className="absolute inset-0 flex flex-col px-3 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 border-b border-slate-200 pb-1">
        {slide.title || '图表页'}
      </h3>
      <div className="bg-slate-100 rounded h-8 flex items-center justify-center text-[9px] text-slate-500 mb-1">
        📊 图表占位
      </div>
      <ul className="flex-1 min-h-0 text-[8px] text-slate-600">
        {shown.map((p, i) => (
          <li key={i} className="line-clamp-1 leading-tight">• {p.heading}</li>
        ))}
      </ul>
    </div>
  )
}
