'use client';

import { useState, useCallback } from 'react';

interface SearchResult {
  chunk_id: string;
  book_title: string;
  content: string;
  score: number;
  chapter_title?: string;
}

export function SearchPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/library/search?q=${encodeURIComponent(query)}&limit=10`);
      const data = await res.json();
      setResults(data.results || data.data || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
    if (e.key === 'Escape') onClose();
  };

  if (!open) return null;

  return (
    <div style={{
      position: 'absolute', top: '48px', right: 0, left: 0, zIndex: 50,
      background: '#111118', borderBottom: '1px solid rgba(255,255,255,0.06)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      {/* Search input */}
      <div style={{ padding: '12px 20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#71717A" strokeWidth="2"
            style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
          >
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="جستجو در کتاب‌ها و محتوا..."
            style={{
              width: '100%', padding: '8px 12px 8px 32px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '8px', color: '#fff', fontSize: '13px',
              outline: 'none',
            }}
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          style={{
            padding: '8px 16px', borderRadius: '8px',
            background: 'rgba(124,58,237,0.15)',
            border: '1px solid rgba(124,58,237,0.3)',
            color: '#a78bfa', fontSize: '12px', fontWeight: 500,
            cursor: loading ? 'wait' : 'pointer',
            opacity: (!query.trim() || loading) ? 0.5 : 1,
          }}
        >
          {loading ? 'جستجو...' : 'جستجو'}
        </button>
      </div>

      {/* Results */}
      <div style={{ maxHeight: '400px', overflowY: 'auto', padding: '0 20px 12px' }}>
        {searched && !loading && results.length === 0 && (
          <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.3)', textAlign: 'center', padding: '16px 0' }}>
            نتیجه‌ای یافت نشد
          </p>
        )}
        {results.map((r, i) => (
          <div
            key={r.chunk_id || i}
            className="rounded-lg p-3 mb-2 transition-colors"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.04)',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
          >
            <div className="flex items-center gap-2 mb-1">
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#a78bfa' }}>{r.book_title}</span>
              {r.chapter_title && (
                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>• {r.chapter_title}</span>
              )}
              <span style={{
                marginLeft: 'auto', fontSize: '10px', padding: '1px 6px',
                borderRadius: '4px', fontVariantNumeric: 'tabular-nums',
                background: r.score >= 0.7 ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.04)',
                color: r.score >= 0.7 ? '#4ade80' : 'rgba(255,255,255,0.3)',
              }}>
                {Math.round(r.score * 100)}%
              </span>
            </div>
            <p style={{
              fontSize: '12px', color: 'rgba(255,255,255,0.5)', lineHeight: '1.5',
              display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {r.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
