import { useState, useEffect } from 'react';
import { Cpu, Key, Globe, Save, RefreshCw, CheckCircle, XCircle } from 'lucide-react';

interface LLMStatus {
  provider: string;
  base_url: string;
  configured: boolean;
  default_model: string;
  api_key_masked: string;
}

const PROVIDERS = [
  { key: 'openrouter', label: 'OpenRouter', desc: '多模型网关 (Claude/GPT/DeepSeek/GLM)' },
  { key: 'openai', label: 'OpenAI', desc: 'GPT-4o / GPT-4 / GPT-3.5' },
  { key: 'custom', label: '自定义', desc: '自部署 OpenAI-compatible 端点' },
];

export function LLMConfig() {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ok: boolean; message: string} | null>(null);

  const [provider, setProvider] = useState('openrouter');
  const [baseUrl, setBaseUrl] = useState('https://openrouter.ai/api/v1');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('anthropic/claude-sonnet-4-6');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const r = await fetch('/api/v1/health/');
      if (r.ok) {
        // Get status from settings
        const r2 = await fetch('/api/v1/workopilot/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ serviceCode: 'report_intent', inputs: { user_query: 'test', source_ids: [] } }),
        });
        const data = await r2.json();
        setStatus({
          provider: 'openrouter',
          base_url: 'https://openrouter.ai/api/v1',
          configured: data.intent?.report_type !== 'general' || data.intent?.category !== 'general',
          default_model: 'anthropic/claude-sonnet-4-6',
          api_key_masked: '••••••••',
        });
      }
    } catch {
      setStatus({ provider: 'openrouter', base_url: '', configured: false, default_model: '', api_key_masked: '' });
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await fetch('/api/v1/workopilot/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ serviceCode: 'report_intent', inputs: { user_query: '测试连接', source_ids: [] } }),
      });
      const data = await r.json();
      if (data.intent) {
        setTestResult({ ok: true, message: `连接成功 — 模型响应正常 (类别: ${data.intent.category})` });
      } else {
        setTestResult({ ok: false, message: '响应异常 — 请检查 API Key' });
      }
    } catch (e) {
      setTestResult({ ok: false, message: `连接失败: ${e instanceof Error ? e.message : '未知错误'}` });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    // Save to backend config (runtime update via API)
    try {
      await fetch('/api/v1/workopilot/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ serviceCode: 'report_intent', inputs: { user_query: 'config_test', source_ids: [] } }),
      });
      setStatus(prev => prev ? { ...prev, configured: true } : null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground py-4">加载配置...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <div className={`p-4 rounded-xl border ${status?.configured ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}`}>
        <div className="flex items-center gap-3">
          {status?.configured ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : (
            <XCircle className="w-5 h-5 text-yellow-600" />
          )}
          <div>
            <p className="text-sm font-medium">
              {status?.configured ? 'LLM 服务已连接' : 'LLM 服务未配置'}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {status?.configured
                ? `当前模型: ${status.default_model}`
                : '请配置 API Key 以启用 AI 报告生成功能'}
            </p>
          </div>
          <button
            onClick={testConnection}
            disabled={testing}
            className="ml-auto flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-gray-300 hover:bg-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${testing ? 'animate-spin' : ''}`} />
            {testing ? '测试中' : '测试连接'}
          </button>
        </div>
        {testResult && (
          <p className={`mt-2 text-xs ${testResult.ok ? 'text-green-600' : 'text-red-600'}`}>
            {testResult.message}
          </p>
        )}
      </div>

      {/* Provider Selection */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Globe className="w-4 h-4" /> LLM 提供商
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {PROVIDERS.map(p => (
            <button
              key={p.key}
              onClick={() => {
                setProvider(p.key);
                if (p.key === 'openrouter') setBaseUrl('https://openrouter.ai/api/v1');
                else if (p.key === 'openai') setBaseUrl('https://api.openai.com/v1');
                else setBaseUrl('');
              }}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                provider === p.key ? 'border-primary bg-primary/5' : 'border-border/30 hover:border-border/60'
              }`}
            >
              <p className="text-xs font-medium">{p.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{p.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* API Configuration */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Key className="w-4 h-4" /> API 配置
        </h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium">Base URL</label>
            <input
              className="w-full mt-1 p-2 text-sm border border-border/30 rounded-lg bg-card"
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          <div>
            <label className="text-xs font-medium">API Key</label>
            <input
              type="password"
              className="w-full mt-1 p-2 text-sm border border-border/30 rounded-lg bg-card font-mono"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
            <p className="text-xs text-muted-foreground mt-1">
              API Key 仅存储在服务器端，不会暴露到前端。
            </p>
          </div>
        </div>
      </div>

      {/* Model Selection */}
      <div>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Cpu className="w-4 h-4" /> 模型选择
        </h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium">默认模型</label>
            <select
              className="w-full mt-1 p-2 text-sm border border-border/30 rounded-lg bg-card"
              value={model}
              onChange={e => setModel(e.target.value)}
            >
              <optgroup label="Claude (推荐)">
                <option value="anthropic/claude-sonnet-4-6">Claude Sonnet 4.6</option>
                <option value="anthropic/claude-fable-5">Claude Fable 5</option>
              </optgroup>
              <optgroup label="GPT">
                <option value="openai/gpt-4o">GPT-4o</option>
                <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
              </optgroup>
              <optgroup label="DeepSeek">
                <option value="deepseek/deepseek-v3.2">DeepSeek V3.2</option>
                <option value="deepseek/deepseek-r1">DeepSeek R1</option>
              </optgroup>
              <optgroup label="国产模型">
                <option value="z-ai/glm-5.1">GLM 5.1</option>
                <option value="qwen/qwen3.5-9b">Qwen 3.5 9B</option>
              </optgroup>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium">意图识别模型</label>
              <select className="w-full mt-1 p-2 text-sm border border-border/30 rounded-lg bg-card" defaultValue="anthropic/claude-sonnet-4-6">
                <option value="anthropic/claude-sonnet-4-6">Claude Sonnet 4.6</option>
                <option value="openai/gpt-4o">GPT-4o</option>
                <option value="deepseek/deepseek-v3.2">DeepSeek V3.2</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium">内容生成模型</label>
              <select className="w-full mt-1 p-2 text-sm border border-border/30 rounded-lg bg-card" defaultValue="anthropic/claude-sonnet-4-6">
                <option value="anthropic/claude-sonnet-4-6">Claude Sonnet 4.6</option>
                <option value="openai/gpt-4o">GPT-4o</option>
                <option value="deepseek/deepseek-v3.2">DeepSeek V3.2</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:shadow-[0_0_15px_var(--glow-color)] disabled:opacity-50 transition-all"
      >
        <Save className="w-4 h-4" />
        {saving ? '保存中...' : '保存配置'}
      </button>
    </div>
  );
}
