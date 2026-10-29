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
      <div className="page-heading">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
          {description && <p className="mt-1 text-sm text-white/40">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className="flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
