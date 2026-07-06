import { useState, useEffect } from 'react';
import { Layout, Search } from 'lucide-react';
import { reportApi } from '../../api/reportClient';
import { Badge } from '../ui/Badge';

const CATEGORY_COLORS: Record<string, string> = {
  '指标类': 'bg-blue-100 text-blue-700', '进度类': 'bg-green-100 text-green-700',
  '分析类': 'bg-purple-100 text-purple-700', '总结类': 'bg-orange-100 text-orange-700',
  '评估类': 'bg-red-100 text-red-700',
};

export function TemplateBrowser() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('');

  useEffect(() => {
    reportApi.listTemplates().then(data => {
      const all = data.data || [];
      setTemplates(all);
      setFiltered(all);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    let result = templates;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t => t.name.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q));
    }
    if (selectedCategory) {
      result = result.filter(t => t.category === selectedCategory);
    }
    setFiltered(result);
  }, [search, selectedCategory, templates]);

  const categories = [...new Set(templates.map(t => t.category))];

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-6">
        <Layout className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">报告模板库</h1>
        <Badge variant="default">{filtered.length} 个</Badge>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/30 bg-card text-sm outline-none focus:border-primary/50"
            placeholder="搜索模板..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button onClick={() => setSelectedCategory('')}
            className={`px-3 py-2 rounded-lg text-xs ${!selectedCategory ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/70'}`}>
            全部
          </button>
          {categories.map(cat => (
            <button key={cat} onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-2 rounded-lg text-xs ${selectedCategory === cat ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/70'}`}>
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Template grid */}
      {loading ? (
        <div className="text-sm text-muted-foreground text-center py-12">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(t => (
            <div key={t.template_id} className="p-5 rounded-xl border border-border/30 bg-card hover:border-primary/30 transition-all">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-sm">{t.name}</h3>
                {t.parent_meta ? (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[t.category] || 'bg-gray-100'}`}>
                    {t.category}
                  </span>
                ) : (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">元模板</span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{t.description}</p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{t.section_count} 个章节</span>
                {t.parent_meta && <span className="text-muted-foreground/60">来源: {t.parent_meta}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
