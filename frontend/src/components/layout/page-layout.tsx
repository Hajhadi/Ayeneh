import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageLayoutProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function PageLayout({ title, description, actions, children, className }: PageLayoutProps) {
  return (
    <div className={cn('flex flex-1 flex-col', className)}>
      <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#fff' }}>{title}</h1>
          {description && <p className="mt-1 text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className="flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
