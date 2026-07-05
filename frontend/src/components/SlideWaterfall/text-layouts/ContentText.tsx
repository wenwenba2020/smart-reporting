import type { SlideItem } from '@/types/events'

export function ContentText({ slide }: { slide: SlideItem }) {
  const shown = slide.points.slice(0, 5)
  const rest = slide.points.length - shown.length
  return (
    <div className="absolute inset-0 flex flex-col px-3 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 border-b border-slate-200 pb-1">
        {slide.title || '内容页'}
      </h3>
      <ul className="flex-1 min-h-0 space-y-1 overflow-hidden">
        {shown.map((p, i) => (
          <li key={i} className="leading-tight">
            <div className="flex gap-1 text-[8px] text-slate-800 font-medium">
              <span className="text-slate-400 shrink-0">•</span>
              <span className="line-clamp-1">{p.heading}</span>
            </div>
            {p.body && (
              <p className="text-[7px] text-slate-500 line-clamp-2 pl-2 mt-0.5">
                {p.body}
              </p>
            )}
          </li>
        ))}
        {rest > 0 && (
          <li className="text-slate-400 italic text-[7px]">… 还有 {rest} 条</li>
        )}
      </ul>
    </div>
  )
}
