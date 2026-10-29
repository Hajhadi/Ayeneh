import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useChatStore } from '@/stores/chat-store';
import { ConversationStreamClient } from '@/lib/stream-client';
import { DirectModelClient } from '@/lib/direct-model-client';
import { secureModelAvailable } from '@/lib/secure-model';
import { buildLocalPromptContext } from '@/lib/local-context';
import { saveLocalMessage } from '@/lib/local-data';
import { useCreateConversation } from './use-create-conversation';
import type { Message } from '@/types/conversation';

export function useStreamChat() {
  const streamClient = useRef<ConversationStreamClient | DirectModelClient | null>(null);
  const sending = useRef(false);
  const queryClient = useQueryClient();
  const createConversation = useCreateConversation();
  const {
    activeConversationId,
    isStreaming,
    setActiveConversation,
    appendMessage,
    setStreaming,
    updateStreamingContent,
    finalizeStream,
    setChatError,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (sending.current || isStreaming || !content.trim()) return;
      sending.current = true;
      setChatError(null);

      try {

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
      await saveLocalMessage(userMessage);
      appendMessage(userMessage);
      await queryClient.invalidateQueries({ queryKey: ['messages', convId] });
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });

      const promptContext = await buildLocalPromptContext(convId, content.trim());

      setStreaming(true, null, convId);

      streamClient.current = secureModelAvailable()
        ? new DirectModelClient()
        : new ConversationStreamClient('/api/v1/runtime/message/stream');

      let accumulated = '';

      await streamClient.current.start(
        { content: content.trim(), conversation_id: convId, ...promptContext },
        {
          onStart: (data) => {
            setStreaming(true, data.id);
          },
          onDelta: (data) => {
            accumulated += data.delta;
            updateStreamingContent(data.delta);
          },
          onEnd: async (data) => {
            const assistantMsg: Message = {
              id: data.id,
              conversation_id: data.conversation_id,
              role: 'assistant',
              content: data.content || accumulated,
              sequence_number: Date.now(),
              token_count: data.token_count,
              created_at: new Date().toISOString(),
            };
            await saveLocalMessage(assistantMsg);
            finalizeStream(assistantMsg);
            await queryClient.invalidateQueries({ queryKey: ['messages', convId] });
            await queryClient.invalidateQueries({ queryKey: ['conversations'] });
          },
          onError: (error) => {
            console.error('Stream error:', error);
            setChatError(error.message);
            setStreaming(false);
          },
        },
      );
      } catch (error) {
        setChatError(error instanceof Error ? error.message : 'Could not save or send message');
        setStreaming(false);
      } finally {
        sending.current = false;
      }
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
      queryClient,
      setChatError,
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
