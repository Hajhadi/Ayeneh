'use client';

import { useState } from 'react';
import { useBooks, useUploadBook, useDeleteBook, useReindexBook, useBookProgress } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { ConfirmDialog } from '@/components/common/confirm-dialog';
import { Button } from '@/components/ui/button';
import type { Book } from '@/types/api';

function UploadForm({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [content, setContent] = useState('');
  const uploadMutation = useUploadBook();

  const handleSubmit = () => {
    if (!title.trim() || !content.trim()) return;
    uploadMutation.mutate(
      { title, author, content, filename: `${title}.txt` },
      { onSuccess: onClose },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="rounded-lg shadow-xl max-w-lg w-full mx-4 p-6" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: '#fff' }}>Upload Document</h3>
        <div className="space-y-3">
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md px-3 py-2 text-sm" style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }} />
          <input placeholder="Author (optional)" value={author} onChange={(e) => setAuthor(e.target.value)}
            className="w-full rounded-md px-3 py-2 text-sm" style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }} />
          <textarea placeholder="Document content" value={content} onChange={(e) => setContent(e.target.value)}
            className="w-full rounded-md px-3 py-2 text-sm h-40 resize-none" style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }} />
        </div>
        <div className="mt-4 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function BookCard({ book, onDelete, onReindex }: {
  book: Book; onDelete: () => void; onReindex: () => void;
}) {
  const statusColor = book.status === 'ready' ? 'rgba(34,197,94,0.1)' :
                      book.status === 'processing' ? 'rgba(234,179,8,0.1)' :
                      book.status === 'failed' ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.05)';
  const statusTextColor = book.status === 'ready' ? '#4ade80' :
                          book.status === 'processing' ? '#facc15' :
                          book.status === 'failed' ? '#f87171' : 'rgba(255,255,255,0.4)';
  return (
    <div className="rounded-lg p-4" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: '#fff' }}>{book.title}</h3>
          {book.author && <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{book.author}</p>}
        </div>
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: statusColor, color: statusTextColor }}>
          {book.status}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-4 text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
        <span>{book.source_format.toUpperCase()}</span>
        <span>{book.chunk_count} chunks</span>
        <span>{new Date(book.created_at).toLocaleDateString()}</span>
      </div>
      <div className="mt-2 flex gap-2">
        <button onClick={onReindex} className="text-xs text-purple-400 hover:text-purple-300">Reindex</button>
        <button onClick={onDelete} className="text-xs text-red-400 hover:text-red-300">Delete</button>
      </div>
    </div>
  );
}

export default function LibraryPage() {
  const [showUpload, setShowUpload] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Book | null>(null);
  const { data, isLoading, error, refetch } = useBooks();
  const deleteMutation = useDeleteBook();
  const reindexMutation = useReindexBook();

  const books = data?.data || [];

  return (
    <PageLayout
      title="Library"
      description="Your knowledge base and documents"
      actions={<Button onClick={() => setShowUpload(true)}>Upload Document</Button>}
    >
      {isLoading && <SkeletonList count={3} />}
      {error && <ErrorState message="Failed to load books" onRetry={() => refetch()} />}
      {!isLoading && !error && books.length === 0 && (
        <EmptyState
          title="No documents yet"
          description="Upload books and documents to build your knowledge base."
          action={<Button onClick={() => setShowUpload(true)}>Upload First Document</Button>}
        />
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {books.map((b) => (
          <BookCard
            key={b.id}
            book={b}
            onDelete={() => setDeleteTarget(b)}
            onReindex={() => reindexMutation.mutate(b.id)}
          />
        ))}
      </div>

      {showUpload && <UploadForm onClose={() => setShowUpload(false)} />}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Book"
        message={`Delete "${deleteTarget?.title}" and all its indexed data?`}
        danger confirmLabel="Delete"
        onConfirm={() => { if (deleteTarget) deleteMutation.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
