import type { SlideItem } from '@/types/events'
import { CoverText } from './CoverText'
import { SectionText } from './SectionText'
import { ContentText } from './ContentText'
import { ComparisonText } from './ComparisonText'
import { ChartText } from './ChartText'

export function TextLayout({ slide }: { slide: SlideItem }) {
  const layout = (slide.layout || '').toLowerCase()
  if (layout.includes('cover') || layout.includes('title')) return <CoverText slide={slide} />
  if (layout.includes('section') || layout.includes('chapter')) return <SectionText slide={slide} />
  if (layout.includes('comparison') || layout.includes('vs')) return <ComparisonText slide={slide} />
  if (layout.includes('chart')) return <ChartText slide={slide} />
  return <ContentText slide={slide} />
}
