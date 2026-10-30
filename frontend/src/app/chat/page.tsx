'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore } from '@/stores/chat-store';
import { useStreamChat } from '@/hooks/use-stream-chat';
import { useConversationMessages } from '@/hooks/use-conversation-messages';
import { ChatWindow } from '@/components/chat/chat-window';
import { MessageInput } from '@/components/chat/message-input';
import { ConversationList } from '@/components/chat/conversation-list';
import { SearchPanel } from '@/components/chat/search-panel';
import { SecureModel, secureModelAvailable, type ModelProfile } from '@/lib/secure-model';

export default function ChatPage() {
  const router = useRouter();
  const [showSearch, setShowSearch] = useState(false);
  const [showConversationDrawer, setShowConversationDrawer] = useState(false);
  const [modelLabel, setModelLabel] = useState('Cloud model');
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [activeProvider, setActiveProvider] = useState('');
  const initialPromptHandled = useRef(false);
  const {
    activeConversationId, messages: storeMessages,
    isStreaming, streamingContent, setMessages, setActiveConversation,
    thinkingSteps, thinkingComplete, thinkingTotalMs,
    chatError, setChatError,
  } = useChatStore();
  const { sendMessage, cancelStream } = useStreamChat();
  const { data: messagesData } = useConversationMessages(activeConversationId);

  useEffect(() => {
    if (initialPromptHandled.current) return;
    initialPromptHandled.current = true;
    const prompt = sessionStorage.getItem('ayeneh_initial_prompt');
    if (!prompt) return;
    sessionStorage.removeItem('ayeneh_initial_prompt');
    void sendMessage(prompt);
  }, [sendMessage]);

  useEffect(() => {
    if (!secureModelAvailable()) { setModelLabel('Backend'); return; }
    SecureModel.listProfiles().then(({ profiles: saved, activeProvider: active }) => {
      setProfiles(saved);
      setActiveProvider(active);
      setModelLabel(saved.find((item) => item.provider === active)?.label || 'Set up model');
    }).catch(() => setModelLabel('Set up model'));
  }, []);

  async function changeModel(provider: string) {
    if (!provider || isStreaming) return;
    try {
      await SecureModel.setActiveProvider({ provider });
      setActiveProvider(provider);
      setModelLabel(profiles.find((item) => item.provider === provider)?.label || 'Cloud model');
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'Could not switch model');
    }
  }

  useEffect(() => {
    if (messagesData?.data && !isStreaming) {
      setMessages(messagesData.data);
    }
  }, [messagesData, isStreaming, setMessages]);

  const onSelect = useCallback((id: string) => {
    if (isStreaming) cancelStream();
    setActiveConversation(id);
    setShowConversationDrawer(false);
  }, [isStreaming, cancelStream, setActiveConversation]);

  const onNew = useCallback(() => {
    if (isStreaming) cancelStream();
    setActiveConversation(null);
    setShowConversationDrawer(false);
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

      {showConversationDrawer && <div className="mobile-conversation-drawer" onClick={() => setShowConversationDrawer(false)}>
        <aside className="mobile-conversation-panel" onClick={(event) => event.stopPropagation()}>
          <div className="mobile-conversation-title">
            <span>Chat history</span>
            <button type="button" className="mobile-conversation-close" onClick={() => setShowConversationDrawer(false)} aria-label="Close chat history">×</button>
          </div>
          <div className="flex-1">
            <ConversationList activeId={activeConversationId} onSelect={onSelect} onNew={onNew} />
          </div>
        </aside>
      </div>}

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
            <button onClick={() => { if (window.history.length > 1) router.back(); else router.push('/'); }} aria-label="Go back" style={{ display: 'grid', placeItems: 'center', width: '28px', height: '28px', borderRadius: '7px', color: '#a78bfa', background: 'rgba(124,58,237,.08)' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2"><path d="m15 18-6-6 6-6"/></svg>
            </button>
            <button className="mobile-history-button" onClick={() => setShowConversationDrawer(true)} aria-label="Open chat history" style={{ display: 'none', placeItems: 'center', width: '30px', height: '30px', borderRadius: '8px', color: '#c4b5fd', background: 'rgba(124,58,237,.12)', border: '1px solid rgba(167,139,250,.2)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 5h16M4 12h16M4 19h10" /></svg>
            </button>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" style={{ opacity: 0.6 }}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#a1a1aa' }}>
              {activeConversationId ? 'Active Conversation' : 'New Conversation'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={() => router.push('/settings')}
              aria-label="Model and app settings"
              style={{ width: '32px', height: '32px', display: 'grid', placeItems: 'center', border: '1px solid rgba(167,139,250,.25)', borderRadius: '8px', color: '#a78bfa', background: 'rgba(124,58,237,.1)' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>
            </button>
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
            {secureModelAvailable() ? <select
              aria-label="Active model"
              value={activeProvider}
              onChange={(event) => { void changeModel(event.target.value); }}
              disabled={isStreaming || profiles.length === 0}
              style={{ maxWidth: '112px', fontSize: '11px', padding: '3px 4px', borderRadius: '6px',
                background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.15)', color: '#a78bfa' }}
            >
              {!activeProvider && <option value="">Set up model</option>}
              {profiles.map((profile) => <option key={profile.provider} value={profile.provider}>{profile.label}</option>)}
            </select> : <span style={{ fontSize: '11px', color: '#a78bfa' }}>Backend</span>}
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
