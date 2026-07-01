import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api-client';

export function useApiQuery<T>(
  key: string[],
  endpoint: string,
  params?: Record<string, string>,
  options?: Omit<UseQueryOptions<T, ApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<T, ApiError>({
    queryKey: key,
    queryFn: () => api.get<T>(endpoint, params),
    ...options,
  });
}
