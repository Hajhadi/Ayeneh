import type {
  Conversation,
  ConversationListResponse,
  Message,
  MessageListResponse,
} from '@/types/conversation';

const DB_NAME = 'ayeneh-local';
const DB_VERSION = 2;

export interface MemoryExcerpt {
  id: string;
  conversation_id: string;
  content: string;
  created_at: string;
  score: number;
}

export interface LocalDocument {
  id: string;
  title: string;
  author: string;
  file_name: string;
  mime_type: string;
  size: number;
  created_at: string;
  content: Blob;
}

interface StoredMessage extends Message {
  search_terms: string[];
}

interface Digest {
  conversation_id: string;
  excerpts: MemoryExcerpt[];
}

let opening: Promise<IDBDatabase> | undefined;

function request<T>(operation: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    operation.onsuccess = () => resolve(operation.result);
    operation.onerror = () => reject(operation.error);
  });
}

function finished(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onabort = () => reject(transaction.error || new Error('Local storage transaction failed'));
    transaction.onerror = () => reject(transaction.error || new Error('Local storage transaction failed'));
  });
}

function database(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') {
    return Promise.reject(new Error('Local storage is unavailable on this device'));
  }
  if (!opening) {
    opening = new Promise<IDBDatabase>((resolve, reject) => {
      const open = indexedDB.open(DB_NAME, DB_VERSION);
      open.onupgradeneeded = () => {
        const db = open.result;
        if (!db.objectStoreNames.contains('conversations')) {
          const conversations = db.createObjectStore('conversations', { keyPath: 'id' });
          conversations.createIndex('updated_at', 'updated_at');
          conversations.createIndex('status_updated', ['status', 'updated_at']);
        }
        if (!db.objectStoreNames.contains('messages')) {
          const messages = db.createObjectStore('messages', { keyPath: 'id' });
          messages.createIndex('conversation_sequence', ['conversation_id', 'sequence_number']);
          messages.createIndex('search_terms', 'search_terms', { multiEntry: true });
        }
        if (!db.objectStoreNames.contains('digests')) db.createObjectStore('digests', { keyPath: 'conversation_id' });
        if (!db.objectStoreNames.contains('documents')) {
          const documents = db.createObjectStore('documents', { keyPath: 'id' });
          documents.createIndex('created_at', 'created_at');
        }
      };
      open.onsuccess = () => {
        const db = open.result;
        db.onversionchange = () => db.close();
        resolve(db);
      };
      open.onerror = () => reject(open.error);
      open.onblocked = () => reject(new Error('Close other Ayeneh tabs to update local storage'));
    }).catch((error) => {
      opening = undefined;
      throw error;
    });
  }
  return opening;
}

