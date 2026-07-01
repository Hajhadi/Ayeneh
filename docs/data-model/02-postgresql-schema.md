# Physical PostgreSQL Schema — Ayeneh

---

## 1. Database Design Principles

- Every logical entity maps to one PostgreSQL table. No splits.
- All PKs: `UUID v7` (time-ordered). No serials.
- All names: `snake_case`. No ORM artifacts.
- JSONB for semi-structured data (preferences, metadata, evidence snapshots, plan steps). Structured columns when query patterns are known.
- All timestamps: `TIMESTAMPTZ` (UTC internally).
- Soft delete via nullable `deleted_at`. Queries filter `WHERE deleted_at IS NULL`.
- No foreign keys across contexts. Cross-context references are UUID columns without FK constraints.

---

## 2. Schema Organization

Single `public` schema. Tables grouped by context prefix:

| Context | Tables |
|---|---|
| Identity | `users` |
| Conversation | `sessions`, `conversations`, `messages` |
| Memory | `memories`, `insights`, `themes`, `theme_entities` |
| Pattern Analysis | `patterns`, `pattern_evidence`, `pattern_relations`, `habits` |
| Reflection | `reflections`, `observations` |
| Knowledge | `books`, `book_chapters`, `book_chunks` |
| Infrastructure | `prompt_templates`, `execution_plans`, `agent_runs`, `execution_plan_templates` |

All tables: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. User-owned tables: `deleted_at TIMESTAMPTZ NULL`.

---

## 3. Table Catalog

### Domain Tables

