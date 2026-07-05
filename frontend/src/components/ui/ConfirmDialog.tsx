import { useState } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'danger';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '确认',
  cancelLabel = '取消',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md rounded-2xl bg-card border border-border shadow-2xl p-6 mx-4">
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg border border-border/50 text-sm hover:bg-accent/30 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              variant === 'danger'
                ? 'bg-destructive text-white hover:opacity-90'
                : 'bg-primary text-primary-foreground hover:opacity-90'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook for managing confirm dialog state.
 */
export function useConfirmDialog() {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<{
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: 'default' | 'danger';
  }>({ title: '', message: '' });
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const confirm = (opts: {
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: 'default' | 'danger';
  }): Promise<boolean> => {
    setConfig(opts);
    setOpen(true);
    return new Promise((resolve) => {
      setResolveRef(() => resolve);
    });
  };

  const handleConfirm = () => {
    setOpen(false);
    resolveRef?.(true);
  };

  const handleCancel = () => {
    setOpen(false);
    resolveRef?.(false);
  };

  const dialog = (
    <ConfirmDialog
      open={open}
      {...config}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  );

  return { confirm, dialog };
}
