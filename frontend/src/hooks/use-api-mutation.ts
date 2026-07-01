import { useMutation, UseMutationOptions } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api-client';

export function useApiMutation<TData, TVariables = void>(
  endpoint: string,
  method: 'POST' | 'PATCH' | 'DELETE' = 'POST',
  options?: Omit<UseMutationOptions<TData, ApiError, TVariables>, 'mutationFn'>,
) {
  return useMutation<TData, ApiError, TVariables>({
    mutationFn: (variables: TVariables) => {
      switch (method) {
        case 'POST':
          return api.post<TData>(endpoint, variables);
        case 'PATCH':
          return api.patch<TData>(endpoint, variables);
        case 'DELETE':
          return api.delete<TData>(endpoint);
        default:
          return api.post<TData>(endpoint, variables);
      }
    },
    ...options,
  });
}
