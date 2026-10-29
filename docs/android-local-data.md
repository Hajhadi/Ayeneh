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
service for web responses, and other legacy screens still call that service.
On Android, Chat can instead call an OpenAI-compatible cloud model directly.
The API key is encrypted by Android Keystore and stays in the app's private
storage. JavaScript sends only the prompt to the native bridge; the bridge adds
the key to the HTTPS request. Chat data backups deliberately omit model keys.
Custom URLs should be trusted because the selected provider receives the key
and the prompt. A compromised or rooted device can still expose runtime secrets.
The legacy library, pattern, and reflection screens have not yet been migrated
to device-only operation.

Debug APKs use `ir.ayeneh.app.preview` so they can be installed beside an older
`ir.ayeneh.app` APK with a different signing key. The two apps have separate
local databases. A stable signing key is required for future in-place updates
that preserve the installed app's data. The Preview workflow uses a private
PKCS#12 key from GitHub Actions secrets. A local copy is kept in the ignored
`.signing/` folder; back up that folder privately if you need to sign an APK
outside GitHub Actions. Never commit its contents.
