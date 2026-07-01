'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { SSEClient, SSEMessage } from '@/lib/sse-client';

interface UseSSEOptions {
  url: string;
  onMessage: (message: SSEMessage) => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export function useSSE({ url, onMessage, onError, autoConnect = true }: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const clientRef = useRef<SSEClient | null>(null);

  const connect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    clientRef.current = new SSEClient(url);
    clientRef.current.connect({
      onMessage,
      onError: (error) => {
        setIsConnected(false);
        onError?.(error);
      },
      onOpen: () => setIsConnected(true),
      onClose: () => setIsConnected(false),
    });
  }, [url, onMessage, onError]);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  return { isConnected, connect, disconnect };
}
