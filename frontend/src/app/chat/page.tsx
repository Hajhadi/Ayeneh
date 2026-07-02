'use client';

import { useEffect, useCallback } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useStreamChat } from '@/hooks/use-stream-chat';
import { useConversationMessages } from '@/hooks/use-conversation-messages';
import { ChatWindow } from '@/components/chat/chat-window';
import { MessageInput } from '@/components/chat/message-input';
import { ConversationList } from '@/components/chat/conversation-list';

export default function ChatPage() {
  const {
    activeConversationId, messages: storeMessages,
    isStreaming, streamingContent, setMessages, setActiveConversation,
  } = useChatStore();
  const { sendMessage, cancelStream } = useStreamChat();
  const { data: messagesData } = useConversationMessages(activeConversationId);

  useEffect(() => {
    if (messagesData?.data && messagesData.data.length > 0) {
      setMessages(messagesData.data);
    }
  }, [messagesData, setMessages]);

  const onSelect = useCallback((id: string) => {
    if (isStreaming) cancelStream();
    setActiveConversation(id);
  }, [isStreaming, cancelStream, setActiveConversation]);

  const onNew = useCallback(() => {
    if (isStreaming) cancelStream();
    setActiveConversation(null);
  }, [isStreaming, cancelStream, setActiveConversation]);

  return (
    <div className="flex h-screen" style={{ background: '#0f0f14' }}>
      <aside className="w-64 shrink-0 flex flex-col" style={{ background: '#16161e', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2.5 px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: '#fff' }}>Ayeneh</h1>
            <p style={{ fontSize: 'var(--text-xs)', color: 'rgba(167,139,250,0.4)', letterSpacing: '0.05em' }}>COGNITIVE MIRROR</p>
          </div>
        </div>
        <ConversationList activeId={activeConversationId} onSelect={onSelect} onNew={onNew} />
        <div className="px-4 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="flex items-center gap-2 px-2 py-2 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span style={{ fontSize: 'var(--text-xs)', color: 'rgba(255,255,255,0.35)' }}>Connected</span>
          </div>
        </div>
      </aside>

      <main className="flex flex-1 flex-col min-w-0" style={{ background: '#0f0f14' }}>
        <header className="flex items-center justify-between px-5 shrink-0" style={{ height: '52px', borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)', backdropFilter: 'blur(12px)' }}>
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.2)' }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: '#e2e8f0' }}>
              {activeConversationId ? 'Active Conversation' : 'New Conversation'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md" style={{ fontSize: 'var(--text-xs)', background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.2)', color: '#a78bfa' }}>GPT-4o</span>
          </div>
        </header>

        <ChatWindow messages={storeMessages} isStreaming={isStreaming} streamingContent={streamingContent} />

        <MessageInput onSend={sendMessage} onCancel={cancelStream} isStreaming={isStreaming} />
      </main>
    </div>
  );
}
