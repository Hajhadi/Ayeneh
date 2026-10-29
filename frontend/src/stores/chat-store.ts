import { create } from 'zustand';
import type { Message } from '@/types/conversation';

export interface ThinkingStep {
  stage: string;
  status: 'running' | 'done' | 'error';
  confidence: number;
  duration_ms: number;
  message?: string;
  details?: Record<string, any>;
}

interface ChatState {
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingMessageId: string | null;
  thinkingSteps: ThinkingStep[];
  thinkingComplete: boolean;
  thinkingTotalMs: number;

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
  addThinkingStep: (step: ThinkingStep) => void;
  setThinkingComplete: (totalMs: number) => void;
  resetThinking: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingMessageId: null,
  thinkingSteps: [],
  thinkingComplete: false,
  thinkingTotalMs: 0,

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

  addThinkingStep: (step) =>
    set((state) => {
      const existing = state.thinkingSteps.findIndex(s => s.stage === step.stage);
      if (existing >= 0) {
        const prev = state.thinkingSteps[existing];
        const updated = [...state.thinkingSteps];
        updated[existing] = {
          ...step,
          message: step.message || prev.message,
          details: step.details || prev.details,
        };
        return { thinkingSteps: updated };
      }
      return { thinkingSteps: [...state.thinkingSteps, step] };
    }),

  setThinkingComplete: (totalMs) =>
    set({ thinkingComplete: true, thinkingTotalMs: totalMs }),

  resetThinking: () =>
    set({ thinkingSteps: [], thinkingComplete: false, thinkingTotalMs: 0 }),

  reset: () =>
    set({
      activeConversationId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
      streamingMessageId: null,
      thinkingSteps: [],
      thinkingComplete: false,
      thinkingTotalMs: 0,
    }),
}));
