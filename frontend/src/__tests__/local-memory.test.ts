import 'fake-indexeddb/auto';
import { describe, expect, it, vi } from 'vitest';
import {
  addPinnedNote, createLocalConversation, exportLocalData, getLocalDigest,
  getRecentLocalMessages, importLocalData, listLocalConversations, listLocalMessages,
  saveLocalMessage, searchLocalHistory, searchTerms,
} from '@/lib/local-data';
import { buildLocalPromptContext, estimateTokens } from '@/lib/local-context';

describe('device-only conversation storage and retrieval', () => {
  it('keeps complete history, indexes Persian text, and sends bounded context', async () => {
    let id = 0;
    vi.stubGlobal('crypto', { randomUUID: () => `generated-${++id}` });
    const conversation = await createLocalConversation('My reflections');
    const oldFact = 'من برای برنامه‌ریزی روزانه به سکوت و زمان کافی نیاز دارم';
    for (let sequence = 1; sequence <= 20; sequence++) {
      await saveLocalMessage({
        id: `message-${sequence}`,
        conversation_id: conversation.id,
        role: sequence % 2 ? 'user' : 'assistant',
        content: sequence === 1 ? oldFact : `Reflection about item ${sequence}`,
        sequence_number: sequence,
        token_count: null,
        created_at: new Date(Date.UTC(2026, 0, sequence)).toISOString(),
      });
    }

    expect((await listLocalConversations()).data[0].message_count).toBe(20);
    expect((await listLocalMessages(conversation.id, 5)).data).toHaveLength(5);
    expect((await getRecentLocalMessages(conversation.id, 100))).toHaveLength(20);
    expect(searchTerms('برنامه ريزي')).toContain('ریزی');
    expect((await searchLocalHistory('برنامه')).map((item) => item.id)).toContain('message-1');
    expect((await getLocalDigest(conversation.id)).map((item) => item.content)).toContain(oldFact);

    await addPinnedNote('I prefer concise answers.');
    const current = 'آیا برنامه من بهتر شده؟';
    await saveLocalMessage({
      id: 'current', conversation_id: conversation.id, role: 'user', content: current,
      sequence_number: 21, token_count: null, created_at: new Date().toISOString(),
    });
    const context = await buildLocalPromptContext(conversation.id, current);
    expect(context.conversation_history.some((item) => item.content === current)).toBe(false);
    expect(context.memory_context).toContain('I prefer concise answers.');
    expect(context.memory_context).toContain('برنامه');
    expect(estimateTokens(JSON.stringify(context))).toBeLessThan(1600);

    const backup = await exportLocalData();
    await importLocalData(backup);
    expect((await listLocalMessages(conversation.id, 100)).total).toBe(21);
    vi.unstubAllGlobals();
  });
});
