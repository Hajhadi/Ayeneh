'use client';

import { usePatterns, usePatternTimeline } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import type { Pattern } from '@/types/api';

function PatternCard({ pattern, onSelect }: { pattern: Pattern; onSelect: () => void }) {
  const strengthColor = pattern.strength >= 0.7 ? 'bg-green-100 text-green-700' :
                        pattern.strength >= 0.4 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <div className="flex items-start justify-between mb-2">
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${strengthColor}`}>
          Strength: {(pattern.strength * 100).toFixed(0)}%
        </span>
        <span className="text-xs text-gray-400">{pattern.evidence_count} evidence</span>
      </div>
      <p className="text-sm text-gray-900">{pattern.description}</p>
      <div className="mt-2 text-xs text-gray-400">
        Detected: {new Date(pattern.first_detected_at).toLocaleDateString()}
      </div>
    </div>
  );
}

function PatternDetail({ pattern, onClose }: { pattern: Pattern; onClose: () => void }) {
  const { data: timeline, isLoading } = usePatternTimeline(pattern.id);
  return (
    <div className="fixed inset-0 z-50 flex bg-black/50">
      <div className="ml-auto w-full max-w-lg bg-white h-full overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Pattern Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">&times;</button>
        </div>
        <p className="text-gray-900 mb-4">{pattern.description}</p>
        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Strength</div>
            <div className="font-semibold">{(pattern.strength * 100).toFixed(1)}%</div>
          </div>
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Evidence</div>
            <div className="font-semibold">{pattern.evidence_count}</div>
          </div>
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Status</div>
            <div className="font-semibold">{pattern.status}</div>
          </div>
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">First Detected</div>
            <div className="font-semibold">{new Date(pattern.first_detected_at).toLocaleDateString()}</div>
          </div>
        </div>
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Trend</h3>
          <div className="flex items-end gap-1 h-20">
            {[0.3, 0.4, 0.5, 0.6, 0.7].map((v, i) => (
              <div key={i} className="flex-1 bg-blue-200 rounded-t" style={{ height: `${v * 100}%` }} />
            ))}
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>1m ago</span><span>Now</span>
          </div>
        </div>
        {timeline?.data && timeline.data.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Timeline</h3>
            <div className="space-y-2">
              {timeline.data.map((entry: Record<string, unknown>, i: number) => (
                <div key={i} className="text-xs bg-gray-50 rounded p-2">
                  {JSON.stringify(entry).slice(0, 200)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatternsPage() {
  const [selected, setSelected] = useState<Pattern | null>(null);
  const { data, isLoading, error, refetch } = usePatterns();

  const patterns = data?.data || [];

  return (
    <PageLayout
      title="Patterns"
      description="Cognitive and behavioral patterns detected by Ayeneh"
      actions={<Button onClick={() => refetch()} variant="outline" size="sm">Refresh</Button>}
    >
      {isLoading && <SkeletonList count={5} />}
      {error && <ErrorState message="Failed to load patterns" onRetry={() => refetch()} />}
      {!isLoading && !error && patterns.length === 0 && (
        <EmptyState title="No patterns detected" description="Patterns will emerge as Ayeneh analyzes your interactions." />
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {patterns.map((p) => (
          <PatternCard key={p.id} pattern={p} onSelect={() => setSelected(p)} />
        ))}
      </div>
      {selected && <PatternDetail pattern={selected} onClose={() => setSelected(null)} />}
    </PageLayout>
  );
}
