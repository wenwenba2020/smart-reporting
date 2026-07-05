import { create } from 'zustand'
import type { LibraryDeck, LibrarySlide } from '@/types/events'
import {
  listLibraryDecks,
  getLibraryDeck,
  uploadToLibrary,
  deleteLibraryDeck,
  updateLibraryDeckName,
  updateLibrarySlide,
  importSlidesToProject,
} from '@/api/client'

interface SlideLibraryState {
  decks: LibraryDeck[]
  expandedDeckId: string | null
  expandedSlides: LibrarySlide[]
  loading: boolean
  searchQuery: string
  uploadError: string | null

  selectionMode: boolean
  selectedSlideIds: string[]

  loadDecks: () => Promise<void>
  toggleExpand: (deckId: string) => Promise<void>
  uploadDeck: (file: File) => Promise<string | null>
  removeDeck: (id: string) => Promise<void>
  renameDeck: (id: string, name: string) => Promise<void>
  patchSlide: (id: string, data: { slide_number?: string | null; tags?: string[] }) => Promise<void>
  importToProject: (projectId: string, slideIds: string[]) => Promise<number>
  setSearchQuery: (q: string) => void

  enterSelection: () => void
  exitSelection: () => void
  toggleSelect: (slideId: string) => void
  selectAllInDeck: (slideIds: string[]) => void
  getSelectedCount: () => number
}

export const useSlideLibraryStore = create<SlideLibraryState>()((set, get) => ({
  decks: [],
  expandedDeckId: null,
  expandedSlides: [],
  loading: false,
  searchQuery: '',
  uploadError: null,

  selectionMode: false,
  selectedSlideIds: [],

  loadDecks: async () => {
    set({ loading: true })
    try {
      const decks = await listLibraryDecks()
      set({ decks, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  toggleExpand: async (deckId: string) => {
    const { expandedDeckId } = get()
    if (expandedDeckId === deckId) {
      set({ expandedDeckId: null, expandedSlides: [] })
    } else {
      const data = await getLibraryDeck(deckId)
      set({ expandedDeckId: deckId, expandedSlides: data.slides })
    }
  },

  uploadDeck: async (file: File) => {
    set({ uploadError: null })
    try {
      const result = await uploadToLibrary(file)
      await get().loadDecks()
      return result.library_id
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = e.response?.data?.detail || e.message || '上传失败'
      set({ uploadError: msg })
      return null
    }
  },

  removeDeck: async (id: string) => {
    await deleteLibraryDeck(id)
    const { expandedDeckId } = get()
    if (expandedDeckId === id) {
      set({ expandedDeckId: null, expandedSlides: [] })
    }
    await get().loadDecks()
  },

  renameDeck: async (id: string, name: string) => {
    await updateLibraryDeckName(id, name)
    await get().loadDecks()
  },

  patchSlide: async (id: string, data) => {
    await updateLibrarySlide(id, data)
    const { expandedDeckId } = get()
    if (expandedDeckId) {
      const refreshed = await getLibraryDeck(expandedDeckId)
      set({ expandedSlides: refreshed.slides })
    }
  },

  importToProject: async (projectId, slideIds) => {
    const result = await importSlidesToProject(projectId, slideIds)
    return result.total_slides
  },

  setSearchQuery: (q: string) => set({ searchQuery: q }),

  enterSelection: () => set({ selectionMode: true, selectedSlideIds: [] }),

  exitSelection: () => set({ selectionMode: false, selectedSlideIds: [] }),

  toggleSelect: (slideId: string) =>
    set((state) => {
      const next = state.selectedSlideIds.includes(slideId)
        ? state.selectedSlideIds.filter((id) => id !== slideId)
        : [...state.selectedSlideIds, slideId]
      return { selectedSlideIds: next }
    }),

  selectAllInDeck: (slideIds: string[]) =>
    set((state) => {
      const allSelected = slideIds.every((id) => state.selectedSlideIds.includes(id))
      if (allSelected) {
        return { selectedSlideIds: state.selectedSlideIds.filter((id) => !slideIds.includes(id)) }
      }
      return { selectedSlideIds: slideIds }
    }),

  getSelectedCount: () => get().selectedSlideIds.length,
}))
