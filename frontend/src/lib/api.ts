import { api } from '@/lib/api-client';
import type {
  Book,
  CognitiveAnalysisResponse,
  Conversation,
  EpistemicProfile,
  ExecutionRecord,
  Job,
  MemoConsolidation,
  MemoEpisode,
  MemoKGNode,
  MemoKGEdge,
  MemoKnowledgeGraph,
  MemoSemantic,
  MemoVersion,
  MemoWorking,
  Memory,
  Message,
  PaginatedResponse,
  Pattern,
  QueueStatus,
  Reflection,
  RegenerateProfileResult,
  User,
  WorkerStatus,
  EvolutionEvent,
  MemoryLineage,
  RuntimeStatus,
} from '@/types/api';

/* ── Auth ── */
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/api/v1/auth/login', { email, password }),
  register: (email: string, password: string, display_name: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/api/v1/auth/register', { email, password, display_name }),
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/api/v1/auth/refresh', { refresh_token }),
  logout: () => api.post('/api/v1/auth/logout'),
  me: () => api.get<User>('/api/v1/users/me'),
  updateProfile: (data: { display_name?: string }) =>
    api.patch<User>('/api/v1/users/me', data),
  stats: () => api.get<Record<string, unknown>>('/api/v1/users/me/stats'),
};

/* ── Conversations ── */
export const conversationsApi = {
  list: (params?: { limit?: number; cursor?: string }) =>
    api.get<{ data: Conversation[]; total: number; has_more: boolean }>('/api/v1/conversations', params as Record<string, string>),
  get: (id: string) => api.get<Conversation>(`/api/v1/conversations/${id}`),
  create: (title: string, topic?: string) =>
    api.post<Conversation>('/api/v1/conversations', { title, topic }),
  update: (id: string, data: { title?: string; topic?: string }) =>
    api.patch(`/api/v1/conversations/${id}`, data),
  archive: (id: string) =>
    api.post(`/api/v1/conversations/${id}/archive`),
  messages: (id: string, params?: { limit?: number }) =>
    api.get<{ data: Message[]; total: number; has_more: boolean }>(`/api/v1/conversations/${id}/messages`, params as Record<string, string>),
  sendMessage: (id: string, content: string) =>
    api.post<Message>(`/api/v1/conversations/${id}/messages`, { content }),
};

/* ── Runtime (streaming) ── */
export const runtimeApi = {
  sendMessage: (content: string, conversation_id?: string) =>
    api.post<Message>('/api/v1/runtime/message', { content, conversation_id }),
  status: () => api.get<RuntimeStatus>('/api/v1/runtime/status'),
  executions: (params?: { limit?: number }) =>
    api.get<{ data: ExecutionRecord[]; total: number; has_more: boolean }>('/api/v1/runtime/executions', params as Record<string, string>),
};

/* ── Memories ── */
export const memoriesApi = {
  list: (params?: { limit?: number; cursor?: string }) =>
    api.get<PaginatedResponse<Memory>>('/api/v1/memories', params as Record<string, string>),
  search: (query: string) =>
    api.post<{ data: Memory[] }>('/api/v1/memories/search', { query }),
  get: (id: string) => api.get<Memory>(`/api/v1/memories/${id}`),
  delete: (id: string) => api.delete(`/api/v1/memories/${id}`),
  archive: (id: string) => api.post(`/api/v1/memories/${id}/archive`),
  evolutionHistory: (id: string) =>
    api.get<EvolutionEvent[]>(`/api/v1/memories/${id}/evolution-history`),
  lineage: (id: string) =>
    api.get<{ ancestors: MemoryLineage[]; descendants: MemoryLineage[] }>(`/api/v1/memories/${id}/lineage`),
};

/* ── Patterns ── */
export const patternsApi = {
  list: (params?: { limit?: number; status?: string }) =>
    api.get<PaginatedResponse<Pattern>>('/api/v1/patterns', params as Record<string, string>),
  get: (id: string) => api.get<Pattern>(`/api/v1/patterns/${id}`),
  timeline: (id: string) =>
    api.get<{ data: Record<string, unknown>[] }>(`/api/v1/patterns/${id}/timeline`),
};

