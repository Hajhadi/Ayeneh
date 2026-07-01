import { useQuery } from '@tanstack/react-query';
import type { ConversationListResponse } from '@/types/conversation';
import { listConversations } from '@/lib/conversation-api';

export function useConversations(limit = 20) {
  return useQuery<ConversationListResponse>({
    queryKey: ['conversations', { limit }],
    queryFn: () => listConversations({ limit }),
  });
}
