'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useBooks, useUploadBook, useDeleteBook, useReindexBook, useBookProgress, useAddBookText } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { SkeletonList } from '@/components/common/skeleton';
import { ErrorState } from '@/components/common/error-state';
import { EmptyState } from '@/components/common/empty-state';
import { ConfirmDialog } from '@/components/common/confirm-dialog';
import { Button } from '@/components/ui/button';
import { BookProfilePanel } from '@/components/library/book-profile-panel';
import type { Book } from '@/types/api';

function UploadForm({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [content, setContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [mode, setMode] = useState<'file' | 'text'>('file');
  const [uploading, setUploading] = useState(false);
  const addText = useAddBookText();
  const uploadBook = useUploadBook();

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    if (!title) setTitle(file.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' '));

    if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setContent(ev.target?.result as string);
        setMode('text');
      };
      reader.readAsText(file);
    } else {
      setContent(`[فایل ${file.name} — برای PDF/DOC ابتدا متن را کپی کنید]`);
      setMode('text');
    }
  };

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setUploading(true);
    try {
      if (content.trim() && !content.startsWith('[فایل')) {
        // Create book first, then add text
        const result = await uploadBook.mutateAsync({
          title, author, content: 'placeholder', filename: `${title}.txt`,
        });
        await addText.mutateAsync({ bookId: result.id, content });
        onClose();
      } else {
        await uploadBook.mutateAsync({
          title, author, content: content || 'Empty document', filename: `${title}.txt`,
        });
        onClose();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="rounded-lg shadow-xl max-w-lg w-full mx-4 p-6" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>افزودن کتاب</h3>

        {/* File upload area */}
        <div
          style={{
            border: '2px dashed rgba(255,255,255,0.1)', borderRadius: '8px',
            padding: '24px', textAlign: 'center', cursor: 'pointer',
            background: fileName ? 'rgba(124,58,237,0.05)' : 'transparent',
            borderColor: fileName ? 'rgba(124,58,237,0.3)' : 'rgba(255,255,255,0.1)',
            transition: 'all 0.15s',
          }}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input" type="file" accept=".txt,.md,.pdf,.doc,.docx"
            onChange={handleFile} style={{ display: 'none' }}
          />
          {fileName ? (
            <div>
              <p style={{ color: '#a78bfa', fontSize: '13px', fontWeight: 500 }}>{fileName}</p>
              <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: '11px', marginTop: '4px' }}>
                {content.length > 0 && `${content.split(/\s+/).length} کلمه`}
              </p>
            </div>
          ) : (
            <div>
              <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
                فایل را اینجا رها کنید یا کلیک کنید
              </p>
              <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: '11px', marginTop: '4px' }}>
                TXT, MD — یا PDF/DOC را کپی کنید
              </p>
            </div>
          )}
        </div>

        <div className="space-y-3 mt-4">
          <input placeholder="عنوان کتاب" value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md px-3 py-2 text-sm" style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }} />
          <input placeholder="نویسنده (اختیاری)" value={author} onChange={(e) => setAuthor(e.target.value)}
            className="w-full rounded-md px-3 py-2 text-sm" style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }} />
        </div>

        <div className="mt-4 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>لغو</Button>
          <Button onClick={handleSubmit} disabled={uploading || !title.trim()}>
            {uploading ? 'در حال آپلود...' : 'ذخیره و ساخت پروفایل'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ManualTextForm({ book, onClose }: { book: Book; onClose: () => void }) {
  const [content, setContent] = useState('');
  const addText = useAddBookText();

  const handleSubmit = () => {
    if (!content.trim()) return;
    addText.mutate(
      { bookId: book.id, content },
      { onSuccess: onClose },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
          افزودن متن به «{book.title}»
        </h3>
        <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginBottom: '16px' }}>
          متن کتاب را اینجا الصاق کنید. پس از ذخیره، chunks و پروفایل شناختی به صورت خودکار ساخته می‌شود.
        </p>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="متن کتاب را اینجا الصاق کنید..."
          style={{
            width: '100%', height: '300px', padding: '12px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '8px', color: '#fff', fontSize: '13px',
            resize: 'vertical', outline: 'none', fontFamily: 'inherit',
            lineHeight: '1.6',
          }}
        />
        <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255,255,255,0.3)' }}>
          {content.length > 0 && `${content.split(/\s+/).length} کلمه`}
        </div>
        <div className="mt-4 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>لغو</Button>
          <Button onClick={handleSubmit} disabled={addText.isPending || !content.trim()}>
            {addText.isPending ? 'در حال ذخیره...' : 'ذخیره و ساخت پروفایل'}
          </Button>
        </div>
        {addText.isSuccess && addText.data && (
          <div style={{ marginTop: '12px', padding: '8px 12px', borderRadius: '6px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.15)', fontSize: '12px', color: '#4ade80' }}>
            ✓ {addText.data.chunks_created} chunk ایجاد شد — پروفایل {addText.data.profile?.is_valid ? 'معتبر' : 'نامعتبر'}
          </div>
        )}
      </div>
    </div>
  );
}