/* ── Reflections ── */
export const reflectionsApi = {
  list: (params?: { limit?: number }) =>
    api.get<PaginatedResponse<Reflection>>('/api/v1/reflections', params as Record<string, string>),
  get: (id: string) => api.get<Reflection>(`/api/v1/reflections/${id}`),
  trigger: () => api.post<Reflection>('/api/v1/reflections/trigger'),
};

/* ── Blind Spots ── */
export const blindSpotsApi = {
  list: (params?: { limit?: number; category?: string }) =>
    api.get<PaginatedResponse<import('@/types/api').BlindSpot>>('/api/v1/blind-spots', params as Record<string, string>),
  get: (id: string) => api.get<import('@/types/api').BlindSpot>(`/api/v1/blind-spots/${id}`),
  analyze: () => api.post<{ id: string; status: string }>('/api/v1/blind-spots/analyze'),
};

/* ── Library ── */
export const libraryApi = {
  list: (params?: { limit?: number }) =>
    api.get<PaginatedResponse<Book>>('/api/v1/library/books', params as Record<string, string>),
  get: (id: string) => api.get<Book>(`/api/v1/library/books/${id}`),
  upload: (data: { title: string; author?: string; content: string; filename: string }) =>
    api.post<{ id: string; status: string }>('/api/v1/library/books', data),
  delete: (id: string) => api.delete(`/api/v1/library/books/${id}`),
  reindex: (id: string) => api.post(`/api/v1/library/books/${id}/reindex`),
  progress: (id: string) => api.get<{ status: string; total_chunks: number; processed: number }>(`/api/v1/library/books/${id}/progress`),
  getProfile: (id: string) => api.get<EpistemicProfile>(`/api/v1/library/books/${id}/profile`),
  regenerateProfile: (id: string) => api.post<RegenerateProfileResult>(`/api/v1/library/books/${id}/regenerate-profile`),
  addText: (id: string, content: string, generateProfile = true) =>
    api.post<{ book_id: string; chunks_created: number; total_words: number; profile: RegenerateProfileResult | null }>(
      `/api/v1/library/books/${id}/text`, { content, generate_profile: generateProfile },
    ),
};

/* ── Jobs ── */
export const jobsApi = {
  enqueue: (job_type: string, payload: Record<string, unknown>, priority?: string) =>
    api.post<{ job_id: string; status: string }>('/api/v1/jobs', { job_type, payload, priority: priority || 'normal' }),
  get: (id: string) => api.get<Job>(`/api/v1/jobs/${id}`),
  retry: (id: string) => api.post(`/api/v1/jobs/${id}/retry`),
  cancel: (id: string) => api.post(`/api/v1/jobs/${id}/cancel`),
  queueStatus: () => api.get<QueueStatus>('/api/v1/queue/status'),
  workers: () => api.get<WorkerStatus[]>('/api/v1/workers'),
};

/* ── Runtime Dashboard ── */
export const dashboardApi = {
  status: () => api.get<RuntimeStatus>('/api/v1/runtime/status'),
  executionHistory: (limit?: number) =>
    runtimeApi.executions({ limit: limit || 20 }),
};

/* ── COG (Cognitive Architecture) ── */
export const cogApi = {
  analyze: (data: { user_id: string; messages: { role: string; content: string }[]; language?: string }) =>
    api.post<CognitiveAnalysisResponse>('/api/v1/cog/analyze', data),
  health: () => api.get<{ status: string; modules: number; version: string }>('/api/v1/cog/health'),
};

