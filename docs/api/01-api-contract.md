# API Contract — Ayeneh

---

## 1. API Design Principles

- **Resource-oriented**: Every domain concept maps to a resource with standard operations.
- **Consistent conventions**: Naming, pagination, filtering, error formats follow uniform rules.
- **Stateless**: Every request contains all information needed to process it.
- **Idempotent writes**: All mutating operations support idempotency keys.
- **Versioned**: API versions in URL path. Breaking changes require a new version.
- **Discoverable**: Responses include `links` objects for related resources.
- **Secure by default**: All endpoints require authentication unless marked public.

---

## 2. Authentication Model

**Mechanism**: Bearer token (JWT) in `Authorization` header.

**Token lifecycle**: Issued on login. Contains `user_id`, `exp`, `iat`, `scope`. Refreshed via opaque refresh token. Revoked on logout or deactivation.

**Public endpoints**: Only `/health` and `/auth/login` are unauthenticated.

**Service-to-service**: Internal services use separate service tokens with elevated scope.

---

## 3. Authorization Model

**Principle**: Every resource is scoped to a single User. No cross-user access.

**Mechanism**: `user_id` from JWT injected into every request. All queries filtered by `user_id`.

**Roles**:
- **User**: Full access to own data.
- **Administrator**: System-level operations (prompts, health). No access to User data.

---

## 4. API Versioning Strategy

**Versioning**: URL path: `/api/v1/...`, `/api/v2/...`.

**Breaking changes**: New major version (renamed/removed fields, changed structure).

**Non-breaking**: New fields, parameters, endpoints added to current version.

**Deprecation**: `Deprecation` header + sunset date. Removed after 6 months. Current version: `v1`.

---

## 5. Resource Catalog

| Resource | Path Prefix | Description |
|---|---|---|
| **User** | `/api/v1/user` | Profile and preferences. |
| **Sessions** | `/api/v1/sessions` | Interaction periods. |
| **Conversations** | `/api/v1/conversations` | Bounded topical interactions. |
| **Messages** | `/api/v1/conversations/{id}/messages` | Atomic utterances (sub-resource). |
| **Memories** | `/api/v1/memories` | Extracted structured knowledge. |
| **Insights** | `/api/v1/insights` | Granular observations (read-only). |
| **Patterns** | `/api/v1/patterns` | Cognitive tendencies (read-only). |
| **Reflections** | `/api/v1/reflections` | Narrative documents. |
| **Observations** | `/api/v1/observations` | Evidence-based statements. |
| **Themes** | `/api/v1/themes` | Recurring subjects. |
| **Library** | `/api/v1/library` | Knowledge base overview. |
| **Books** | `/api/v1/library/books` | Imported knowledge sources. |
| **Search** | `/api/v1/search` | Unified search. |
| **Runtime** | `/api/v1/runtime` | Conversation processing. |
| **Health** | `/api/v1/health` | System health (public). |
| **Prompts** | `/api/v1/admin/prompts` | Template management (admin). |

---

## 6. Operations per Resource

| Resource | Method | Path | Description |
|---|---|---|---|
| **User** | `GET` | `/user` | Get profile. |
| | `PATCH` | `/user` | Update preferences. |
| | `POST` | `/user/export` | Data export (async). |
| | `DELETE` | `/user` | Delete account + all data. |
| **Sessions** | `GET` | `/sessions` | List (paginated, by recency). |
| | `GET` | `/sessions/{id}` | Get details. |
| | `POST` | `/sessions/{id}/close` | End session. |
| **Conversations** | `GET` | `/conversations` | List (paginated, by status). |
| | `GET` | `/conversations/{id}` | Get with metadata. |
| | `POST` | `/conversations` | Start new (also implicit). |
| | `POST` | `/conversations/{id}/close` | Close. |
| | `POST` | `/conversations/{id}/summarize` | Generate summary. |
| **Messages** | `GET` | `/conversations/{id}/messages` | List (paginated, chronological). |
| | `GET` | `/conversations/{id}/messages/{msgId}` | Get single. |
| **Memories** | `GET` | `/memories` | List (paginated, by type/status). |
| | `GET` | `/memories/{id}` | Get single. |
| | `GET` | `/memories?q=...` | Semantic search. |
| | `POST` | `/memories/{id}/archive` | Soft-archive. |
| **Insights** | `GET` | `/insights` | List (paginated, by type). |
| | `GET` | `/insights/{id}` | Get single. |
| **Patterns** | `GET` | `/patterns` | List (paginated, by status). |
| | `GET` | `/patterns/{id}` | Get with evidence. |
| **Reflections** | `GET` | `/reflections` | List (paginated, by period). |
| | `GET` | `/reflections/{id}` | Get with narrative. |
| | `POST` | `/reflections` | Trigger generation (async). |
| **Observations** | `GET` | `/observations` | List pending + recent. |
| | `GET` | `/observations/{id}` | Get with evidence. |
| | `POST` | `/observations/{id}/acknowledge` | Acknowledge. |
| | `POST` | `/observations/{id}/dismiss` | Dismiss. |
| **Themes** | `GET` | `/themes` | List (paginated). |
| | `GET` | `/themes/{id}` | Get with count. |
| | `PATCH` | `/themes/{id}` | Rename/update. |
| **Library** | `GET` | `/library` | Stats overview. |
| **Books** | `GET` | `/library/books` | List (paginated, by status). |
| | `GET` | `/library/books/{id}` | Get with metadata. |
| | `POST` | `/library/books` | Import (file or URL). |
| | `DELETE` | `/library/books/{id}` | Remove + chunks. |
| | `GET` | `/library/books/{id}/chapters` | List chapters. |
| | `GET` | `/library/books/{id}/chunks` | List chunks (paginated). |
| **Search** | `GET` | `/search?q=...` | Unified (memories + library). |
| | `GET` | `/search/library?q=...` | Library only. |
| **Runtime** | `POST` | `/runtime/message` | Send message, get response. |
| | `POST` | `/runtime/message/stream` | Send message, stream SSE. |
| **Health** | `GET` | `/health` | Health check (no auth). |
| **Admin** | `GET` | `/admin/prompts` | List templates. |
| | `GET` | `/admin/prompts/{id}` | Get with history. |
| | `POST` | `/admin/prompts` | Create version. |
| | `POST` | `/admin/prompts/{id}/activate` | Set active. |

