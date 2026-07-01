import { useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { ConversationStreamClient } from '@/lib/stream-client';
import { useCreateConversation } from './use-create-conversation';
import type { Message } from '@/types/conversation';

export function useStreamChat() {
  const streamClient = useRef<ConversationStreamClient | null>(null);
  const createConversation = useCreateConversation();
  const {
    activeConversationId,
    isStreaming,
    setActiveConversation,
    appendMessage,
    setStreaming,
    updateStreamingContent,
    finalizeStream,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreaming || !content.trim()) return;

      let convId = activeConversationId;

      if (!convId) {
        const conv = await createConversation.mutateAsync({
          title: content.slice(0, 100),
        });
        convId = conv.id;
        setActiveConversation(convId);
      }

      const userMessage: Message = {
        id: crypto.randomUUID(),
        conversation_id: convId,
        role: 'user',
        content: content.trim(),
        sequence_number: Date.now(),
        token_count: null,
        created_at: new Date().toISOString(),
      };
      appendMessage(userMessage);

      setStreaming(true, null, convId);

      streamClient.current = new ConversationStreamClient(
        '/api/v1/runtime/message/stream',
      );

      let accumulated = '';

      await streamClient.current.start(
        { content: content.trim(), conversation_id: convId },
        {
          onStart: (data) => {
            setStreaming(true, data.id);
          },
          onDelta: (data) => {
            accumulated += data.delta;
            updateStreamingContent(data.delta);
          },
          onEnd: (data) => {
            const assistantMsg: Message = {
              id: data.id,
              conversation_id: data.conversation_id,
              role: 'assistant',
              content: data.content || accumulated,
              sequence_number: Date.now(),
              token_count: data.token_count,
              created_at: new Date().toISOString(),
            };
            finalizeStream(assistantMsg);
          },
          onError: (error) => {
            console.error('Stream error:', error);
            setStreaming(false);
          },
        },
      );
    },
    [
      activeConversationId,
      isStreaming,
      createConversation,
      setActiveConversation,
      appendMessage,
      setStreaming,
      updateStreamingContent,
      finalizeStream,
    ],
  );

  const cancelStream = useCallback(() => {
    streamClient.current?.cancel();
    setStreaming(false);
  }, [setStreaming]);

  return {
    sendMessage,
    cancelStream,
    isStreaming,
    activeConversationId,
  };
}
