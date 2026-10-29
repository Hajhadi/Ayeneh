export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  topic: string | null;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sequence_number: number;
  token_count: number | null;
  created_at: string;
}

export interface ConversationListResponse {
  data: Conversation[];
  total: number;
  has_more: boolean;
}

export interface MessageListResponse {
  data: Message[];
  total: number;
  has_more: boolean;
}

export interface CreateConversationRequest {
  title: string;
  topic?: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface StreamMessageRequest {
  content: string;
  conversation_id?: string;
  conversation_history?: { role: 'user' | 'assistant'; content: string }[];
  memory_context?: string;
}

export interface SSEMessageStart {
  id: string;
  conversation_id: string;
  role: 'assistant';
  created_at: string;
}

export interface SSEContentDelta {
  delta: string;
  index: number;
}

export interface SSEMessageEnd {
  id: string;
  conversation_id: string;
  content: string;
  token_count: number;
}

export interface StreamCallbacks {
  onStart: (data: SSEMessageStart) => void;
  onDelta: (data: SSEContentDelta) => void;
  onEnd: (data: SSEMessageEnd) => void | Promise<void>;
  onError: (error: Error) => void;
}