export async function listLocalDocuments(): Promise<LocalDocument[]> {
  const db = await database();
  const tx = db.transaction('documents', 'readonly');
  const done = finished(tx);
  const documents = await request<LocalDocument[]>(tx.objectStore('documents').getAll());
  await done;
  return documents.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function saveLocalDocument(input: {
  title: string;
  author?: string;
  file?: File | null;
  text?: string;
}): Promise<LocalDocument> {
  const title = input.title.trim();
  if (!title) throw new Error('Document title is required');
  const file = input.file;
  const text = input.text || '';
  const content = file || new Blob([text], { type: 'text/plain;charset=utf-8' });
  const document: LocalDocument = {
    id: crypto.randomUUID(), title, author: input.author?.trim() || '',
    file_name: file?.name || `${title}.txt`,
    mime_type: file?.type || 'text/plain', size: content.size,
    created_at: new Date().toISOString(), content,
  };
  const db = await database();
  const tx = db.transaction('documents', 'readwrite');
  const done = finished(tx);
  tx.objectStore('documents').put(document);
  await done;
  return document;
}

export async function removeLocalDocument(id: string): Promise<void> {
  const db = await database();
  const tx = db.transaction('documents', 'readwrite');
  const done = finished(tx);
  tx.objectStore('documents').delete(id);
  await done;
}

export function searchTerms(text: string): string[] {
  return [...new Set(
    text.toLocaleLowerCase()
      .normalize('NFKC')
      .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
      .replace(/[يى]/g, 'ی')
      .replace(/ك/g, 'ک')
      .match(/[\p{L}\p{N}]{2,}/gu) || [],
  )].filter((term) => !STOP_WORDS.has(term));
}

const STOP_WORDS = new Set([
  'the', 'and', 'for', 'with', 'that', 'this', 'are', 'was', 'you',
  'از', 'به', 'در', 'که', 'را', 'این', 'آن', 'برای', 'با', 'من', 'تو', 'هم', 'یک',
]);

export async function createLocalConversation(title: string): Promise<Conversation> {
  const db = await database();
  const now = new Date().toISOString();
  const conversation: Conversation = {
    id: crypto.randomUUID(), user_id: 'local', title: title.trim().slice(0, 100),
    topic: null, status: 'active', message_count: 0, created_at: now, updated_at: now,
  };
  const tx = db.transaction('conversations', 'readwrite');
  const done = finished(tx);
  tx.objectStore('conversations').put(conversation);
  await done;
  return conversation;
}

export async function listLocalConversations(limit = 20): Promise<ConversationListResponse> {
  const db = await database();
  const tx = db.transaction('conversations', 'readonly');
  const done = finished(tx);
  const store = tx.objectStore('conversations');
  const active = IDBKeyRange.bound(['active', ''], ['active', '\uffff']);
  const index = store.index('status_updated');
  const total = await request(index.count(active));
  const data: Conversation[] = [];
  await new Promise<void>((resolve, reject) => {
    const cursor = index.openCursor(active, 'prev');
    cursor.onerror = () => reject(cursor.error);
    cursor.onsuccess = () => {
      if (!cursor.result || data.length >= limit) return resolve();
      data.push(cursor.result.value);
      cursor.result.continue();
    };
  });
  await done;
  return { data, total, has_more: total > data.length };
}

export async function getLocalConversation(id: string): Promise<Conversation | undefined> {
  const db = await database();
  return request(db.transaction('conversations').objectStore('conversations').get(id));
}

export async function updateLocalConversation(
  id: string, changes: Partial<Pick<Conversation, 'title' | 'topic' | 'status'>>,
): Promise<{ id: string; updated: boolean }> {
  const db = await database();
  const tx = db.transaction('conversations', 'readwrite');
  const done = finished(tx);
  const store = tx.objectStore('conversations');
  const existing = await request<Conversation | undefined>(store.get(id));
  if (existing) store.put({ ...existing, ...changes, updated_at: new Date().toISOString() });
  await done;
  return { id, updated: !!existing };
}

export async function saveLocalMessage(message: Message): Promise<void> {
  const db = await database();
  const tx = db.transaction(['messages', 'conversations'], 'readwrite');
  const done = finished(tx);
  const messages = tx.objectStore('messages');
  const conversations = tx.objectStore('conversations');
  const existing = await request<StoredMessage | undefined>(messages.get(message.id));
  const conversation = await request<Conversation | undefined>(conversations.get(message.conversation_id));
  if (!conversation) {
    await done;
    throw new Error('Conversation was not saved locally');
  }
  messages.put({ ...message, search_terms: searchTerms(message.content) } satisfies StoredMessage);
  conversations.put({
    ...conversation,
    message_count: conversation.message_count + (existing ? 0 : 1),
    updated_at: message.created_at,
  });
  await done;
  if (message.role === 'assistant') await refreshDigest(message.conversation_id);
}

export async function getRecentLocalMessages(conversationId: string, limit = 100): Promise<Message[]> {
  const db = await database();
  const tx = db.transaction('messages', 'readonly');
  const done = finished(tx);
  const range = IDBKeyRange.bound([conversationId, 0], [conversationId, Number.MAX_SAFE_INTEGER]);
  const messages: Message[] = [];
  await new Promise<void>((resolve, reject) => {
    const cursor = tx.objectStore('messages').index('conversation_sequence').openCursor(range, 'prev');
    cursor.onerror = () => reject(cursor.error);
    cursor.onsuccess = () => {
      if (!cursor.result || messages.length >= limit) return resolve();
      messages.push(cursor.result.value);
      cursor.result.continue();
    };
  });
  await done;
  return messages.reverse();
}

export async function listLocalMessages(conversationId: string, limit = 100): Promise<MessageListResponse> {
  const [messages, conversation] = await Promise.all([
    getRecentLocalMessages(conversationId, limit), getLocalConversation(conversationId),
  ]);
  return {
    data: messages, total: conversation?.message_count || 0,
    has_more: (conversation?.message_count || 0) > messages.length,
  };
}

function excerptScore(content: string): number {
  const personal = /\b(i am|i have|i want|i prefer|my|always|never)\b|(?:من|زندگی|هدف|ترجیح|دوست|همیشه|هیچوقت|خانواده|کارم)/iu.test(content);
  return (personal ? 3 : 0) + Math.min(searchTerms(content).length, 20) / 10;
}

async function refreshDigest(conversationId: string): Promise<void> {
  // Preserve selected, verbatim older user statements. This avoids an extra model call
  // and never invents a biographical fact while keeping a small continuity note.
  const recent = await getRecentLocalMessages(conversationId, 16);
  if (recent.length < 16) return;
  const candidate = recent[0];
  if (candidate.role !== 'user' || candidate.content.trim().length < 24) return;
  const db = await database();
  const tx = db.transaction('digests', 'readwrite');
  const done = finished(tx);
  const store = tx.objectStore('digests');
  const digest = await request<Digest | undefined>(store.get(conversationId));
  const excerpts = digest?.excerpts || [];
  if (!excerpts.some((item) => item.id === candidate.id)) {
    excerpts.push({
      id: candidate.id, conversation_id: conversationId,
      content: candidate.content.trim().slice(0, 240),
      created_at: candidate.created_at, score: excerptScore(candidate.content),
    });
    excerpts.sort((a, b) => b.score - a.score || b.created_at.localeCompare(a.created_at));
    store.put({ conversation_id: conversationId, excerpts: excerpts.slice(0, 8) } satisfies Digest);
  }
  await done;
}

export async function getLocalDigest(conversationId: string): Promise<MemoryExcerpt[]> {
  const db = await database();
  const digest = await request<Digest | undefined>(
    db.transaction('digests').objectStore('digests').get(conversationId),
  );
  return digest?.excerpts || [];
}

export async function listLocalDigests(): Promise<MemoryExcerpt[]> {
  const db = await database();
  const digests = await request<Digest[]>(db.transaction('digests').objectStore('digests').getAll());
  return digests.flatMap((digest) => digest.conversation_id === 'pinned' ? [] : digest.excerpts)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function addPinnedNote(content: string): Promise<MemoryExcerpt> {
  const clean = content.trim();
  if (!clean || clean.length > 500) throw new Error('Memory must be between 1 and 500 characters');
  const db = await database();
  const tx = db.transaction('digests', 'readwrite');
  const done = finished(tx);
  const store = tx.objectStore('digests');
  const digest = await request<Digest | undefined>(store.get('pinned'));
  const note: MemoryExcerpt = {
    id: crypto.randomUUID(), conversation_id: 'pinned', content: clean,
    created_at: new Date().toISOString(), score: 10,
  };
  store.put({ conversation_id: 'pinned', excerpts: [note, ...(digest?.excerpts || [])] } satisfies Digest);
  await done;
  return note;
}

export async function removePinnedNote(id: string): Promise<void> {
  const db = await database();
  const tx = db.transaction('digests', 'readwrite');
  const done = finished(tx);
  const store = tx.objectStore('digests');
  const digest = await request<Digest | undefined>(store.get('pinned'));
  if (digest) store.put({ ...digest, excerpts: digest.excerpts.filter((item) => item.id !== id) });
  await done;
}

export async function exportLocalData(): Promise<string> {
  const db = await database();
  const tx = db.transaction(['conversations', 'messages', 'digests'], 'readonly');
  const done = finished(tx);
  const [conversations, messages, digests] = await Promise.all([
    request<Conversation[]>(tx.objectStore('conversations').getAll()),
    request<StoredMessage[]>(tx.objectStore('messages').getAll()),
    request<Digest[]>(tx.objectStore('digests').getAll()),
  ]);
  await done;
  return JSON.stringify({ schema_version: DB_VERSION, exported_at: new Date().toISOString(), conversations, messages, digests });
}

export async function importLocalData(json: string): Promise<void> {
  const parsed: unknown = JSON.parse(json);
  if (!parsed || typeof parsed !== 'object') throw new Error('Invalid backup file');
  const data = parsed as Record<string, unknown>;
  if (data.schema_version !== DB_VERSION || !Array.isArray(data.conversations)
    || !Array.isArray(data.messages) || !Array.isArray(data.digests)) {
    throw new Error('Unsupported Ayeneh backup version');
  }
  const conversations = data.conversations as Conversation[];
  const messages = data.messages as StoredMessage[];
  const digests = data.digests as Digest[];
  if (conversations.some((item) => !item || typeof item.id !== 'string' || typeof item.title !== 'string')
    || messages.some((item) => !item || typeof item.id !== 'string' || typeof item.conversation_id !== 'string'
      || typeof item.content !== 'string' || !['user', 'assistant'].includes(item.role))
    || digests.some((item) => !item || typeof item.conversation_id !== 'string' || !Array.isArray(item.excerpts))) {
    throw new Error('Backup contains invalid records');
  }
  const db = await database();
  const tx = db.transaction(['conversations', 'messages', 'digests'], 'readwrite');
  const done = finished(tx);
  const conversationStore = tx.objectStore('conversations');
  const messageStore = tx.objectStore('messages');
  const digestStore = tx.objectStore('digests');
  for (const item of conversations) conversationStore.put(item);
  for (const item of messages) messageStore.put({ ...item, search_terms: searchTerms(item.content) });
  for (const item of digests) digestStore.put(item);
  await done;
}

export async function searchLocalHistory(query: string, limit = 8): Promise<Message[]> {
  const terms = searchTerms(query).slice(0, 8);
  if (!terms.length) return [];
  const db = await database();
  const tx = db.transaction('messages', 'readonly');
  const done = finished(tx);
  const index = tx.objectStore('messages').index('search_terms');
  const candidates = new Map<string, StoredMessage>();
  for (const term of terms) {
    const matches = await request<StoredMessage[]>(index.getAll(IDBKeyRange.only(term), 100));
    for (const match of matches) candidates.set(match.id, match);
  }
  await done;
  return [...candidates.values()]
    .map((message) => ({
      message,
      score: terms.filter((term) => message.search_terms.includes(term)).length / terms.length
        + (message.role === 'user' ? 0.15 : 0),
    }))
    .sort((a, b) => b.score - a.score || b.message.created_at.localeCompare(a.message.created_at))
    .slice(0, limit)
    .map(({ message }) => message);
}
