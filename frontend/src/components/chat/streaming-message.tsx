'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { SSEClient, SSEMessage } from '@/lib/sse-client';

interface StreamingMessageProps {
  url: string;
  onComplete?: (content: string) => void;
  onError?: (error: Error) => void;
  className?: string;
}

export function StreamingMessage({ url, onComplete, onError, className }: StreamingMessageProps) {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  useEffect(() => {
    const client = new SSEClient(url);
    let fullContent = '';

    client.connect({
      onMessage: (message: SSEMessage) => {
        if (message.event === 'content_delta') {
          const delta = JSON.parse(message.data).delta;
          fullContent += delta;
          setContent(fullContent);
        } else if (message.event === 'message_end') {
          setIsStreaming(false);
          onComplete?.(fullContent);
        }
      },
      onError: () => {
        setIsStreaming(false);
        onError?.(new Error('Stream error'));
      },
    });

    return () => client.disconnect();
  }, [url, onComplete, onError]);

  return (
    <div className={cn('prose prose-sm max-w-none', className)}>
      {content}
      {isStreaming && <span className="animate-pulse">|</span>}
    </div>
  );
}
