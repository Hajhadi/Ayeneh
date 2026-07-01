import type { StreamCallbacks } from '@/types/conversation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ConversationStreamClient {
  private controller: AbortController | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  async start(
    body: { content: string; conversation_id?: string },
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

      const response = await fetch(`${API_BASE}${this.url}`, {
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              switch (currentEvent) {
                case 'message_start':
                  callbacks.onStart(parsed);
                  break;
                case 'content_delta':
                  callbacks.onDelta(parsed);
                  break;
                case 'message_end':
                  callbacks.onEnd(parsed);
                  break;
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }
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
