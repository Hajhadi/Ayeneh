import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  icon?: ReactNode;
  className?: string;
}

export function ErrorState({ title = 'Error', message, onRetry, icon, className }: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {icon && <div className="mb-4 text-red-400">{icon}</div>}
      <h3 className="text-lg font-medium" style={{ color: '#fff' }}>{title}</h3>
      <p className="mt-1 max-w-md text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-4">
          Try again
        </Button>
      )}
    </div>
  );
}
