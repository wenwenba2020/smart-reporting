import { useState, useEffect } from 'react';
import { Database, FileText, Trash2, X, RefreshCw } from 'lucide-react';
import { reportApi } from '../../api/reportClient';
import { Badge } from '../ui/Badge';

const TYPE_LABELS: Record<string, string> = {
  file_upload: '文件上传', chat_export: '聊天记录', enterprise_ppt: '企业PPT',
  rest_api: 'REST API', mcp: 'MCP工具', database: '数据库', knowledge_base: 'RAG知识库',
};

export function DataSourceManager() {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadSources = async () => {
    setLoading(true);
    try {
      const data = await reportApi.listDatasources();
      setSources(data.data || []);
    } catch (e) { console.error('Failed to load sources', e); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadSources(); }, []);

  const handleDelete = async (id: string) => {
    try {
      await reportApi.deleteDatasource(id);
      setSources(prev => prev.filter(s => s.id !== id));
    } catch (e) { console.error('Delete failed', e); }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-primary" />
          <h1 className="text-xl font-bold">数据源管理</h1>
          <Badge variant="default">{sources.length} 个</Badge>
        </div>
        <button onClick={loadSources} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw className="w-3 h-3" />刷新
        </button>
      </div>

      {loading ? (
        <div className="text-sm text-muted-foreground text-center py-12">加载中...</div>
      ) : sources.length === 0 ? (
        <div className="rounded-xl border border-border/30 bg-card p-12 text-center">
          <Database className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
          <p className="text-sm text-muted-foreground">暂无数据源</p>
          <p className="text-xs text-muted-foreground/70 mt-1">在"智能报告生成"页面上传文件或通过高级数据源获取数据</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sources.map((s: any) => (
            <div key={s.id} className="flex items-center gap-3 p-4 rounded-xl bg-card border border-border/30">
              <FileText className="w-5 h-5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{s.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
                    {TYPE_LABELS[s.source_type] || s.source_type}
                  </span>
                  {s.metadata && Object.entries(s.metadata as Record<string,unknown>).slice(0,2).map(([k,v]) => (
                    <span key={k} className="text-xs text-muted-foreground/70">{k}: {String(v).slice(0,40)}</span>
                  ))}
                </div>
              </div>
              <button onClick={() => handleDelete(s.id)}
                className="p-1.5 rounded hover:bg-destructive/10 hover:text-destructive transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
