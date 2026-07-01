'use client';

import { useConversations } from '@/hooks/use-conversations';
import type { Conversation } from '@/types/conversation';

interface ConversationListProps {
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function ConvItem({ conv, active, onClick }: { conv: Conversation; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="w-full text-left rounded-xl px-3 py-2.5 mb-1 transition-all"
      style={active
        ? { background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.2)' }
        : { border: '1px solid transparent', color: 'rgba(255,255,255,0.4)' }
      }>
      <p className="truncate font-medium" style={{ fontSize: '13px', color: active ? '#fff' : 'rgba(255,255,255,0.4)' }}>
        {conv.title || 'New chat'}
      </p>
      <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.2)', marginTop: '2px' }}>
        {conv.message_count} messages
      </p>
    </button>
  );
}

import { cn } from '@/lib/utils';

export function ConversationList({ activeId, onSelect, onNew }: ConversationListProps) {
  const { data, isLoading } = useConversations();

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between px-4 py-3">
        <span style={{ fontSize: '11px', fontWeight: 600, letterSpacing: '0.08em', color: 'rgba(255,255,255,0.25)' }}>CONVERSATIONS</span>
        <button onClick={onNew} className="w-6 h-6 rounded-lg flex items-center justify-center transition-all"
                style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.3)' }}
                aria-label="New conversation">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {isLoading && <div className="px-3 py-4 text-center" style={{ fontSize: '11px', color: 'rgba(255,255,255,0.2)' }}>Loading...</div>}
        {data?.data.map((c) => <ConvItem key={c.id} conv={c} active={c.id === activeId} onClick={() => onSelect(c.id)} />)}
        {data?.data.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
                style={{ color: 'rgba(255,255,255,0.2)' }}>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                <line x1="9" y1="10" x2="15" y2="10" opacity="0.5"/>
              </svg>
            </div>
            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.3)', marginBottom: '8px' }}>
              No conversations yet
            </p>
            <button onClick={onNew}
              className="transition-all duration-200"
              style={{ fontSize: '12px', color: '#A78BFA', background: 'none', border: 'none', cursor: 'pointer' }}>
              Start your first reflection →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
