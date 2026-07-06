import { useState, useEffect } from 'react';
import { reportApi } from '../../api/reportClient';
import type { PPTDeck, PPTSlide } from '../../types';

interface Props {
  onSelectSlides: (slides: PPTSlide[]) => void;
  selectedSlideIds?: string[];
}

export function PPTLibraryBrowser({ onSelectSlides, selectedSlideIds = [] }: Props) {
  const [decks, setDecks] = useState<PPTDeck[]>([]);
  const [selectedDeck, setSelectedDeck] = useState<string | null>(null);
  const [slides, setSlides] = useState<PPTSlide[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(selectedSlideIds));
  const [loading, setLoading] = useState(true);
  const [slidesLoading, setSlidesLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDecks();
  }, []);

  const loadDecks = async () => {
    try {
      const data = await reportApi.listPPTDecks();
      setDecks(data.data || []);
    } catch (e) {
      console.error('Failed to load PPT decks:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadSlides = async (deckId: string) => {
    setSlidesLoading(true);
    setSelectedDeck(deckId);
    try {
      const data = await reportApi.getPPTDeck(deckId);
      setSlides((data as any).slides || []);
    } catch (e) {
      console.error('Failed to load slides:', e);
    } finally {
      setSlidesLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!search.trim()) return;
    setSlidesLoading(true);
    setSelectedDeck(null);
    try {
      const data = await reportApi.searchPPTSlides(search);
      setSlides((data.data || []) as PPTSlide[]);
    } catch (e) {
      console.error('Search failed:', e);
    } finally {
      setSlidesLoading(false);
    }
  };

  const toggleSlide = (slide: PPTSlide) => {
    const next = new Set(selected);
    if (next.has(slide.slide_id)) {
      next.delete(slide.slide_id);
    } else {
      next.add(slide.slide_id);
    }
    setSelected(next);
    const allSlides = [...next].map(id => slides.find(s => s.slide_id === id)!).filter(Boolean);
    onSelectSlides(allSlides);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await reportApi.uploadPPT(file, 'content');
      await loadDecks();
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">加载企业PPT库...</div>;
  }

  return (
    <div className="flex h-full">
      {/* Left: Deck list */}
      <div className="w-56 border-r bg-gray-50 overflow-y-auto p-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">PPT 库</h3>

        {/* Search */}
        <div className="flex gap-1 mb-3">
          <input
            className="flex-1 text-xs border rounded px-2 py-1"
            placeholder="搜索Slide..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          <button
            className="px-2 py-1 bg-gray-200 text-xs rounded hover:bg-gray-300"
            onClick={handleSearch}
          >
            搜
          </button>
        </div>

        {/* Deck list */}
        {decks.map(deck => (
          <button
            key={deck.deck_id}
            onClick={() => loadSlides(deck.deck_id)}
            className={`w-full text-left px-2 py-1.5 rounded text-xs mb-0.5 transition-colors ${
              selectedDeck === deck.deck_id
                ? 'bg-blue-100 text-blue-800 font-medium'
                : 'hover:bg-gray-200 text-gray-700'
            }`}
          >
            <div className="truncate">{deck.filename}</div>
            <div className="text-gray-400">{deck.slide_count} slides</div>
          </button>
        ))}

        {/* Upload */}
        <label className={`block w-full mt-3 p-2 border border-dashed rounded text-center text-xs cursor-pointer transition-colors ${
          uploading ? 'bg-gray-100 text-gray-400' : 'text-gray-500 hover:border-blue-400 hover:bg-blue-50'
        }`}>
          <input type="file" accept=".pptx" onChange={handleUpload} disabled={uploading} className="hidden" />
          {uploading ? '上传中...' : '+ 上传PPT'}
        </label>
      </div>

      {/* Right: Slide grid */}
      <div className="flex-1 overflow-y-auto p-3">
        {slidesLoading ? (
          <div className="text-sm text-gray-400 py-8 text-center">加载中...</div>
        ) : slides.length === 0 ? (
          <div className="text-sm text-gray-400 py-8 text-center">
            {selectedDeck ? '该 PPT 暂无 Slide 数据' : '选择左侧 PPT 文件查看 Slide'}
          </div>
        ) : (
          <>
            <div className="text-xs text-gray-500 mb-2">
              {slides.length} slides · 已选 {selected.size}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {slides.map(slide => (
                <button
                  key={slide.slide_id}
                  onClick={() => toggleSlide(slide)}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    selected.has(slide.slide_id)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-800 truncate flex-1">
                      {slide.title || `Slide ${slide.slide_index}`}
                    </span>
                    <span className="text-xs text-gray-400 ml-1">P{slide.slide_index}</span>
                  </div>
                  <div className="text-xs text-gray-500 line-clamp-2 mb-1">
                    {slide.content_summary}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {slide.topic_tags?.slice(0, 3).map(tag => (
                      <span key={tag} className="px-1 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                        {tag}
                      </span>
                    ))}
                    <span className="px-1 py-0.5 bg-gray-50 text-gray-400 rounded text-xs">
                      {slide.section_type}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
