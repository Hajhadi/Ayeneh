import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError } from '@/lib/api-client';

describe('ApiError', () => {
  it('creates error with status and code', () => {
    const error = new ApiError(404, 'NOT_FOUND', 'Resource not found');
    expect(error.status).toBe(404);
    expect(error.code).toBe('NOT_FOUND');
    expect(error.message).toBe('Resource not found');
    expect(error.name).toBe('ApiError');
  });

  it('includes details when provided', () => {
    const error = new ApiError(400, 'VALIDATION', 'Bad request', [{ field: 'email' }]);
    expect(error.details).toEqual([{ field: 'email' }]);
  });
});
