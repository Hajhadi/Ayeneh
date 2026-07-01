import { useQuery } from '@tanstack/react-query';
import type { MessageListResponse } from '@/types/conversation';
import { listMessages } from '@/lib/conversation-api';

export function useConversationMessages(conversationId: string | null, limit = 100) {
  return useQuery<MessageListResponse>({
    queryKey: ['messages', conversationId, { limit }],
    queryFn: () => listMessages(conversationId!, { limit }),
    enabled: !!conversationId,
  });
}
