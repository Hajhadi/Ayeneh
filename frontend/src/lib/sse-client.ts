export interface SSEMessage {
  event: string;
  data: string;
  id?: string;
}

export interface SSEOptions {
  onMessage: (message: SSEMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect(options: SSEOptions) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    this.eventSource = new EventSource(
      `${this.url}${this.url.includes('?') ? '&' : '?'}token=${token}`,
    );

    this.eventSource.onmessage = (event) => {
      options.onMessage({
        event: event.type || 'message',
        data: event.data,
        id: event.lastEventId || undefined,
      });
    };

    this.eventSource.onerror = (error) => {
      options.onError?.(error);
    };

    this.eventSource.onopen = () => {
      options.onOpen?.();
    };
  }

  disconnect() {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
