# Android local data path

The Capacitor app stores conversations, messages, pinned facts, and older user
excerpts in the WebView's IndexedDB database (`ayeneh-local`). The app does not
need a backend to create or read those records. Android automatic app backup is
disabled. Uninstalling the app or clearing its data removes the database.

Settings offers JSON export and import. On Android, export writes a temporary
cache file and opens the native share sheet; the user must save that file in a
location they control. Import merges records by ID and preserves full message
text. Backups are unencrypted JSON, so they should be stored privately.

Before each response request, the app selects recent dialogue (up to roughly
800 estimated tokens) and a small amount of older context (up to roughly 500
estimated tokens). Older context comes from exact, on-device excerpts and a
word index, including Persian normalization. These estimates are deliberately
conservative; the provider's actual tokenizer determines billed tokens. The
full conversation remains on the device. Extractive excerpts are not semantic
LLM summaries and never overwrite original messages.

The runtime streaming endpoint accepts `conversation_history` and
`memory_context` from the app. It no longer reads or writes chat messages at a
hard-coded SQLite path. The current Python pipeline still needs a running
service for cloud model responses, and other legacy screens still call that
service. A serverless model gateway and migration of those screens are separate
work; this local data change alone does not make the entire app server-free.