| Table | PK | Foreign Keys | Key Columns | Constraints |
|---|---|---|---|---|
| `users` | `id UUID` | — | `email VARCHAR(255) NOT NULL`, `display_name VARCHAR(100)`, `status VARCHAR(20) DEFAULT 'active'`, `preferences JSONB DEFAULT '{}'`, `last_active_at TIMESTAMPTZ`, `deleted_at` | `UNIQUE(email) WHERE deleted_at IS NULL` |
| `sessions` | `id UUID` | `user_id → users` | `started_at TIMESTAMPTZ NOT NULL`, `ended_at TIMESTAMPTZ`, `duration_seconds INT`, `platform VARCHAR(50)`, `device VARCHAR(100)`, `deleted_at` | `ended_at >= started_at` |
| `conversations` | `id UUID` | `user_id → users`, `session_id → sessions` | `topic VARCHAR(255)`, `status VARCHAR(20) DEFAULT 'active'`, `title VARCHAR(255)`, `summary TEXT`, `message_count INT DEFAULT 0`, `started_at`, `ended_at`, `last_activity_at`, `deleted_at` | `ended_at >= started_at` |
| `messages` | `id UUID` | `conversation_id → conversations`, `user_id → users` | `role VARCHAR(20) NOT NULL`, `content TEXT NOT NULL`, `sequence_number INT NOT NULL`, `token_count INT`, `emotion JSONB`, `deleted_at` | `UNIQUE(conversation_id, sequence_number)`, `role IN ('user','assistant','system')` |
| `memories` | `id UUID` | `user_id → users` | `type VARCHAR(20) NOT NULL`, `content TEXT NOT NULL`, `confidence REAL DEFAULT 0.5`, `source_message_ids UUID[] DEFAULT '{}'`, `superseded_by UUID`, `status VARCHAR(20) DEFAULT 'active'`, `embedding_version INT DEFAULT 0`, `updated_at`, `deleted_at` | `type IN ('episodic','semantic','pattern','reflection')`, `status IN ('active','superseded','archived')`, `confidence BETWEEN 0 AND 1` |
| `insights` | `id UUID` | `user_id → users` | `type VARCHAR(30) NOT NULL`, `content TEXT NOT NULL`, `confidence REAL DEFAULT 0.5`, `source_message_ids UUID[] DEFAULT '{}'`, `deleted_at` | `confidence BETWEEN 0 AND 1` |
| `themes` | `id UUID` | `user_id → users` | `name VARCHAR(255) NOT NULL`, `description TEXT`, `memory_count INT DEFAULT 0`, `status VARCHAR(20) DEFAULT 'active'`, `updated_at`, `deleted_at` | `UNIQUE(user_id, name) WHERE deleted_at IS NULL` |
| `theme_entities` | `(theme_id, entity_id, entity_type)` | `theme_id → themes` | `entity_type VARCHAR(20) NOT NULL`, `added_at` | `entity_type IN ('memory','insight','pattern')` |
| `patterns` | `id UUID` | `user_id → users` | `description TEXT NOT NULL`, `strength REAL DEFAULT 0.5`, `evidence_count INT DEFAULT 0`, `status VARCHAR(20) DEFAULT 'active'`, `first_detected_at`, `last_updated_at`, `superseded_by UUID`, `deleted_at` | `strength BETWEEN 0 AND 1`, `status IN ('active','weakening','deprecated')` |
| `pattern_evidence` | `(pattern_id, evidence_id, evidence_type)` | `pattern_id → patterns` | `evidence_type VARCHAR(10) NOT NULL`, `added_at` | `evidence_type IN ('insight','memory')` |
| `pattern_relations` | `(pattern_id, related_pattern_id, relation_type)` | `pattern_id → patterns`, `related_pattern_id → patterns` | `relation_type VARCHAR(20) NOT NULL` | `relation_type IN ('supports','contradicts','supersedes')` |
| `habits` | `id UUID` | `user_id → users` | `description TEXT NOT NULL`, `strength REAL DEFAULT 0.5`, `evidence_count INT DEFAULT 0`, `status VARCHAR(20) DEFAULT 'active'`, `first_detected_at`, `last_observed_at`, `deleted_at` | `strength BETWEEN 0 AND 1` |
| `reflections` | `id UUID` | `user_id → users` | `title VARCHAR(255) NOT NULL`, `narrative TEXT NOT NULL`, `period_start TIMESTAMPTZ NOT NULL`, `period_end TIMESTAMPTZ NOT NULL`, `status VARCHAR(20) DEFAULT 'draft'`, `evidence_snapshot JSONB DEFAULT '[]'`, `deleted_at` | `period_end > period_start` |
| `observations` | `id UUID` | `user_id → users` | `content TEXT NOT NULL`, `source_agent VARCHAR(50) NOT NULL`, `evidence_ids JSONB DEFAULT '[]'`, `status VARCHAR(20) DEFAULT 'pending'`, `acknowledged_at TIMESTAMPTZ`, `deleted_at` | `status IN ('pending','acknowledged','dismissed')` |
| `books` | `id UUID` | `user_id → users` | `title VARCHAR(500) NOT NULL`, `author VARCHAR(255)`, `source_format VARCHAR(20) NOT NULL`, `source_url TEXT`, `status VARCHAR(20) DEFAULT 'processing'`, `chunk_count INT DEFAULT 0`, `metadata JSONB DEFAULT '{}'`, `indexed_at TIMESTAMPTZ`, `deleted_at` | `status IN ('processing','ready','failed')` |
| `book_chapters` | `id UUID` | `book_id → books` | `title VARCHAR(500) NOT NULL`, `sequence_number INT NOT NULL`, `page_start INT`, `page_end INT`, `deleted_at` | `UNIQUE(book_id, sequence_number) WHERE deleted_at IS NULL` |
| `book_chunks` | `id UUID` | `book_id → books`, `chapter_id → book_chapters` | `content TEXT NOT NULL`, `sequence_number INT NOT NULL`, `page_start INT`, `page_end INT`, `section_heading VARCHAR(500)`, `token_count INT NOT NULL`, `deleted_at` | `UNIQUE(book_id, sequence_number) WHERE deleted_at IS NULL` |

### Infrastructure Tables

| Table | PK | Foreign Keys | Key Columns | Constraints |
|---|---|---|---|---|
| `prompt_templates` | `id UUID` | — | `task_type VARCHAR(50) NOT NULL`, `version INT NOT NULL`, `content TEXT NOT NULL`, `is_active BOOLEAN DEFAULT false`, `created_by UUID` | `UNIQUE(task_type, version)`, `UNIQUE(task_type) WHERE is_active = true` |
| `execution_plans` | `id UUID` | `user_id → users` | `request_id UUID NOT NULL`, `strategy VARCHAR(20) NOT NULL`, `confidence REAL`, `steps JSONB NOT NULL`, `budget_llm_calls INT`, `budget_time_ms INT`, `status VARCHAR(20) DEFAULT 'created'`, `completed_at TIMESTAMPTZ` | `strategy IN ('rule_based','llm_assisted')` |
| `agent_runs` | `id UUID` | `plan_id → execution_plans` | `step_id VARCHAR(50) NOT NULL`, `agent_name VARCHAR(50) NOT NULL`, `status VARCHAR(20) DEFAULT 'pending'`, `input_summary TEXT`, `output_summary TEXT`, `started_at TIMESTAMPTZ`, `completed_at TIMESTAMPTZ`, `duration_ms INT`, `error_message TEXT`, `retry_count INT DEFAULT 0` | `status IN ('pending','running','completed','failed','skipped')` |
| `execution_plan_templates` | `id UUID` | — | `name VARCHAR(100) NOT NULL UNIQUE`, `description TEXT`, `match_conditions JSONB NOT NULL`, `agent_sequence JSONB NOT NULL`, `input_bindings JSONB DEFAULT '{}'`, `error_strategies JSONB DEFAULT '{}'`, `is_active BOOLEAN DEFAULT true`, `updated_at` | — |

