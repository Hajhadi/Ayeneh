import { useQuery, useMutation, useQueryClient, UseQueryOptions } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api-client';
import {
  authApi,
  conversationsApi,
  memoriesApi,
  patternsApi,
  reflectionsApi,
  blindSpotsApi,
  libraryApi,
  jobsApi,
  dashboardApi,
} from '@/lib/api';
import type * as T from '@/types/api';

/* ── Auth hooks ── */
export function useUser() {
  return useQuery<T.User, ApiError>({
    queryKey: ['user'],
    queryFn: authApi.me,
    retry: false,
    staleTime: 300000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { display_name?: string }) => authApi.updateProfile(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user'] }),
  });
}

export function useUserStats() {
  return useQuery({
    queryKey: ['user-stats'],
    queryFn: authApi.stats,
  });
}

/* ── Conversation hooks ── */
export function useConversations(limit = 20) {
  return useQuery({
    queryKey: ['conversations', limit],
    queryFn: () => conversationsApi.list({ limit }),
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ['conversation', id],
    queryFn: () => conversationsApi.get(id!),
    enabled: !!id,
  });
}

export function useConversationMessages(id: string | null, limit = 100) {
  return useQuery({
    queryKey: ['messages', id, limit],
    queryFn: () => conversationsApi.messages(id!, { limit }),
    enabled: !!id,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; topic?: string }) =>
      conversationsApi.create(data.title, data.topic),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversations'] }),
  });
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; title?: string; topic?: string }) =>
      conversationsApi.update(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['conversations'] });
      qc.invalidateQueries({ queryKey: ['conversation', vars.id] });
    },
  });
}

export function useArchiveConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => conversationsApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversations'] }),
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, content }: { conversationId: string; content: string }) =>
      conversationsApi.sendMessage(conversationId, content),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['messages', vars.conversationId] });
      qc.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

/* ── Memory hooks ── */
export function useMemories(limit = 20) {
  return useQuery({
    queryKey: ['memories', limit],
    queryFn: () => memoriesApi.list({ limit }),
  });
}

export function useMemory(id: string | null) {
  return useQuery({
    queryKey: ['memory', id],
    queryFn: () => memoriesApi.get(id!),
    enabled: !!id,
  });
}

export function useSearchMemories(query: string) {
  return useQuery({
    queryKey: ['memories-search', query],
    queryFn: () => memoriesApi.search(query),
    enabled: query.length > 0,
  });
}

export function useMemoryEvolution(id: string | null) {
  return useQuery({
    queryKey: ['memory-evolution', id],
    queryFn: () => memoriesApi.evolutionHistory(id!),
    enabled: !!id,
  });
}

export function useMemoryLineage(id: string | null) {
  return useQuery({
    queryKey: ['memory-lineage', id],
    queryFn: () => memoriesApi.lineage(id!),
    enabled: !!id,
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => memoriesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories'] }),
  });
}

export function useArchiveMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => memoriesApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories'] }),
  });
}

/* ── Pattern hooks ── */
export function usePatterns(limit = 20) {
  return useQuery({
    queryKey: ['patterns', limit],
    queryFn: () => patternsApi.list({ limit }),
  });
}

export function usePattern(id: string | null) {
  return useQuery({
    queryKey: ['pattern', id],
    queryFn: () => patternsApi.get(id!),
    enabled: !!id,
  });
}

export function usePatternTimeline(id: string | null) {
  return useQuery({
    queryKey: ['pattern-timeline', id],
    queryFn: () => patternsApi.timeline(id!),
    enabled: !!id,
  });
}

/* ── Reflection hooks ── */
export function useReflections(limit = 20) {
  return useQuery({
    queryKey: ['reflections', limit],
    queryFn: () => reflectionsApi.list({ limit }),
  });
}

export function useReflection(id: string | null) {
  return useQuery({
    queryKey: ['reflection', id],
    queryFn: () => reflectionsApi.get(id!),
    enabled: !!id,
  });
}

export function useTriggerReflection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reflectionsApi.trigger(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reflections'] }),
  });
}

/* ── Blind Spot hooks ── */
export function useBlindSpots(limit = 20) {
  return useQuery({
    queryKey: ['blind-spots', limit],
    queryFn: () => blindSpotsApi.list({ limit }),
  });
}

export function useBlindSpot(id: string | null) {
  return useQuery({
    queryKey: ['blind-spot', id],
    queryFn: () => blindSpotsApi.get(id!),
    enabled: !!id,
  });
}

export function useAnalyzeBlindSpots() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => blindSpotsApi.analyze(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['blind-spots'] }),
  });
}

/* ── Library hooks ── */
export function useBooks(limit = 20) {
  return useQuery({
    queryKey: ['books', limit],
    queryFn: () => libraryApi.list({ limit }),
  });
}

export function useBook(id: string | null) {
  return useQuery({
    queryKey: ['book', id],
    queryFn: () => libraryApi.get(id!),
    enabled: !!id,
  });
}

export function useUploadBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; author?: string; content: string; filename: string }) =>
      libraryApi.upload(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['books'] }),
  });
}

export function useDeleteBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => libraryApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['books'] }),
  });
}

export function useReindexBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => libraryApi.reindex(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['books'] }),
  });
}

export function useBookProgress(id: string | null) {
  return useQuery({
    queryKey: ['book-progress', id],
    queryFn: () => libraryApi.progress(id!),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? 2000 : false),
  });
}

export function useBookProfile(bookId: string | null) {
  return useQuery({
    queryKey: ['book-profile', bookId],
    queryFn: () => libraryApi.getProfile(bookId!),
    enabled: !!bookId,
  });
}

export function useRegenerateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bookId: string) => libraryApi.regenerateProfile(bookId),
    onSuccess: (_data, bookId) => {
      qc.invalidateQueries({ queryKey: ['book-profile', bookId] });
    },
  });
}

export function useAddBookText() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ bookId, content }: { bookId: string; content: string }) =>
      libraryApi.addText(bookId, content),
    onSuccess: (_data, { bookId }) => {
      qc.invalidateQueries({ queryKey: ['books'] });
      qc.invalidateQueries({ queryKey: ['book-profile', bookId] });
    },
  });
}

/* ── Jobs hooks ── */
export function useJob(id: string | null) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.get(id!),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === 'running' || query.state.data?.status === 'queued' ? 3000 : false),
  });
}

export function useQueueStatus() {
  return useQuery({
    queryKey: ['queue-status'],
    queryFn: jobsApi.queueStatus,
    refetchInterval: 5000,
  });
}

export function useWorkers() {
  return useQuery({
    queryKey: ['workers'],
    queryFn: jobsApi.workers,
    refetchInterval: 5000,
  });
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsApi.retry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job'] }),
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job'] }),
  });
}

/* ── Dashboard hooks ── */
export function useRuntimeStatus() {
  return useQuery({
    queryKey: ['runtime-status'],
    queryFn: dashboardApi.status,
    refetchInterval: 10000,
  });
}

export function useExecutionHistory(limit = 20) {
  return useQuery({
    queryKey: ['execution-history', limit],
    queryFn: () => dashboardApi.executionHistory(limit),
  });
}
