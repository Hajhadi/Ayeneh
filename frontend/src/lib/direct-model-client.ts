import type { StreamCallbacks, StreamMessageRequest } from '@/types/conversation';
import { SecureModel } from '@/lib/secure-model';

export class DirectModelClient {
  private cancelled = false;

  async start(body: StreamMessageRequest, callbacks: StreamCallbacks): Promise<void> {
    const requestId = crypto.randomUUID();
    const conversationId = body.conversation_id || crypto.randomUUID();
    this.cancelled = false;
    let accumulated = '';
    const listener = await SecureModel.addListener('modelDelta', (event) => {
      if (this.cancelled || event.requestId !== requestId) return;
      accumulated += event.delta;
      callbacks.onDelta({ delta: event.delta, index: accumulated.length });
    });

    try {
      const profiles = await SecureModel.listProfiles();
      if (!profiles.activeProvider) {
        throw new Error('Save and select a cloud model API key in Settings.');
      }
      callbacks.onStart({
        id: requestId, conversation_id: conversationId, role: 'assistant',
        created_at: new Date().toISOString(),
      });
      const result = await SecureModel.generate({
        requestId,
        content: body.content,
        conversationHistory: body.conversation_history || [],
        memoryContext: body.memory_context || '',
      });
      if (!this.cancelled) {
        await callbacks.onEnd({
          id: requestId, conversation_id: conversationId,
          content: result.content || accumulated,
          token_count: result.tokenCount,
        });
      }
    } catch (error) {
      if (!this.cancelled) callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    } finally {
      await listener.remove();
    }
  }

  cancel(): void {
    this.cancelled = true;
    void SecureModel.cancelGeneration();
  }
}
