import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ChatWindow } from '@/components/chat/chat-window';
import { MessageInput } from '@/components/chat/message-input';
import type { Message } from '@/types/conversation';

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: crypto.randomUUID(),
    conversation_id: 'conv-1',
    role: 'user',
    content: 'Hello',
    sequence_number: 1,
    token_count: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('ChatWindow', () => {
  it('renders empty state when no messages', () => {
    render(
      <ChatWindow messages={[]} isStreaming={false} streamingContent="" />,
    );
    expect(screen.getByText('Start a conversation with Ayeneh.')).toBeInTheDocument();
  });

  it('renders user messages with right alignment', () => {
    const messages = [makeMessage({ role: 'user', content: 'Hi there' })];
    render(
      <ChatWindow messages={messages} isStreaming={false} streamingContent="" />,
    );
    expect(screen.getByText('Hi there')).toBeInTheDocument();
  });

  it('renders assistant messages with markdown', () => {
    const messages = [
      makeMessage({
        role: 'assistant',
        content: '**Bold text**',
        sequence_number: 2,
      }),
    ];
    render(
      <ChatWindow messages={messages} isStreaming={false} streamingContent="" />,
    );
    expect(screen.getByText('Bold text')).toBeInTheDocument();
  });

  it('renders streaming content with cursor', () => {
    const messages = [makeMessage({ role: 'user', content: 'Hello' })];
    const { container } = render(
      <ChatWindow
        messages={messages}
        isStreaming={true}
        streamingContent="Hello world"
      />,
    );
    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows spinner when streaming with no content yet', () => {
    const messages = [makeMessage({ role: 'user', content: 'Hello' })];
    const { container } = render(
      <ChatWindow
        messages={messages}
        isStreaming={true}
        streamingContent=""
      />,
    );
    expect(container.querySelector('svg.animate-spin')).toBeInTheDocument();
  });

  it('preserves message ordering', () => {
    const messages = [
      makeMessage({ role: 'user', content: 'First', sequence_number: 1 }),
      makeMessage({
        role: 'assistant',
        content: 'Second',
        sequence_number: 2,
      }),
      makeMessage({ role: 'user', content: 'Third', sequence_number: 3 }),
    ];
    render(
      <ChatWindow messages={messages} isStreaming={false} streamingContent="" />,
    );
    const rendered = screen.getAllByText(/First|Second|Third/);
    expect(rendered).toHaveLength(3);
  });
});

describe('MessageInput', () => {
  it('renders textarea placeholder', () => {
    render(<MessageInput onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });

  it('calls onSend when Enter is pressed', () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    expect(onSend).toHaveBeenCalledWith('Hello world');
  });

  it('does not send empty messages', () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
  });

  it('shows stop button when streaming', () => {
    const onCancel = vi.fn();
    render(
      <MessageInput
        onSend={vi.fn()}
        onCancel={onCancel}
        isStreaming={true}
      />,
    );
    expect(screen.getByLabelText('Stop generating')).toBeInTheDocument();
  });

  it('calls onCancel when stop button clicked', () => {
    const onCancel = vi.fn();
    render(
      <MessageInput
        onSend={vi.fn()}
        onCancel={onCancel}
        isStreaming={true}
      />,
    );
    fireEvent.click(screen.getByLabelText('Stop generating'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('disables input when streaming', () => {
    render(
      <MessageInput onSend={vi.fn()} isStreaming={true} />,
    );
    expect(screen.getByPlaceholderText('Type a message...')).toBeDisabled();
  });

  it('clears input after sending', () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'Test' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    expect(textarea).toHaveValue('');
  });
});
