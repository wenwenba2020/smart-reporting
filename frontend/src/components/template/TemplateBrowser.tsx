import { useState, useEffect } from 'react';
import { Layout, Search, Plus, X, Save, Trash2, Edit3 } from 'lucide-react';
import { reportApi } from '../../api/reportClient';
import { Badge } from '../ui/Badge';

const CATEGORIES = ['指标类', '进度类', '分析类', '总结类', '评估类'];
const CATEGORY_COLORS: Record<string, string> = {
  '指标类': 'bg-blue-100 text-blue-700', '进度类': 'bg-green-100 text-green-700',
  '分析类': 'bg-purple-100 text-purple-700', '总结类': 'bg-orange-100 text-orange-700',
  '评估类': 'bg-red-100 text-red-700',
};

interface TemplateDetail {
  template_id: string; name: string; category: string; description: string;
  system_prompt: string; is_custom: boolean;
  sections: Array<{key:string; title:string; required:boolean; description:string; source:string; suggested_length:string}>;
}

export function TemplateBrowser() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('');

  // Detail modal
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Editor
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<{
    template_id?: string; name: string; category: string; description: string;
    system_prompt: string; sections: any[];
  }>({ name: '', category: '进度类', description: '', system_prompt: '', sections: [] });
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadTemplates(); }, []);

  const loadTemplates = () => {
    setLoading(true);
    reportApi.listTemplates().then(templates => {
      if (Array.isArray(templates)) { setTemplates(templates); setFiltered(templates); }
      else { setError(`数据格式异常: ${typeof templates}`); }
      setLoading(false);
    }).catch((e) => { setError(e instanceof Error ? e.message : String(e)); setLoading(false); });
  };

  useEffect(() => {
    let result = templates;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t => t.name.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q));
    }
    if (selectedCategory) result = result.filter(t => t.category === selectedCategory);
    setFiltered(result);
  }, [search, selectedCategory, templates]);

  const categories = [...new Set(templates.map(t => t.category))];

  const openDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const data = await reportApi.getTemplate(id);
      setDetail(data);
    } catch (e) { console.error(e); }
    finally { setDetailLoading(false); }
  };

  const startCreate = () => {
    setEditData({ name: '', category: '进度类', description: '', system_prompt: '', sections: [{ key: 'section_1', title: '章节一', required: true, description: '', source: 'generated', suggested_length: 'medium' }] });
    setEditing(true);
  };

  const startEdit = (tpl: TemplateDetail) => {
    setEditData({ template_id: tpl.template_id, name: tpl.name, category: tpl.category, description: tpl.description, system_prompt: tpl.system_prompt || '', sections: tpl.sections.map(s => ({...s})) });
    setEditing(true);
    setDetail(null);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = { name: editData.name, category: editData.category, description: editData.description, system_prompt: editData.system_prompt, sections: editData.sections, template_id: editData.template_id };
      if (editData.template_id) {
        await reportApi.updateTemplate(editData.template_id, data);
      } else {
        const id = `custom_${editData.name.toLowerCase().replace(/[^a-z0-9一-鿿]/g, '_').replace(/_+/g, '_')}`;
        await reportApi.createTemplate({ ...data, template_id: id });
      }
      setEditing(false);
      loadTemplates();
    } catch (e) { alert('保存失败: ' + (e instanceof Error ? e.message : e)); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此模板？')) return;
    try { await reportApi.deleteTemplate(id); setDetail(null); loadTemplates(); }
    catch (e) { alert('删除失败: ' + (e instanceof Error ? e.message : e)); }
  };

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Layout className="w-5 h-5 text-primary" />
          <h1 className="text-xl font-bold">报告模板库</h1>
          <Badge variant="default">{filtered.length} 个</Badge>
        </div>
        <button onClick={startCreate} className="flex items-center gap-1 px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:shadow-[0_0_15px_var(--glow-color)]">
          <Plus className="w-4 h-4" />新建模板
        </button>
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
            className={`px-3 py-2 rounded-lg text-xs ${!selectedCategory ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/70'}`}>全部</button>
          {categories.map(cat => (
            <button key={cat} onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-2 rounded-lg text-xs ${selectedCategory === cat ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/70'}`}>{cat}</button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-sm mb-4"><p className="font-medium">加载失败</p><p className="text-xs mt-1 font-mono">{error}</p></div>}

      {/* Template grid */}
      {loading ? <div className="text-sm text-muted-foreground text-center py-12">加载中...</div> : error && filtered.length === 0 ? <div className="text-sm text-muted-foreground text-center py-12">加载失败，请刷新重试</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(t => (
            <div key={t.template_id} onClick={() => openDetail(t.template_id)}
              className="p-5 rounded-xl border border-border/30 bg-card hover:border-primary/30 hover:shadow-sm transition-all cursor-pointer">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-sm">{t.name}</h3>
                <div className="flex gap-1">
                  {t.is_custom && <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700">自定义</span>}
                  <span className={`text-xs px-2 py-0.5 rounded-full ${t.parent_meta ? (CATEGORY_COLORS[t.category] || 'bg-gray-100') : 'bg-gray-100 text-gray-500'}`}>
                    {t.parent_meta ? t.category : '元模板'}
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{t.description}</p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{t.section_count} 个章节</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {detailLoading && <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"><div className="bg-card p-8 rounded-xl text-sm">加载中...</div></div>}
      {detail && (
        <div className="fixed inset-0 bg-black/30 flex items-start justify-center pt-20 z-50" onClick={() => setDetail(null)}>
          <div className="bg-card rounded-xl border border-border/30 shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-card border-b border-border/30 p-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold">{detail.name}</h2>
                <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[detail.category] || 'bg-gray-100'}`}>{detail.category}</span>
                {detail.is_custom && <span className="text-xs ml-2 px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700">自定义</span>}
              </div>
              <div className="flex gap-2">
                {!detail.is_custom && (
                  <button onClick={() => startEdit({...detail, name: detail.name + ' (自定义)', template_id: ''})}
                    className="flex items-center gap-1 px-2 py-1 bg-primary text-primary-foreground text-xs rounded-lg hover:bg-primary/90">
                    <Edit3 className="w-3 h-3" />基于此创建
                  </button>
                )}
                {detail.is_custom && (
                  <>
                    <button onClick={() => startEdit(detail)} className="p-1.5 rounded hover:bg-accent"><Edit3 className="w-4 h-4" /></button>
                    <button onClick={() => handleDelete(detail.template_id)} className="p-1.5 rounded hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                  </>
                )}
                <button onClick={() => setDetail(null)} className="p-1.5 rounded hover:bg-accent"><X className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="p-4 space-y-4">
              <p className="text-sm text-muted-foreground">{detail.description}</p>
              {detail.system_prompt && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 mb-1">System Prompt</h4>
                  <pre className="text-xs bg-muted p-3 rounded-lg whitespace-pre-wrap">{detail.system_prompt}</pre>
                </div>
              )}
              <div>
                <h4 className="text-xs font-semibold text-gray-500 mb-2">报告章节 ({detail.sections.length})</h4>
                <div className="space-y-2">
                  {detail.sections.map((s, i) => (
                    <div key={s.key} className="flex items-start gap-3 p-3 rounded-lg border border-border/30">
                      <span className="text-xs text-muted-foreground w-6 pt-0.5">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{s.title}</span>
                          {s.required && <span className="text-xs px-1 rounded bg-red-50 text-red-500">必填</span>}
                          <span className="text-xs text-muted-foreground">{s.source === 'enterprise_ppt' ? '🏢PPT库' : '✍️生成'}</span>
                        </div>
                        {s.description && <p className="text-xs text-muted-foreground mt-0.5">{s.description}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Editor Modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/30 flex items-start justify-center pt-10 z-50">
          <div className="bg-card rounded-xl border border-border/30 shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-card border-b border-border/30 p-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">{editData.template_id ? '编辑模板' : '新建模板'}</h2>
              <button onClick={() => setEditing(false)} className="p-1.5 rounded hover:bg-accent"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium">模板名称 *</label>
                  <input className="w-full mt-1 p-2 text-sm border rounded-lg" value={editData.name}
                    onChange={e => setEditData(p => ({...p, name: e.target.value}))} placeholder="如：客户分析报告" />
                </div>
                <div>
                  <label className="text-xs font-medium">类别</label>
                  <select className="w-full mt-1 p-2 text-sm border rounded-lg" value={editData.category}
                    onChange={e => setEditData(p => ({...p, category: e.target.value}))}>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium">描述</label>
                <textarea className="w-full mt-1 p-2 text-sm border rounded-lg" rows={2} value={editData.description}
                  onChange={e => setEditData(p => ({...p, description: e.target.value}))} placeholder="模板用途说明" />
              </div>
              <div>
                <label className="text-xs font-medium">System Prompt</label>
                <textarea className="w-full mt-1 p-2 text-sm border rounded-lg font-mono" rows={3} value={editData.system_prompt}
                  onChange={e => setEditData(p => ({...p, system_prompt: e.target.value}))} placeholder="LLM 提示词" />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium">章节 ({editData.sections.length})</label>
                  <button onClick={() => setEditData(p => ({...p, sections: [...p.sections, {key: `section_${p.sections.length+1}`, title: `新章节`, required: false, description: '', source: 'generated', suggested_length: 'medium'}]}))}
                    className="text-xs text-primary hover:underline">+ 添加章节</button>
                </div>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {editData.sections.map((s, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded border border-border/30">
                      <span className="text-xs text-muted-foreground w-5">{i+1}.</span>
                      <input className="flex-1 text-xs p-1.5 border rounded" value={s.title}
                        onChange={e => { const ns = [...editData.sections]; ns[i] = {...ns[i], title: e.target.value}; setEditData(p => ({...p, sections: ns})); }} placeholder="章节标题" />
                      <input className="w-24 text-xs p-1.5 border rounded" value={s.key}
                        onChange={e => { const ns = [...editData.sections]; ns[i] = {...ns[i], key: e.target.value}; setEditData(p => ({...p, sections: ns})); }} placeholder="key" />
                      <button onClick={() => { const ns = editData.sections.filter((_, j) => j !== i); setEditData(p => ({...p, sections: ns})); }}
                        className="p-1 text-red-400 hover:text-red-600"><X className="w-3 h-3" /></button>
                    </div>
                  ))}
                </div>
              </div>
              <button onClick={handleSave} disabled={saving || !editData.name.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm disabled:opacity-50">
                <Save className="w-4 h-4" />{saving ? '保存中...' : '保存模板'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
