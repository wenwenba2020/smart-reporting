import { create } from 'zustand'
import type { KnowledgeBase } from '@/types/events'
import {
  listKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase,
  uploadToKnowledgeBase,
} from '@/api/client'

interface KnowledgeStore {
  bases: KnowledgeBase[]
  loading: boolean
  selectedKbId: string | null

  loadBases: () => Promise<void>
  createBase: (name: string, category: string) => Promise<void>
  removeBase: (id: string) => Promise<void>
  uploadFile: (kbId: string, file: File) => Promise<number>
  selectKb: (id: string | null) => void
}

export const useKnowledgeStore = create<KnowledgeStore>((set, get) => ({
  bases: [],
  loading: false,
  selectedKbId: null,

  loadBases: async () => {
    set({ loading: true })
    try {
      const bases = await listKnowledgeBases()
      set({ bases, loading: false })
    } catch { set({ loading: false }) }
  },

  createBase: async (name, category) => {
    await createKnowledgeBase({ name, category })
    await get().loadBases()
  },

  removeBase: async (id) => {
    await deleteKnowledgeBase(id)
    if (get().selectedKbId === id) set({ selectedKbId: null })
    await get().loadBases()
  },

  uploadFile: async (kbId, file) => {
    const result = await uploadToKnowledgeBase(kbId, file)
    await get().loadBases()
    return result.chunks_created
  },

  selectKb: (id) => set({ selectedKbId: id }),
}))
