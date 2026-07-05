import { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, Loader2 } from 'lucide-react';
import { useReportWorkflowStore } from '../../stores/reportWorkflowStore';
import { reportApi } from '../../api/reportClient';
import { cn } from '../../lib/utils';

export function ChatPanel() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    report,
    activeSectionKey,
    chatMessages,
    addChatMessage,
    updateSection,
  } = useReportWorkflowStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const activeSection = report?.sections.find((s) => s.key === activeSectionKey);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !report) return;

    addChatMessage('user', text);
    setInput('');
    setLoading(true);

    try {
      const targetContext = activeSection
        ? `当前正在编辑章节: ${activeSection.title} (key: ${activeSection.key})`
        : '';

      const result = await reportApi.chatCommand(
        report.report_id,
        text,
        targetContext
      );

      // Process operations
      const ops = result.operations || [];
      let responseText = '';

      for (const op of ops) {
        const action = op.action as string;
        const opResult = op.result as Record<string, unknown> | undefined;

        if (action === 'add_section' && opResult?.added) {
          responseText += `已添加新章节: ${opResult.title || opResult.added}\n`;
        } else if (action === 'rewrite' && opResult?.rewritten) {
          // Find and update the section in the local store
          // The backend updates the stored report; we need to re-fetch
          responseText += `已重写章节: ${opResult.rewritten}\n`;
          // Re-fetch the full report to get updated content
          try {
            const updated = await reportApi.getReport(report.report_id);
            for (const sec of updated.sections) {
              updateSection(sec.key, sec.content);
            }
          } catch {
            // Local update still shows response
          }
        } else if (opResult?.error) {
          responseText += `操作失败: ${opResult.error}\n`;
        } else {
          responseText += `已处理: ${action}\n`;
        }
      }

      if (!responseText) {
        responseText = '命令已处理。';
      }

      addChatMessage('assistant', responseText.trim());
    } catch (e) {
      addChatMessage(
        'assistant',
        `处理失败: ${e instanceof Error ? e.message : '未知错误'}`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-semibold">AI 助手</span>
      </div>

      {/* Active section context */}
      {activeSection && (
        <div className="mx-3 mt-3 p-2 rounded-lg bg-primary/5 border border-primary/10 text-xs">
          <span className="text-muted-foreground">当前上下文：</span>
          <span className="font-medium">{activeSection.title}</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatMessages.length === 0 && (
          <div className="text-center mt-8 space-y-2">
            <MessageSquare className="w-8 h-8 mx-auto text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              输入自然语言命令来编辑报告
            </p>
            <div className="text-xs text-muted-foreground/60 space-y-1">
              <p>例如："重写背景介绍章节"</p>
              <p>"添加一个风险评估章节"</p>
            </div>
          </div>
        )}

        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[90%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap',
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted/50 border border-border/30'
              )}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-xl px-3 py-2 bg-muted/50 border border-border/30 flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              <span className="text-xs text-muted-foreground">处理中...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border/30">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入命令编辑报告..."
            disabled={loading || !report}
            className="flex-1 rounded-lg border border-border/30 bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50 transition-all placeholder:text-muted-foreground/50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || !report}
            className="rounded-lg bg-primary px-3 py-2 text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
