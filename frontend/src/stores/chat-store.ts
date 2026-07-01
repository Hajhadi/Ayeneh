import { create } from 'zustand';
import type { Message } from '@/types/conversation';

interface ChatState {
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingMessageId: string | null;

  setActiveConversation: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  appendMessage: (message: Message) => void;
  updateStreamingContent: (delta: string) => void;
  setStreaming: (
    streaming: boolean,
    messageId?: string | null,
    conversationId?: string | null,
  ) => void;
  finalizeStream: (message: Message) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingMessageId: null,

  setActiveConversation: (id) =>
    set({ activeConversationId: id, messages: [], streamingContent: '', streamingMessageId: null }),

  setMessages: (messages) => set({ messages }),

  appendMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateStreamingContent: (delta) =>
    set((state) => ({
      streamingContent: state.streamingContent + delta,
    })),

  setStreaming: (streaming, messageId = null, conversationId = null) =>
    set((state) => ({
      isStreaming: streaming,
      streamingMessageId: messageId,
      streamingContent: streaming ? '' : state.streamingContent,
      ...(conversationId !== null ? { activeConversationId: conversationId } : {}),
    })),

  finalizeStream: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      isStreaming: false,
      streamingContent: '',
      streamingMessageId: null,
    })),

  reset: () =>
    set({
      activeConversationId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
      streamingMessageId: null,
    }),
}));
