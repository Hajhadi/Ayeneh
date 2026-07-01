'use client';

import { useEffect, useRef, useCallback } from 'react';
import { MarkdownRenderer } from '@/components/common/markdown-renderer';
import type { Message } from '@/types/conversation';

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
}

function UserBubble({ message }: { message: Message }) {
  return (
    <div className="flex justify-end mb-3 msg-in">
      <div className="max-w-[72%] rounded-2xl rounded-br-sm px-4 py-2.5"
           style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)', color: '#fff', fontSize: 'var(--text-sm)', lineHeight: '1.6' }}>
        {message.content}
      </div>
    </div>
  );
}

function AssistantBubble({ message }: { message: Message }) {
  return (
    <div className="flex justify-start mb-3 msg-in">
      <div className="flex gap-2.5 max-w-[78%]">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
             style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            <line x1="9" y1="9" x2="9.01" y2="9"/>
            <line x1="15" y1="9" x2="15.01" y2="9"/>
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded-xl px-4 py-2.5" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', fontSize: 'var(--text-sm)', lineHeight: '1.6' }}>
            <MarkdownRenderer content={message.content} />
          </div>
        </div>
      </div>
    </div>
  );
}

function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-start mb-3 msg-in">
      <div className="flex gap-2.5 max-w-[78%]">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
             style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            <line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded-xl px-4 py-2.5" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', fontSize: 'var(--text-sm)' }}>
            {content || (
              <div className="flex gap-1.5 items-center py-0.5">
                <span className="w-1.5 h-1.5 rounded-full typing-dot" style={{ background: 'var(--accent)' }} />
                <span className="w-1.5 h-1.5 rounded-full typing-dot" style={{ background: 'var(--accent)', animationDelay: '0.2s' }} />
                <span className="w-1.5 h-1.5 rounded-full typing-dot" style={{ background: 'var(--accent)', animationDelay: '0.4s' }} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function WelcomeState() {
  return (
    <div className="flex flex-col items-center justify-center h-full msg-in select-none">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5"
           style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)', boxShadow: '0 8px 32px rgba(124,58,237,0.25)' }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/>
          <line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-white mb-1">Ayeneh</h2>
      <p className="text-xs text-white/35 text-center max-w-xs leading-relaxed">
        Your Cognitive Mirror for self-observation and growth.
        I reflect back your thinking patterns — not advice, not therapy.
      </p>
      <div className="flex gap-1.5 mt-4">
        {['Reflection', 'Growth', 'Knowledge'].map(t => (
          <span key={t} className="px-2.5 py-1 rounded-full text-[10px] font-medium"
                style={{ background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.2)', color: '#a78bfa' }}>
            {t}
          </span>
        ))}
      </div>
      <p className="text-[10px] text-white/15 mt-5">Type below to begin</p>
    </div>
  );
}

export function ChatWindow({ messages, isStreaming, streamingContent }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScroll = useRef(true);

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);

  useEffect(() => {
    if (autoScroll.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  return (
    <div ref={scrollRef} onScroll={onScroll} className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-5 py-6" style={{ minHeight: '100%' }}>
        {messages.length === 0 && !isStreaming && <WelcomeState />}
        {messages.map(m => m.role === 'user'
          ? <UserBubble key={m.id} message={m} />
          : <AssistantBubble key={m.id} message={m} />
        )}
        {isStreaming && <StreamingBubble content={streamingContent} />}
      </div>
    </div>
  );
}
