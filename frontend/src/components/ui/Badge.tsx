export function Badge({
  children,
  variant = 'default',
  className = '',
}: {
  children: React.ReactNode;
  variant?: 'default' | 'draft' | 'confirmed' | 'modified' | 'warning' | 'error' | 'success';
  className?: string;
}) {
  const variantClasses: Record<string, string> = {
    default: 'bg-muted text-muted-foreground',
    draft: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
    confirmed: 'bg-green-500/15 text-green-600 dark:text-green-400',
    modified: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400',
    warning: 'bg-orange-500/15 text-orange-600 dark:text-orange-400',
    error: 'bg-red-500/15 text-red-600 dark:text-red-400',
    success: 'bg-green-500/15 text-green-600 dark:text-green-400',
  };

  const labels: Record<string, string> = {
    draft: '草稿',
    confirmed: '已确认',
    modified: '已修改',
    warning: '低置信度',
    error: '错误',
    success: '完成',
  };

  const displayLabel = typeof children === 'string' && labels[children] ? labels[children] : children;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${variantClasses[variant] || variantClasses.default} ${className}`}
    >
      {displayLabel}
    </span>
  );
}