function BookCard({ book, onDelete, onReindex, onSelect, isSelected, onAddText }: {
  book: Book; onDelete: () => void; onReindex: () => void; onSelect: () => void; isSelected: boolean; onAddText: () => void;
}) {
  const statusColor = book.status === 'ready' ? 'rgba(34,197,94,0.1)' :
                      book.status === 'processing' ? 'rgba(234,179,8,0.1)' :
                      book.status === 'failed' ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.05)';
  const statusTextColor = book.status === 'ready' ? '#4ade80' :
                          book.status === 'processing' ? '#facc15' :
                          book.status === 'failed' ? '#f87171' : 'rgba(255,255,255,0.4)';
  const isEmpty = book.chunk_count === 0;
  return (
    <div
      className="rounded-lg p-4 cursor-pointer transition-all"
      onClick={onSelect}
      style={{
        border: isSelected ? '1px solid rgba(124,58,237,0.4)' : '1px solid rgba(255,255,255,0.06)',
        background: isSelected ? 'rgba(124,58,237,0.06)' : '#1A1A2E',
      }}
    >
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
      <div className="mt-2 flex gap-2" onClick={(e) => e.stopPropagation()}>
        {isEmpty && (
          <button onClick={onAddText} className="text-xs text-amber-400 hover:text-amber-300" style={{ fontWeight: 500 }}>
            + افزودن متن
          </button>
        )}
        <button onClick={onReindex} className="text-xs text-purple-400 hover:text-purple-300">Reindex</button>
        <button onClick={onDelete} className="text-xs text-red-400 hover:text-red-300">Delete</button>
      </div>
    </div>
  );
}

export default function LibraryPage() {
  const router = useRouter();
  const [showUpload, setShowUpload] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Book | null>(null);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [textTarget, setTextTarget] = useState<Book | null>(null);
  const { data, isLoading, error, refetch } = useBooks();
  const deleteMutation = useDeleteBook();
  const reindexMutation = useReindexBook();

  const books = data?.data || [];

  return (
    <PageLayout
      title="Library"
      description="Your knowledge base and documents"
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/chat')}>← چت</Button>
          <Button onClick={() => setShowUpload(true)}>Upload Document</Button>
        </div>
      }
    >
      <div className="flex gap-4" style={{ minHeight: 'calc(100vh - 160px)' }}>
        {/* Book list */}
        <div className={`${selectedBook ? 'w-1/2' : 'w-full'} transition-all`}>
          {isLoading && <SkeletonList count={3} />}
          {error && <ErrorState message="Failed to load books" onRetry={() => refetch()} />}
          {!isLoading && !error && books.length === 0 && (
            <EmptyState
              title="No documents yet"
              description="Upload books and documents to build your knowledge base."
              action={<Button onClick={() => setShowUpload(true)}>Upload First Document</Button>}
            />
          )}
          <div className={`grid gap-3 ${selectedBook ? 'grid-cols-1' : 'sm:grid-cols-2'}`}>
            {books.map((b) => (
              <BookCard
                key={b.id}
                book={b}
                isSelected={selectedBook?.id === b.id}
                onSelect={() => setSelectedBook(selectedBook?.id === b.id ? null : b)}
                onDelete={() => setDeleteTarget(b)}
                onReindex={() => reindexMutation.mutate(b.id)}
                onAddText={() => setTextTarget(b)}
              />
            ))}
          </div>
        </div>

        {/* Profile panel */}
        {selectedBook && (
          <div className="w-1/2 sticky top-4" style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
            <BookProfilePanel bookId={selectedBook.id} bookTitle={selectedBook.title} />
          </div>
        )}
      </div>

      {showUpload && <UploadForm onClose={() => setShowUpload(false)} />}
      {textTarget && <ManualTextForm book={textTarget} onClose={() => setTextTarget(null)} />}

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
