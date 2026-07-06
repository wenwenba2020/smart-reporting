import { useState, useEffect } from 'react';
import { reportApi } from '../../api/reportClient';
import type { PPTDeck } from '../../types';

interface Props {
  selectedId?: string;
  onSelect: (deckId: string | null) => void;
}

export function PPTTemplateSelector({ selectedId, onSelect }: Props) {
  const [templates, setTemplates] = useState<PPTDeck[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const result = await reportApi.listPPTTemplates();
      setTemplates((result as any).data || []);
    } catch (e) {
      console.error('Failed to load PPT templates:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await reportApi.uploadPPT(file, 'template');
      await loadTemplates();
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">加载PPT模板...</div>;
  }

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">选择 PPT 模板</h3>

      {templates.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <p className="text-sm">暂无企业 PPT 模板</p>
          <p className="text-xs mt-1">上传 .pptx 文件作为样式模板</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 mb-4">
          {templates.map((tpl) => (
            <button
              key={tpl.deck_id}
              onClick={() => onSelect(tpl.deck_id === selectedId ? null : tpl.deck_id)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                tpl.deck_id === selectedId
                  ? 'border-blue-500 bg-blue-50 shadow-sm'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <div className="text-sm font-medium text-gray-800 truncate">
                {tpl.name || tpl.filename}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {tpl.slide_count} slides
                {tpl.is_default && (
                  <span className="ml-2 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                    默认
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Upload new template */}
      <label className={`block w-full p-3 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors ${
        uploading ? 'border-gray-300 bg-gray-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
      }`}>
        <input
          type="file"
          accept=".pptx"
          onChange={handleUpload}
          disabled={uploading}
          className="hidden"
        />
        <span className="text-sm text-gray-500">
          {uploading ? '上传中...' : '+ 上传新模板 (.pptx)'}
        </span>
      </label>

      {selectedId && (
        <div className="mt-3 text-xs text-blue-600">
          已选择: {templates.find(t => t.deck_id === selectedId)?.name || selectedId}
        </div>
      )}
    </div>
  );
}
