import type { StreamCallbacks, StreamMessageRequest } from '@/types/conversation';
import { getApiBase } from '@/lib/api-client';

export class ConversationStreamClient {
  private controller: AbortController | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  async start(
    body: StreamMessageRequest,
    callbacks: StreamCallbacks,
  ): Promise<void> {
    this.controller = new AbortController();
    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem('access_token')
        : null;

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) headers.Authorization = `Bearer ${token}`;

      const response = await fetch(`${getApiBase()}${this.url}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: this.controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let completed = false;
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line === '') {
            currentEvent = '';
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            let parsed: unknown;
            try {
              parsed = JSON.parse(data);
            } catch {
              continue;
            }
            switch (currentEvent) {
                case 'message_start':
                  callbacks.onStart(parsed as Parameters<StreamCallbacks['onStart']>[0]);
                  break;
                case 'content_delta':
                  callbacks.onDelta(parsed as Parameters<StreamCallbacks['onDelta']>[0]);
                  break;
                case 'message_end':
                  await callbacks.onEnd(parsed as Parameters<StreamCallbacks['onEnd']>[0]);
                  completed = true;
                  break;
                case 'message_error':
                  throw new Error((parsed as { message?: string }).message || 'Model response failed');
            }
          }
        }
      }
      if (!completed) throw new Error('Response ended before the assistant message was complete');
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      callbacks.onError(error as Error);
    }
  }

  cancel(): void {
    this.controller?.abort();
    this.controller = null;
  }
}
