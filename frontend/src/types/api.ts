/* ── Domain types matching backend Pydantic models ── */

export interface User {
  id: string;
  email: string;
  role: string;
  display_name?: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  topic?: string | null;
  status: string;
  message_count: number;
  created_at: string;
  updated_at?: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sequence_number: number;
  token_count?: number | null;
  created_at: string;
}

export interface Memory {
  id: string;
  user_id: string;
  type: string;
  content: string;
  confidence: number;
  source_message_ids: string[];
  superseded_by?: string | null;
  status: string;
  embedding_version: number;
  evolution_version?: number;
  parent_memory_id?: string | null;
  confidence_history?: Record<string, number>;
  importance_history?: Record<string, number>;
  last_evolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Pattern {
  id: string;
  user_id: string;
  description: string;
  strength: number;
  evidence_count: number;
  status: string;
  first_detected_at: string;
  created_at: string;
  updated_at: string;
}

export interface Reflection {
  id: string;
  user_id: string;
  title: string;
  narrative: string;
  period_start: string;
  period_end: string;
  status: string;
  evidence_snapshot: Record<string, unknown>[];
  created_at: string;
}

export interface BlindSpot {
  id: string;
  user_id: string;
  content: string;
  source_agent: string;
  evidence_ids: string[];
  status: string;
  acknowledged_at?: string | null;
  created_at: string;
}

export interface Book {
  id: string;
  user_id: string;
  title: string;
  author?: string;
  source_format: string;
  status: string;
  chunk_count: number;
  indexed_at?: string | null;
  created_at: string;
}

export interface EpistemicProfile {
  id: string;
  book_id: string;
  tradition: string;
  framework: string;
  discipline: string;
  evidence_level: string;
  reasoning_style: string;
  authority: string;
  primary_topics: string[];
  secondary_topics: string[];
  supported_questions: string[];
  unsupported_questions: string[];
  claim_types: string[];
  limitations: Array<{ description: string; severity: string; affected_domains?: string[] }>;
  scope_boundary: { included_topics: string[]; excluded_topics: string[]; overlap_notes: string[] };
  citation_policy: { required: boolean; format: string; min_confidence: number };
  source_reliability: { score: number; basis: string };
  language: string;
}

export interface RegenerateProfileResult {
  profile_id: string;
  book_id: string;
  framework: string;
  discipline: string;
  evidence_level: string;
  reasoning_style: string;
  is_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  duration_ms: number;
}

export interface Chapter {
  id: string;
  book_id: string;
  title: string;
  sequence_number: number;
  page_start?: number;
  page_end?: number;
}

export interface BookChunk {
  id: string;
  book_id: string;
  chapter_id: string;
  content: string;
  sequence_number: number;
  token_count: number;
  section_heading?: string;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  priority: string;
  attempt: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result?: Record<string, unknown>;
  error?: string;
  duration_ms?: number;
}

export interface WorkerStatus {
  worker_id: string;
  hostname: string;
  pid: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  status: string;
}

export interface QueueStatus {
  depth: number;
  throughput_per_second: number;
  success_rate: number;
  retry_rate: number;
  avg_latency_ms: number;
}

export interface RuntimeStatus {
  status: string;
  active_executions: number;
  uptime_seconds: number;
  version: string;
}

export interface ExecutionPlan {
  id: string;
  conversation_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface ExecutionRecord {
  id: string;
  conversation_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface EvolutionEvent {
  event_type: string;
  old_confidence?: number;
  new_confidence?: number;
  old_importance?: number;
  new_importance?: number;
  detail?: string;
  created_at: string;
}

export interface MemoryLineage {
  child_id: string;
  relation: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  has_more: boolean;
}

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: unknown[];
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}
