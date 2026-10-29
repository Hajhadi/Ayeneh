import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationStreamClient } from '@/lib/stream-client';

describe('conversation stream client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('uses the configured endpoint and parses SSE events split across chunks', async () => {
    localStorage.setItem('ayeneh_api_url', 'https://gateway.example.com/');
    const chunks = [
      'event: message_start\n',
      'data: {"id":"m1","conversation_id":"c1","role":"assistant","created_at":"2026-01-01"}\n\n',
      'event: content_delta\ndata: {"delta":"Hello","index":0}\n\n',
      'event: message_end\n',
      'data: {"id":"m1","conversation_id":"c1","content":"Hello","token_count":1}\n\n',
    ];
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
        controller.close();
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(new Response(stream, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const onEnd = vi.fn();
    const onError = vi.fn();
    await new ConversationStreamClient('/api/v1/runtime/message/stream').start(
      { content: 'Hi', conversation_id: 'c1', conversation_history: [], memory_context: 'A saved fact' },
      { onStart: vi.fn(), onDelta: vi.fn(), onEnd, onError },
    );
    expect(fetchMock.mock.calls[0][0]).toBe('https://gateway.example.com/api/v1/runtime/message/stream');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).memory_context).toBe('A saved fact');
    expect(onEnd).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
  });
});