---

## 4. Enum Catalog

All enums are `VARCHAR` with `CHECK` constraints (not native ENUMs) for flexibility:

| Column | Values |
|---|---|
| `users.status` | `active`, `paused`, `deactivated` |
| `conversations.status` | `active`, `closed`, `archived` |
| `messages.role` | `user`, `assistant`, `system` |
| `memories.type` | `episodic`, `semantic`, `pattern`, `reflection` |
| `memories.status` | `active`, `superseded`, `archived` |
| `patterns.status` | `active`, `weakening`, `deprecated` |
| `reflections.status` | `draft`, `published`, `archived` |
| `observations.status` | `pending`, `acknowledged`, `dismissed` |
| `books.status` | `processing`, `ready`, `failed` |
| `theme_entities.entity_type` | `memory`, `insight`, `pattern` |
| `pattern_evidence.evidence_type` | `insight`, `memory` |
| `pattern_relations.relation_type` | `supports`, `contradicts`, `supersedes` |
| `execution_plans.strategy` | `rule_based`, `llm_assisted` |
| `agent_runs.status` | `pending`, `running`, `completed`, `failed`, `skipped` |

---

## 5. JSONB Usage Policy

| Table | Column | Structure | Rule |
|---|---|---|---|
| `users` | `preferences` | `{llm_provider, reflection_cadence, privacy_level}` | Read entire, rarely query inside |
| `books` | `metadata` | `{isbn, page_count, language}` | Read entire |
| `reflections` | `evidence_snapshot` | `[{id, type}, ...]` | Read entire, append |
| `observations` | `evidence_ids` | `[{id, type}, ...]` | Read entire |
| `memories`, `insights` | `source_message_ids` | `[uuid, ...]` | Containment check |
| `execution_plans` | `steps` | `[{step_id, agent, input, ...}]` | Read entire |
| `execution_plan_templates` | `match_conditions`, `agent_sequence`, `input_bindings`, `error_strategies` | Various | Read entire |

Dedicated columns preferred over JSONB when query/filter patterns are known.

---

## 6. Timestamp Policy

- All timestamps: `TIMESTAMPTZ`. UTC stored, displayed in session timezone.
- `created_at`: On insert, never modified. Default `now()`.
- `updated_at`: On insert and every update. Application-layer responsibility.
- `deleted_at`: Nullable. Set on soft-delete only.
- Domain timestamps (`started_at`, `ended_at`, etc.): Set by application logic.

---

## 7. Soft Delete Policy

- `deleted_at` nullable on all user-owned tables. Active: `NULL`. Deleted: timestamp set.
- All queries include `WHERE deleted_at IS NULL` by default.
- Restoration: Set `deleted_at = NULL`.
- Cascade: Soft-deleting `users` → all children. Soft-deleting `books` → chapters + chunks.
- Hard delete: Reserved for retention expiry (`execution_plans`, `agent_runs`) and regulatory requests.
- System tables: `is_active` flag instead of `deleted_at`.

---

## 8. Cascade Rules

| Parent | Child | Physical Delete | Soft Delete |
|---|---|---|---|
| `users` | All children | CASCADE | SET `deleted_at` on all |
| `conversations` | `messages` | CASCADE | SET `deleted_at` |
| `books` | `book_chapters`, `book_chunks` | CASCADE | SET `deleted_at` |
| `book_chapters` | `book_chunks` | CASCADE | SET `deleted_at` |
| `patterns` | `pattern_evidence`, `pattern_relations` | CASCADE | CASCADE (join tables) |
| `themes` | `theme_entities` | CASCADE | CASCADE (join table) |
| `execution_plans` | `agent_runs` | CASCADE | Hard delete (no soft-delete) |

---

## 9. Indexing Strategy (Conceptual)