/* ── MEMO (Memory Architecture) ── */
export const memoApi = {
  health: () => api.get<{ status: string; module: string; timestamp: string }>('/api/v1/memo/health'),

  // Episodes
  createEpisode: (data: { title: string; summary?: string; episode_type?: string; state?: string; confidence?: number; importance?: number; outcome?: string }) =>
    api.post<MemoEpisode>('/api/v1/memo/episodes', data),
  listEpisodes: (params?: { state?: string; limit?: number }) =>
    api.get<{ data: MemoEpisode[]; total: number }>('/api/v1/memo/episodes', params as Record<string, string>),

  // Semantic memories
  createSemantic: (data: { knowledge_statement: string; category?: string; confidence?: number; importance?: number; temporal_stability?: string }) =>
    api.post<MemoSemantic>('/api/v1/memo/semantic', data),
  listSemantic: (params?: { category?: string; limit?: number }) =>
    api.get<{ data: MemoSemantic[]; total: number }>('/api/v1/memo/semantic', params as Record<string, string>),

  // Working memory
  createWorking: (data: { source_memory_id?: string; activation_reason?: string; activation_score?: number; priority_score?: number }) =>
    api.post<MemoWorking>('/api/v1/memo/working', data),
  listWorking: (params?: { status?: string; limit?: number }) =>
    api.get<{ data: MemoWorking[]; total: number }>('/api/v1/memo/working', params as Record<string, string>),

  // Knowledge graph
  createKGNode: (data: { label: string; category: string; layer?: string; properties?: Record<string, unknown>; confidence?: number }) =>
    api.post<MemoKGNode>('/api/v1/memo/graph/nodes', data),
  createKGEdge: (data: { source_node_id: string; target_node_id: string; relationship?: string; weight?: number; confidence?: number }) =>
    api.post<MemoKGEdge>('/api/v1/memo/graph/edges', data),
  getKnowledgeGraph: (params?: { category?: string }) =>
    api.get<MemoKnowledgeGraph>('/api/v1/memo/graph', params as Record<string, string>),

  // Consolidation
  consolidate: (data: { target_memory_id: string; evidence_summary?: string; confidence_before?: number; confidence_after?: number; decision?: string; consolidation_level?: string }) =>
    api.post<MemoConsolidation>('/api/v1/memo/consolidate', data),
  listConsolidations: (params?: { decision?: string; limit?: number }) =>
    api.get<{ data: MemoConsolidation[]; total: number }>('/api/v1/memo/consolidate', params as Record<string, string>),

  // Retrieval
  retrieve: (data: { memory_type?: string; limit?: number }) =>
    api.post<{ data: { id: string; memory_id: string; memory_type: string; final_score: number; strategy_used: string }[]; total: number }>('/api/v1/memo/retrieve', data),

  // Ranking
  rank: (data: { target_memory_id: string; task_profile?: string }) =>
    api.post<{ id: string; target_memory_id: string; overall_score: number; task_profile: string }>('/api/v1/memo/rank', data),

  // Forgetting
  forget: (data: { affected_memory_ids?: string[]; compression_strategy?: string; reason?: string }) =>
    api.post<{ id: string; recoverability_status: string }>('/api/v1/memo/forget', data),

  // Versioning
  listVersions: (params?: { memory_id?: string; limit?: number }) =>
    api.get<{ data: MemoVersion[]; total: number }>('/api/v1/memo/versions', params as Record<string, string>),
};

/* ── Health ── */
export const healthApi = {
  check: () => api.get<{ status: string }>('/api/v1/health'),
  ready: () => api.get<{ status: string; checks: Record<string, string> }>('/api/v1/ready'),
  metrics: () => fetch('/api/v1/metrics').then(r => r.text()),
};

/* ── Wizard ── */
export const wizardApi = {
  status: () => api.get<{ current_step: string; completed_steps: string[]; is_complete: boolean; steps: any[] }>('/api/v1/wizard/status'),
  validateLLM: () => api.post<{ valid: boolean; provider: string | null }>('/api/v1/wizard/validate-llm', {}),
  validateEmbeddings: () => api.post<{ valid: boolean; provider: string | null }>('/api/v1/wizard/validate-embeddings', {}),
  validateStorage: () => api.post<{ valid: boolean; provider: string | null }>('/api/v1/wizard/validate-storage', {}),
  runFullCheck: () => api.post<{ checks: Record<string, { valid: boolean; provider?: string }>; all_healthy: boolean }>('/api/v1/wizard/run-full-check', {}),
};

/* ── Diagnostics ── */
export const diagnosticsApi = {
  check: () => api.get<{ status: string; checks: Record<string, { status: string; provider?: string }> }>('/api/v1/diagnostics'),
  metrics: () => fetch('/api/v1/diagnostics/metrics').then(r => r.text()),
};
