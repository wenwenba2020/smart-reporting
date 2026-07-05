import { create } from 'zustand'
import type { ScenarioTemplate, ScenarioDetail } from '@/types/events'
import { listScenarios, getScenarioDetail } from '@/api/client'

interface ScenarioStore {
  scenarios: ScenarioTemplate[]
  selectedId: string | null
  selectedDetail: ScenarioDetail | null
  loading: boolean

  loadScenarios: () => Promise<void>
  selectScenario: (id: string | null) => Promise<void>
}

export const useScenarioStore = create<ScenarioStore>((set) => ({
  scenarios: [],
  selectedId: null,
  selectedDetail: null,
  loading: false,

  loadScenarios: async () => {
    set({ loading: true })
    try {
      const scenarios = await listScenarios()
      set({ scenarios, loading: false })
    } catch { set({ loading: false }) }
  },

  selectScenario: async (id) => {
    if (!id) {
      set({ selectedId: null, selectedDetail: null })
      return
    }
    set({ selectedId: id })
    try {
      const detail = await getScenarioDetail(id)
      set({ selectedDetail: detail })
    } catch {}
  },
}))