- **PK indexes**: Automatic on all UUID PKs.
- **FK indexes**: All `*_id` FK columns indexed.
- **Soft delete**: Partial index `WHERE deleted_at IS NULL` on user-owned tables.
- **Unique constraints**: Already create indexes.
- **Query-driven**: `messages(conversation_id, sequence_number)`, `memories(user_id, type, status)`, `patterns(user_id, status)`, `books(user_id, status)`, `execution_plans(user_id, created_at)`.
- **JSONB**: GIN index on `users.preferences` and `execution_plans.steps` if querying inside.
- **Full-text**: GIN on `tsvector` columns for `messages.content`, `memories.content`, `book_chunks.content` (see §11).

---

## 10. Partitioning Strategy

**Partition candidates**: `execution_plans` and `agent_runs` — high-volume, time-series, retention-bound. Range partition on `created_at` (monthly). Old partitions dropped after retention.

**Non-partitioned**: All user-owned domain tables. Volume bounded by user count. Not justified at current scale.

**Future**: If `messages` grows significantly, consider range partition on `created_at` or hash partition on `user_id`.

---

## 11. Full-Text Search Strategy

PostgreSQL `tsvector` + `tsquery` for keyword search.

**Indexed columns**: `messages.content`, `memories.content`, `book_chunks.content`, `insights.content`, `reflections.narrative`.

**Approach**: Generated `tsvector` column (`content_tsv`) via `to_tsvector('english', content)`. GIN index. Query with `@@` operator.

**Language**: English default. Multi-language via per-user preference in `users.preferences`.

**Hybrid**: Combined with vector similarity search (§12) for ranking.

---

## 12. Vector Storage Strategy

Embeddings stored in a dedicated vector database (pgvector or external Qdrant), not as columns in main tables.

**Vector records** reference source by ID and type:

| Source | Vector Record Fields |
|---|---|
| `memories` | `entity_id`, `entity_type: 'memory'`, `embedding`, `model_version` |
| `book_chunks` | `entity_id`, `entity_type: 'book_chunk'`, `embedding`, `model_version` |
| `messages` | `entity_id`, `entity_type: 'message'`, `embedding`, `model_version` |
| `patterns` | `entity_id`, `entity_type: 'pattern'`, `embedding`, `model_version` |

**Index**: HNSW or IVFFlat on embedding column for ANN search.

**Re-embedding**: `memories.embedding_version` tracks staleness. Async re-embedding when version < current model.

---

## 13. Transaction Boundaries

**Principle**: Transactions short. LLM calls, embedding generation outside transactions.

| Operation | Scope |
|---|---|
| Message storage + conversation update | Single transaction |
| Memory creation + insight extraction | Single transaction per batch |
| Pattern update + evidence linkage | Single transaction |
| Reflection creation | Single transaction |
| Book status update | Single transaction |
| Prompt template activation | Single transaction (deactivate old + activate new) |
| Soft-delete cascade | Single transaction |
| Execution plan + agent runs | Separate transactions |

**Isolation**: `READ COMMITTED` (PostgreSQL default). Optimistic locking via `updated_at` where needed.

---

## 14. Concurrency Strategy

**Optimistic locking**: Pattern and Memory updates use `updated_at` as version check. Retry on conflict.

**Pessimistic locking**: `SELECT ... FOR UPDATE` for prompt template activation only (prevent concurrent activation of same task_type).

**Queue-based**: Background jobs process one user at a time per job type. No distributed locking.

**Connection pooling**: Application-level pool (PgBouncer or built-in). No connection-per-request.

---

## 15. Backup & Recovery

- Continuous WAL archiving + daily base backups.
- RPO: Near-zero. RTO: < 1 hour.
- Back up entire database. Retain 30 days.
- Weekly restore test to staging.
- Hard-deleted data recoverable only from backups.

---

## 16. Future Migration Strategy

All changes additive. No destructive migrations without backup.

| Change | Strategy |
|---|---|
| New table | `CREATE TABLE`. No impact. |
| New nullable column | `ALTER TABLE ADD COLUMN ... DEFAULT`. No downtime. |
| New non-nullable column | Add nullable → backfill → set NOT NULL. |
| New index | `CREATE INDEX CONCURRENTLY`. No locks. |
| New constraint | Add not-enforced → validate → enforce. |
| Column type change | New column → backfill → swap → drop old. |
| Drop column | Deprecate → stop read/write → drop next release. |

Migrations numbered sequentially. Forward + backward scripts. Rollback tested. Zero-downtime required.
