'use client';

import { useEffect, useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore } from '@/stores/chat-store';
import { useStreamChat } from '@/hooks/use-stream-chat';
import { useConversationMessages } from '@/hooks/use-conversation-messages';
import { ChatWindow } from '@/components/chat/chat-window';
import { MessageInput } from '@/components/chat/message-input';
import { ConversationList } from '@/components/chat/conversation-list';
import { SearchPanel } from '@/components/chat/search-panel';
import { SecureModel, secureModelAvailable } from '@/lib/secure-model';

export default function ChatPage() {
  const router = useRouter();
  const [showSearch, setShowSearch] = useState(false);
  const [modelLabel, setModelLabel] = useState('Cloud model');
  const {
    activeConversationId, messages: storeMessages,
    isStreaming, streamingContent, setMessages, setActiveConversation,
    thinkingSteps, thinkingComplete, thinkingTotalMs,
    chatError,
  } = useChatStore();
  const { sendMessage, cancelStream } = useStreamChat();
  const { data: messagesData } = useConversationMessages(activeConversationId);

  useEffect(() => {
    if (!secureModelAvailable()) { setModelLabel('Backend'); return; }
    SecureModel.listProfiles().then(({ profiles, activeProvider }) => {
      setModelLabel(profiles.find((item) => item.provider === activeProvider)?.model || 'Set up model');
    }).catch(() => setModelLabel('Set up model'));
  }, []);

  useEffect(() => {
    if (messagesData?.data && !isStreaming) {
      setMessages(messagesData.data);
    }
  }, [messagesData, isStreaming, setMessages]);

  const onSelect = useCallback((id: string) => {
    if (isStreaming) cancelStream();
    setActiveConversation(id);
  }, [isStreaming, cancelStream, setActiveConversation]);

  const onNew = useCallback(() => {
    if (isStreaming) cancelStream();
    setActiveConversation(null);
  }, [isStreaming, cancelStream, setActiveConversation]);

  return (
    <div className="chat-shell" style={{
      display: 'flex', height: '100vh',
      background: '#0A0A12', color: '#e2e8f0',
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: '15px',
    }}>
      {/* Sidebar */}
      <aside className="chat-sidebar" style={{
        width: '260px', flexShrink: 0,
        background: '#111118',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Logo */}
        <div
          onClick={() => router.push('/')}
          style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '16px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: 'linear-gradient(135deg, #7c3aed, #6366f1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Ayeneh</div>
            <div style={{ fontSize: '11px', color: '#a78bfa', letterSpacing: '0.08em', opacity: 0.5 }}>COGNITIVE MIRROR</div>
          </div>
        </div>

        {/* Conversations */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <ConversationList activeId={activeConversationId} onSelect={onSelect} onNew={onNew} />
        </div>

        {/* Status */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '8px 10px', borderRadius: '8px',
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
          }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22C55E' }} />
            <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.3)' }}>{modelLabel}</span>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <main className="chat-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>
        {/* Search panel */}
        <SearchPanel open={showSearch} onClose={() => setShowSearch(false)} />
        {/* Header */}
        <header className="chat-header" style={{
          height: '48px', flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(17,17,24,0.9)', backdropFilter: 'blur(8px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" style={{ opacity: 0.6 }}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#a1a1aa' }}>
              {activeConversationId ? 'Active Conversation' : 'New Conversation'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {/* Search icon */}
            <button
              onClick={() => setShowSearch(!showSearch)}
              title="جستجوی کتاب‌ها"
              style={{
                width: '32px', height: '32px', borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: showSearch ? 'rgba(124,58,237,0.15)' : 'transparent',
                border: showSearch ? '1px solid rgba(124,58,237,0.3)' : '1px solid transparent',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { if (!showSearch) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseLeave={(e) => { if (!showSearch) e.currentTarget.style.background = 'transparent'; }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={showSearch ? '#a78bfa' : '#71717A'} strokeWidth="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </button>
            {/* Library icon */}
            <button
              onClick={() => router.push('/library')}
              title="کتابخانه"
              style={{
                width: '32px', height: '32px', borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent',
                border: '1px solid transparent',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#71717A" strokeWidth="2">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
              </svg>
            </button>
            <span style={{
              fontSize: '11px', padding: '3px 8px', borderRadius: '6px',
              background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.15)',
              color: '#a78bfa',
            }}>
              {modelLabel}
            </span>
          </div>
        </header>

        {/* Chat + Pipeline */}
        <ChatWindow
          messages={storeMessages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          thinkingSteps={thinkingSteps}
          thinkingComplete={thinkingComplete}
          thinkingTotalMs={thinkingTotalMs}
        />

        {chatError && (
          <p role="alert" className="mx-5 mb-2 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-2 text-sm text-red-200">
            {chatError}
          </p>
        )}

        {/* Input */}
        <MessageInput onSend={sendMessage} onCancel={cancelStream} isStreaming={isStreaming} />
      </main>
    </div>
  );
}
