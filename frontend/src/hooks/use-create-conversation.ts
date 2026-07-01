import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Conversation, CreateConversationRequest } from '@/types/conversation';
import { createConversation } from '@/lib/conversation-api';

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation<Conversation, Error, CreateConversationRequest>({
    mutationFn: createConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}
