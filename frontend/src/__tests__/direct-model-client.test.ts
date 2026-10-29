import { beforeEach, describe, expect, it, vi } from 'vitest';

const secure = vi.hoisted(() => ({
  addListener: vi.fn(), listProfiles: vi.fn(), generate: vi.fn(), cancelGeneration: vi.fn(),
}));

vi.mock('@/lib/secure-model', () => ({ SecureModel: secure }));

import { DirectModelClient } from '@/lib/direct-model-client';

describe('direct model client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    secure.addListener.mockResolvedValue({ remove: vi.fn().mockResolvedValue(undefined) });
    secure.listProfiles.mockResolvedValue({ activeProvider: 'openai', profiles: [] });
    secure.generate.mockResolvedValue({ content: 'A considered answer', tokenCount: 12 });
  });

  it('passes bounded local context to the native bridge without an API key', async () => {
    const onEnd = vi.fn();
    const onError = vi.fn();
    const client = new DirectModelClient();
    await client.start({
      content: 'Hello', conversation_id: 'conv-1',
      conversation_history: [{ role: 'user', content: 'Earlier' }],
      memory_context: 'I like concise answers',
    }, { onStart: vi.fn(), onDelta: vi.fn(), onEnd, onError });
    expect(secure.generate).toHaveBeenCalledOnce();
    expect(secure.generate.mock.calls[0][0].memoryContext).toBe('I like concise answers');
    expect(JSON.stringify(secure.generate.mock.calls[0][0])).not.toContain('apiKey');
    expect(onEnd.mock.calls[0][0].content).toBe('A considered answer');
    expect(onError).not.toHaveBeenCalled();
  });

  it('asks for a saved key when no model is active', async () => {
    secure.listProfiles.mockResolvedValue({ activeProvider: '', profiles: [] });
    const onError = vi.fn();
    await new DirectModelClient().start({ content: 'Hello' }, {
      onStart: vi.fn(), onDelta: vi.fn(), onEnd: vi.fn(), onError,
    });
    expect(secure.generate).not.toHaveBeenCalled();
    expect(onError.mock.calls[0][0].message).toContain('Settings');
  });
});
