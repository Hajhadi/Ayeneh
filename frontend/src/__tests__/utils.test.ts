import { describe, it, expect } from 'vitest';
import { cn, formatDate, formatRelativeTime, truncate } from '@/lib/utils';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('foo', false && 'bar')).toBe('foo');
    expect(cn('foo', true && 'bar')).toBe('foo bar');
  });

  it('deduplicates classes via twMerge', () => {
    expect(cn('foo', 'foo')).toContain('foo');
  });
});

describe('formatDate', () => {
  it('formats a date string', () => {
    const result = formatDate('2024-01-15');
    expect(result).toContain('Jan');
    expect(result).toContain('2024');
  });

  it('formats a Date object', () => {
    const result = formatDate(new Date('2024-06-15'));
    expect(result).toContain('Jun');
    expect(result).toContain('2024');
  });
});

describe('formatRelativeTime', () => {
  it('returns just now for recent times', () => {
    const now = new Date();
    expect(formatRelativeTime(now)).toBe('just now');
  });

  it('returns minutes ago', () => {
    const past = new Date(Date.now() - 5 * 60 * 1000);
    expect(formatRelativeTime(past)).toBe('5m ago');
  });

  it('returns hours ago', () => {
    const past = new Date(Date.now() - 3 * 60 * 60 * 1000);
    expect(formatRelativeTime(past)).toBe('3h ago');
  });

  it('returns days ago', () => {
    const past = new Date(Date.now() - 5 * 86400000);
    expect(formatRelativeTime(past)).toBe('5d ago');
  });
});

describe('truncate', () => {
  it('returns short text as-is', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('truncates long text', () => {
    const result = truncate('hello world this is long', 10);
    expect(result).toBe('hello w...');
    expect(result.length).toBe(10);
  });
});
