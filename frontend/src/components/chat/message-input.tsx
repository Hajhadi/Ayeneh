'use client';

import { useCallback, useRef, useState } from 'react';

interface MessageInputProps {
  onSend: (content: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
}

export function MessageInput({ onSend, onCancel, disabled = false, isStreaming = false }: MessageInputProps) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  const send = useCallback(() => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue('');
    if (ref.current) ref.current.style.height = 'auto';
  }, [value, disabled, onSend]);

  return (
    <div className="shrink-0 px-5 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)', background: '#16161e' }}>
      <div className="mx-auto max-w-3xl flex items-end gap-2.5 rounded-2xl p-2.5 input-ring"
           style={{ background: '#1e1e2a', border: '1px solid rgba(255,255,255,0.08)' }}>
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => { setValue(e.target.value); e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'; }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder="Type a message..."
          rows={1}
          disabled={disabled || isStreaming}
          className="flex-1 resize-none bg-transparent outline-none disabled:opacity-40"
          style={{ fontSize: 'var(--text-sm)', color: '#e2e8f0', minHeight: '36px', maxHeight: '140px' }}
        />
        {isStreaming ? (
          <button onClick={onCancel} className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-all"
                  style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }}
                  aria-label="Stop generating">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          </button>
        ) : (
          <button onClick={send} disabled={!value.trim() || disabled}
                  className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-all disabled:opacity-20"
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)', color: '#fff' }}
                  aria-label="Send">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        )}
      </div>
      <p className="text-center mt-2" style={{ fontSize: '10px', color: 'rgba(255,255,255,0.12)' }}>
        Ayeneh reflects your thinking patterns — not advice, not therapy, just a mirror.
      </p>
    </div>
  );
}
