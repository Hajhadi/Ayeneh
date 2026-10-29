import {
  createLocalConversation,
  getLocalConversation,
  listLocalConversations,
  listLocalMessages,
  saveLocalMessage,
  updateLocalConversation,
} from '@/lib/local-data';
import type {
  Conversation,
  ConversationListResponse,
  Message,
  MessageListResponse,
  CreateConversationRequest,
  SendMessageRequest,
} from '@/types/conversation';

export async function listConversations(
  params: { limit?: number; cursor?: string } = {},
): Promise<ConversationListResponse> {
  return listLocalConversations(params.limit);
}

export async function getConversation(id: string): Promise<Conversation> {
  const conversation = await getLocalConversation(id);
  if (!conversation) throw new Error('Conversation not found on this device');
  return conversation;
}

export async function createConversation(
  body: CreateConversationRequest,
): Promise<Conversation> {
  return createLocalConversation(body.title);
}

export async function updateConversation(
  id: string,
  body: Partial<CreateConversationRequest>,
): Promise<{ id: string; updated: boolean }> {
  return updateLocalConversation(id, body);
}

export async function archiveConversation(
  id: string,
): Promise<{ id: string; status: string }> {
  await updateLocalConversation(id, { status: 'archived' });
  return { id, status: 'archived' };
}

export async function listMessages(
  conversationId: string,
  params: { limit?: number; cursor?: string } = {},
): Promise<MessageListResponse> {
  return listLocalMessages(conversationId, params.limit);
}

export async function sendMessage(
  conversationId: string,
  body: SendMessageRequest,
): Promise<Message> {
  const message: Message = {
    id: crypto.randomUUID(), conversation_id: conversationId, role: 'user',
    content: body.content.trim(), sequence_number: Date.now(), token_count: null,
    created_at: new Date().toISOString(),
  };
  await saveLocalMessage(message);
  return message;
}
