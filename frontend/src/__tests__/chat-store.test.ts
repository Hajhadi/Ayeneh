import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '@/stores/chat-store';
import type { Message } from '@/types/conversation';

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 'msg-1',
    conversation_id: 'conv-1',
    role: 'user',
    content: 'Hello',
    sequence_number: 1,
    token_count: null,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('chat store', () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });

  it('starts with empty state', () => {
    const state = useChatStore.getState();
    expect(state.activeConversationId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.isStreaming).toBe(false);
    expect(state.streamingContent).toBe('');
  });

  it('sets active conversation', () => {
    useChatStore.getState().setActiveConversation('conv-123');
    expect(useChatStore.getState().activeConversationId).toBe('conv-123');
  });

  it('clears messages when switching conversations', () => {
    useChatStore.getState().setMessages([makeMessage()]);
    useChatStore.getState().setActiveConversation('conv-2');
    expect(useChatStore.getState().messages).toEqual([]);
  });

  it('sets messages', () => {
    const msgs = [makeMessage({ id: '1' }), makeMessage({ id: '2' })];
    useChatStore.getState().setMessages(msgs);
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('appends message', () => {
    useChatStore.getState().appendMessage(makeMessage({ id: '1' }));
    useChatStore.getState().appendMessage(makeMessage({ id: '2' }));
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('updates streaming content incrementally', () => {
    useChatStore.getState().updateStreamingContent('Hello');
    expect(useChatStore.getState().streamingContent).toBe('Hello');
    useChatStore.getState().updateStreamingContent(' world');
    expect(useChatStore.getState().streamingContent).toBe('Hello world');
  });

  it('sets streaming on and clears content', () => {
    useChatStore.getState().updateStreamingContent('old');
    useChatStore.getState().setStreaming(true, 'msg-1', 'conv-1');
    const state = useChatStore.getState();
    expect(state.isStreaming).toBe(true);
    expect(state.streamingMessageId).toBe('msg-1');
    expect(state.streamingContent).toBe('');
    expect(state.activeConversationId).toBe('conv-1');
  });

  it('finalizes stream with message', () => {
    useChatStore.getState().setStreaming(true, 'msg-1');
    useChatStore.getState().updateStreamingContent('content');
    useChatStore.getState().finalizeStream(
      makeMessage({ id: 'msg-1', role: 'assistant', content: 'content' }),
    );
    const state = useChatStore.getState();
    expect(state.isStreaming).toBe(false);
    expect(state.streamingContent).toBe('');
    expect(state.streamingMessageId).toBeNull();
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].content).toBe('content');
  });

  it('resets all state', () => {
    useChatStore.getState().setActiveConversation('conv-1');
    useChatStore.getState().appendMessage(makeMessage());
    useChatStore.getState().setStreaming(true);
    useChatStore.getState().reset();
    const state = useChatStore.getState();
    expect(state.activeConversationId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.isStreaming).toBe(false);
  });
});
