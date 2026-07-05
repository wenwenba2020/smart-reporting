import type { SlideItem } from '@/types/events'

export function SectionText({ slide }: { slide: SlideItem }) {
  const num = slide.slide_id.padStart(2, '0')
  return (
    <div className="absolute inset-0 flex items-center gap-2 px-3 bg-slate-50">
      <div className="text-[28px] font-black text-slate-300 leading-none shrink-0">
        {num}
      </div>
      <div className="flex-1 min-w-0 border-l-2 border-slate-300 pl-2">
        <h3 className="text-[11px] font-semibold text-slate-800 line-clamp-2">
          {slide.title || '章节'}
        </h3>
      </div>
    </div>
  )
}
