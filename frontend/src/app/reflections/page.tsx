'use client';

import { useReflections, useReflection, useTriggerReflection } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import type { Reflection } from '@/types/api';

function ReflectionCard({ reflection, onSelect }: { reflection: Reflection; onSelect: () => void }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <h3 className="text-sm font-semibold text-gray-900 mb-1">{reflection.title}</h3>
      <p className="text-xs text-gray-500 line-clamp-3">{reflection.narrative}</p>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>{new Date(reflection.created_at).toLocaleDateString()}</span>
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px]">{reflection.status}</span>
      </div>
    </div>
  );
}

function ReflectionDetail({ reflection, onClose }: { reflection: Reflection; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex bg-black/50">
      <div className="ml-auto w-full max-w-lg bg-white h-full overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{reflection.title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">&times;</button>
        </div>
        <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">{reflection.narrative}</div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Period</div>
            <div className="font-semibold">{new Date(reflection.period_start).toLocaleDateString()} — {new Date(reflection.period_end).toLocaleDateString()}</div>
          </div>
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Status</div>
            <div className="font-semibold">{reflection.status}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReflectionsPage() {
  const [selected, setSelected] = useState<Reflection | null>(null);
  const { data, isLoading, error, refetch } = useReflections();
  const triggerMutation = useTriggerReflection();

  const reflections = data?.data || [];

  return (
    <PageLayout
      title="Reflections"
      description="Longitudinal insights about your cognitive patterns"
      actions={
        <Button onClick={() => triggerMutation.mutate()} disabled={triggerMutation.isPending}>
          {triggerMutation.isPending ? 'Generating...' : 'Generate Reflection'}
        </Button>
      }
    >
      {isLoading && <SkeletonList count={3} />}
      {error && <ErrorState message="Failed to load reflections" onRetry={() => refetch()} />}
      {!isLoading && !error && reflections.length === 0 && (
        <EmptyState
          title="No reflections yet"
          description="Reflections are generated periodically to synthesize your cognitive data."
          action={<Button onClick={() => triggerMutation.mutate()}>Generate First Reflection</Button>}
        />
      )}
      <div className="grid gap-3">
        {reflections.map((r) => (
          <ReflectionCard key={r.id} reflection={r} onSelect={() => setSelected(r)} />
        ))}
      </div>
      {selected && <ReflectionDetail reflection={selected} onClose={() => setSelected(null)} />}
    </PageLayout>
  );
}
