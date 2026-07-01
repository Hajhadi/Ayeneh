'use client';

import { useState } from 'react';
import { useMemories, useSearchMemories, useDeleteMemory, useArchiveMemory, useMemoryEvolution } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { ConfirmDialog } from '@/components/common/confirm-dialog';
import { SearchBar } from '@/components/common/search-bar';
import { Button } from '@/components/ui/button';
import type { Memory } from '@/types/api';

function MemoryCard({ memory, onSelect, onDelete, onArchive }: {
  memory: Memory;
  onSelect: () => void;
  onDelete: () => void;
  onArchive: () => void;
}) {
  const confColor = memory.confidence >= 0.8 ? 'text-green-600' :
                    memory.confidence >= 0.5 ? 'text-yellow-600' : 'text-red-600';
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 cursor-pointer" onClick={onSelect}>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {memory.type}
            </span>
            {memory.evolution_version && memory.evolution_version > 1 && (
              <span className="inline-flex items-center rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                v{memory.evolution_version}
              </span>
            )}
            {memory.status === 'superseded' && (
              <span className="text-xs text-gray-400">superseded</span>
            )}
          </div>
          <p className="text-sm text-gray-900 line-clamp-2">{memory.content}</p>
        </div>
        <div className="flex flex-col items-end gap-1 ml-3 shrink-0">
          <span className={`text-xs font-mono ${confColor}`}>
            {(memory.confidence * 100).toFixed(0)}%
          </span>
          {memory.confidence_history && Object.keys(memory.confidence_history).length > 1 && (
            <span className="text-[10px] text-gray-400">evolved</span>
          )}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>{new Date(memory.created_at).toLocaleDateString()}</span>
        <div className="flex gap-1">
          <button onClick={onArchive} className="hover:text-yellow-600 px-1">Archive</button>
          <button onClick={onDelete} className="hover:text-red-600 px-1">Delete</button>
        </div>
      </div>
    </div>
  );
}

function MemoryDetail({ memory, onClose }: { memory: Memory; onClose: () => void }) {
  const { data: history, isLoading } = useMemoryEvolution(memory.id);
  return (
    <div className="fixed inset-0 z-50 flex bg-black/50">
      <div className="ml-auto w-full max-w-lg bg-white h-full overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Memory Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">&times;</button>
        </div>
        <div className="space-y-4">
          <div>
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 mb-2">
              {memory.type}
            </span>
            <p className="text-gray-900">{memory.content}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="text-gray-500">Confidence</div>
              <div className="font-semibold">{(memory.confidence * 100).toFixed(1)}%</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="text-gray-500">Status</div>
              <div className="font-semibold">{memory.status}</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="text-gray-500">Version</div>
              <div className="font-semibold">v{memory.evolution_version || 1}</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="text-gray-500">Updated</div>
              <div className="font-semibold">{new Date(memory.updated_at).toLocaleDateString()}</div>
            </div>
          </div>
          {memory.confidence_history && Object.keys(memory.confidence_history).length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Confidence History</h3>
              <div className="flex gap-1 flex-wrap">
                {Object.entries(memory.confidence_history).map(([v, c]) => (
                  <span key={v} className="text-xs bg-gray-100 rounded px-2 py-1">
                    {v}: {(c as number * 100).toFixed(0)}%
                  </span>
                ))}
              </div>
            </div>
          )}
          {history && history.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Evolution History</h3>
              <div className="space-y-2">
                {history.map((e, i) => (
                  <div key={i} className="text-xs bg-gray-50 rounded p-2">
                    <span className="font-medium">{e.event_type}</span>
                    {e.old_confidence !== undefined && e.new_confidence !== undefined && (
                      <span className="ml-2 text-gray-500">
                        confidence: {((e.old_confidence || 0) * 100).toFixed(0)}% → {((e.new_confidence || 0) * 100).toFixed(0)}%
                      </span>
                    )}
                    {e.detail && <span className="ml-2 text-gray-400">{e.detail}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MemoriesPage() {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Memory | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Memory | null>(null);

  const { data, isLoading, error, refetch } = useMemories();
  const { data: searchData, isLoading: searchLoading } = useSearchMemories(search);
  const deleteMutation = useDeleteMemory();
  const archiveMutation = useArchiveMemory();

  const memories = search.length > 0 ? (searchData?.data || []) : (data?.data || []);

  return (
    <PageLayout
      title="Memories"
      description="Your cognitive memories and insights"
      actions={<Button onClick={() => refetch()} variant="outline" size="sm">Refresh</Button>}
    >
      <div className="mb-4">
        <SearchBar placeholder="Search memories..." onSearch={setSearch} />
      </div>

      {(isLoading || searchLoading) && <SkeletonList count={5} />}

      {error && <ErrorState message="Failed to load memories" onRetry={() => refetch()} />}

      {!isLoading && !error && memories.length === 0 && (
        <EmptyState title="No memories yet" description="Memories will appear here as you interact with Ayeneh." />
      )}

      <div className="grid gap-3">
        {memories.map((m) => (
          <MemoryCard
            key={m.id}
            memory={m}
            onSelect={() => setSelected(m)}
            onDelete={() => setDeleteTarget(m)}
            onArchive={() => archiveMutation.mutate(m.id)}
          />
        ))}
      </div>

      {selected && <MemoryDetail memory={selected} onClose={() => setSelected(null)} />}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Memory"
        message={`Are you sure you want to delete this memory? This cannot be undone.`}
        danger
        confirmLabel="Delete"
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
          setDeleteTarget(null);
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
