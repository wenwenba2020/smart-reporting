import type { SlideItem } from '@/types/events'

export function ComparisonText({ slide }: { slide: SlideItem }) {
  const half = Math.ceil(slide.points.length / 2)
  const left = slide.points.slice(0, half)
  const right = slide.points.slice(half)
  return (
    <div className="absolute inset-0 flex flex-col px-2 py-2 bg-white">
      <h3 className="text-[10px] font-semibold text-slate-800 mb-1 line-clamp-1 text-center">
        {slide.title || '对比'}
      </h3>
      <div className="flex-1 min-h-0 grid grid-cols-2 gap-1 text-[7px]">
        <div className="bg-blue-50 rounded p-1 overflow-hidden">
          {left.map((p, i) => (
            <p key={i} className="text-slate-700 leading-tight line-clamp-1">• {p.heading}</p>
          ))}
        </div>
        <div className="bg-orange-50 rounded p-1 overflow-hidden">
          {right.map((p, i) => (
            <p key={i} className="text-slate-700 leading-tight line-clamp-1">• {p.heading}</p>
          ))}
        </div>
      </div>
    </div>
  )
}
