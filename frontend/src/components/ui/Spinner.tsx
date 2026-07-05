export function Spinner({ size = 'md', className = '' }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const sizeClass = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6';
  return (
    <div
      className={`${sizeClass} border-2 border-primary border-t-transparent rounded-full animate-spin ${className}`}
      role="status"
      aria-label="加载中"
    />
  );
}
