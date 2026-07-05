import { create } from 'zustand'

export type ReportType = 'ppt' | 'docx' | 'pdf'
export type NavSection = 'create' | 'history' | 'datasources' | 'templates' | 'settings'

interface ReportState {
  navSection: NavSection
  reportType: ReportType
  scenarioId: string | null
  selectedSources: string[]
  query: string

  setNav: (section: NavSection) => void
  setReportType: (type: ReportType) => void
  setScenario: (id: string | null) => void
  toggleSource: (sourceType: string) => void
  setQuery: (q: string) => void
}

export const useReportStore = create<ReportState>((set) => ({
  navSection: 'create',
  reportType: 'ppt',
  scenarioId: null,
  selectedSources: ['knowledge_base', 'case_library'],
  query: '',

  setNav: (section) => set({ navSection: section }),
  setReportType: (type) => set({ reportType: type }),
  setScenario: (id) => set({ scenarioId: id }),
  toggleSource: (sourceType) => set((s) => ({
    selectedSources: s.selectedSources.includes(sourceType)
      ? s.selectedSources.filter(t => t !== sourceType)
      : [...s.selectedSources, sourceType],
  })),
  setQuery: (q) => set({ query: q }),
}))
