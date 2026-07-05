import type { SlideItem } from '@/types/events'

export function CoverText({ slide }: { slide: SlideItem }) {
  const subtitle = slide.points[0]?.heading || ''
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4 bg-gradient-to-br from-blue-50 to-white">
      <h2 className="text-[13px] font-bold text-slate-800 leading-tight mb-1 line-clamp-2">
        {slide.title || '未命名封面'}
      </h2>
      {subtitle && (
        <p className="text-[9px] text-slate-500 line-clamp-1">{subtitle}</p>
      )}
    </div>
  )
}