Note: Messages created through Runtime. Memories created by MemoryAgent. Insights/Patterns read-only for user.

---

## 7. Request/Response Conventions

**Headers**:
- `Content-Type: application/json` (requests with body).
- `Authorization: Bearer <token>` (authenticated requests).
- `X-Idempotency-Key: <uuid>` (mutating requests).

**Response envelope**:
- **Single resource**: `{ "data": {...}, "meta": {...}, "links": {...} }`
- **Collection**: `{ "data": [...], "meta": { "total_count", "page_size", "has_next", "next_cursor" } }`
- **Error**: `{ "data": null, "error": { "code", "message", "details" } }`
- **Async accepted**: `{ "data": { "id": "...", "status": "processing" } }`

**Conventions**: Null fields omitted. Timestamps: ISO 8601 UTC. IDs: UUID v7.

---

## 8. Pagination Strategy

**Cursor-based** for large collections, **offset-based** for small.

**Parameters**: `cursor` (opaque string), `page_size` (default 20, max 100).

**Response**: `total_count`, `has_next`, `next_cursor`, `has_prev`, `prev_cursor`.

**Default sort**: `created_at` descending. Configurable via `sort` parameter.

---

## 9. Filtering & Sorting

**Filters**: Query parameters matching field names: `?status=active&type=episodic`.

| Resource | Filters |
|---|---|
| Sessions | `status`, `platform` |
| Conversations | `status`, `topic` |
| Memories | `type`, `status`, `created_after`, `created_before` |
| Patterns | `status` |
| Reflections | `status`, `period_start_after`, `period_start_before` |
| Books | `status`, `source_format` |

**Sorting**: `?sort=-created_at` (desc), `?sort=created_at` (asc). Multiple: `?sort=-strength,created_at`.

**Search**: `?q=<query>` for text/semantic search.

---

## 10. Error Model

```json
{
  "data": null,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Conversation not found.",
    "details": [{ "field": "conversation_id", "reason": "No conversation with this ID." }]
  }
}
```

| Code | HTTP | Description |
|---|---|---|
| `AUTHENTICATION_REQUIRED` | 401 | Missing/invalid token. |
| `AUTHORIZATION_DENIED` | 403 | Insufficient permissions. |
| `RESOURCE_NOT_FOUND` | 404 | Resource does not exist. |
| `VALIDATION_ERROR` | 400 | Request validation failed. |
| `CONFLICT` | 409 | Idempotency key reuse with different body. |
| `RATE_LIMITED` | 429 | Too many requests. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. |
| `SERVICE_UNAVAILABLE` | 503 | Temporary unavailability. |
| `PLANNING_FAILED` | 422 | Runtime could not produce plan. |
| `AGENT_FAILED` | 422 | Agent failed after retries. |

---

## 11. Idempotency Strategy

**Mechanism**: `X-Idempotency-Key` header (UUID) on mutating requests.

**Behavior**: First request processed normally. Same key returns cached response (24h). Different body with same key: `409`. GET requests: naturally idempotent.

**Scope**: Per user + endpoint. Same key, different user: independent.

---

## 12. Rate Limiting

| Category | Limit | Window |
|---|---|---|
| Read (GET) | 200 | per minute |
| Write (POST/PATCH) | 60 | per minute |
| Runtime (message) | 20 | per minute |
| Search | 30 | per minute |
| File upload | 5 | per minute |

**Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

**Exceeded**: `429` with `Retry-After` header.

---

## 13. Streaming Strategy

**Endpoint**: `POST /api/v1/runtime/message/stream`. **Protocol**: SSE.

| Event | When | Data |
|---|---|---|
| `message_start` | Stream begins | `{ "message_id" }` |
| `content_delta` | Text chunk | `{ "delta" }` |
| `message_end` | Complete | `{ "message_id", "metadata" }` |
| `agent_status` | Agent lifecycle | `{ "agent", "status" }` |
| `error` | Error | `{ "code", "message" }` |

**Timeout**: 60s inactivity. Client reconnects with last event ID.

---

## 14. Webhook/Event Strategy (Future)

Not implemented in v1. Designed for extensibility.

**Available events**: `reflection.created`, `observation.created`, `book.indexed`, `memory.created` (opt-in).

**Delivery**: HTTP POST, HMAC-signed, exponential backoff retries (3 attempts over 24h).

---

## 15. API Lifecycle

| Phase | Description |
|---|---|
| **Design** | Contract reviewed. No implementation. |
| **Development** | Implementation. Contract tests validate compliance. |
| **Beta** | Available with `beta` header. May change without version bump. |
| **Stable** | Published. Semantic versioning applies. |
| **Deprecated** | `Deprecation` header. Sunset in 6 months. |
| **Removed** | Endpoint removed. New version for equivalent. |

---

## 16. Future Expansion

**New resources**: Under `/api/v{version}/...`. No existing endpoints modified.

**New operations**: Added to existing resources. Non-breaking.

**New parameters**: Added to existing endpoints. Non-breaking.

**Breaking changes**: New API version. Old version maintained for deprecation period.

**GraphQL**: If query flexibility needed, added alongside REST. Resource catalog already structured for it.
