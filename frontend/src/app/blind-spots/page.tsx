'use client';

import { useBlindSpots, useAnalyzeBlindSpots } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import type { BlindSpot } from '@/types/api';

function BlindSpotCard({ spot, onSelect }: { spot: BlindSpot; onSelect: () => void }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center shrink-0">
          <span className="text-red-600 text-sm">!</span>
        </div>
        <div className="flex-1">
          <p className="text-sm text-gray-900">{spot.content}</p>
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
            <span>{spot.source_agent}</span>
            <span>•</span>
            <span>{new Date(spot.created_at).toLocaleDateString()}</span>
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
              spot.status === 'pending' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
            }`}>{spot.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function BlindSpotDetail({ spot, onClose }: { spot: BlindSpot; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex bg-black/50">
      <div className="ml-auto w-full max-w-lg bg-white h-full overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Blind Spot</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">&times;</button>
        </div>
        <p className="text-gray-900 mb-4">{spot.content}</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Source</div>
            <div className="font-semibold">{spot.source_agent}</div>
          </div>
          <div className="rounded-lg bg-gray-50 p-3">
            <div className="text-gray-500">Status</div>
            <div className="font-semibold">{spot.status}</div>
          </div>
        </div>
        {spot.evidence_ids.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Evidence IDs</h3>
            <div className="flex flex-wrap gap-1">
              {spot.evidence_ids.map((eid, i) => (
                <span key={i} className="text-xs bg-gray-100 rounded px-2 py-1">{eid.slice(0, 8)}...</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function BlindSpotsPage() {
  const [selected, setSelected] = useState<BlindSpot | null>(null);
  const { data, isLoading, error, refetch } = useBlindSpots();
  const analyzeMutation = useAnalyzeBlindSpots();

  const spots = data?.data || [];

  return (
    <PageLayout
      title="Blind Spots"
      description="Cognitive blind spots and inconsistencies"
      actions={
        <Button onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending}>
          {analyzeMutation.isPending ? 'Analyzing...' : 'Run Analysis'}
        </Button>
      }
    >
      {isLoading && <SkeletonList count={5} />}
      {error && <ErrorState message="Failed to load blind spots" onRetry={() => refetch()} />}
      {!isLoading && !error && spots.length === 0 && (
        <EmptyState
          title="No blind spots detected"
          description="Ayeneh will identify cognitive blind spots as it analyzes your patterns."
          action={<Button onClick={() => analyzeMutation.mutate()}>Run First Analysis</Button>}
        />
      )}
      <div className="grid gap-3">
        {spots.map((s) => (
          <BlindSpotCard key={s.id} spot={s} onSelect={() => setSelected(s)} />
        ))}
      </div>
      {selected && <BlindSpotDetail spot={selected} onClose={() => setSelected(null)} />}
    </PageLayout>
  );
}
