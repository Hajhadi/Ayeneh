import { api } from '@/lib/api-client';
import type {
  Conversation,
  ConversationListResponse,
  Message,
  MessageListResponse,
  CreateConversationRequest,
  SendMessageRequest,
} from '@/types/conversation';

const BASE = '/api/v1/conversations';

export async function listConversations(
  params: { limit?: number; cursor?: string } = {},
): Promise<ConversationListResponse> {
  const query: Record<string, string> = {};
  if (params.limit) query.limit = String(params.limit);
  if (params.cursor) query.cursor = params.cursor;
  return api.get<ConversationListResponse>(BASE, query);
}

export async function getConversation(id: string): Promise<Conversation> {
  return api.get<Conversation>(`${BASE}/${id}`);
}

export async function createConversation(
  body: CreateConversationRequest,
): Promise<Conversation> {
  return api.post<Conversation>(BASE, body);
}

export async function updateConversation(
  id: string,
  body: Partial<CreateConversationRequest>,
): Promise<{ id: string; updated: boolean }> {
  return api.patch<{ id: string; updated: boolean }>(`${BASE}/${id}`, body);
}

export async function archiveConversation(
  id: string,
): Promise<{ id: string; status: string }> {
  return api.post<{ id: string; status: string }>(`${BASE}/${id}/archive`);
}

export async function listMessages(
  conversationId: string,
  params: { limit?: number; cursor?: string } = {},
): Promise<MessageListResponse> {
  const query: Record<string, string> = {};
  if (params.limit) query.limit = String(params.limit);
  if (params.cursor) query.cursor = params.cursor;
  return api.get<MessageListResponse>(`${BASE}/${conversationId}/messages`, query);
}

export async function sendMessage(
  conversationId: string,
  body: SendMessageRequest,
): Promise<Message> {
  return api.post<Message>(`${BASE}/${conversationId}/messages`, body);
}
