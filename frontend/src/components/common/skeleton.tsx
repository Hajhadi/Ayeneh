'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div className={cn('animate-pulse rounded-md', className)} style={{ background: 'rgba(255,255,255,0.05)' }} />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg p-6 space-y-4" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

export function SkeletonList({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
