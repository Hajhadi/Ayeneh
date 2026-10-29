'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { PageLayout } from '@/components/layout/page-layout';
import { useChatStore } from '@/stores/chat-store';
import {
  getLocalDigest, listLocalDigests, removePinnedNote, searchLocalHistory,
  type MemoryExcerpt,
} from '@/lib/local-data';
import type { Message } from '@/types/conversation';

export default function MemoriesPage() {
  const router = useRouter();
  const setActiveConversation = useChatStore((state) => state.setActiveConversation);
  const [pinned, setPinned] = useState<MemoryExcerpt[]>([]);
  const [digest, setDigest] = useState<MemoryExcerpt[]>([]);
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<Message[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getLocalDigest('pinned'), listLocalDigests()])
      .then(([notes, excerpts]) => { setPinned(notes); setDigest(excerpts); })
      .catch((reason) => setError(String(reason)));
  }, []);

  useEffect(() => {
    if (!query.trim()) { setMatches([]); return; }
    let active = true;
    searchLocalHistory(query, 30)
      .then((items) => { if (active) setMatches(items); })
      .catch((reason) => { if (active) setError(String(reason)); });
    return () => { active = false; };
  }, [query]);

  function openConversation(id: string) {
    setActiveConversation(id);
    router.push('/chat');
  }

  return (
    <PageLayout title="Memories" description="Private notes and excerpts saved on this device">
      <div className="mx-auto max-w-3xl space-y-6">
        <input value={query} onChange={(event) => setQuery(event.target.value)}
          aria-label="Search local history" placeholder="Search your past conversations"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-violet-400/50" />
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}

        {query.trim() ? (
          <section>
            <h2 className="mb-3 text-sm font-semibold text-white/70">Matching conversations</h2>
            {matches.length === 0 && <p className="text-sm text-white/40">No matches found on this device.</p>}
            <div className="space-y-2">
              {matches.map((item) => <button key={item.id} onClick={() => openConversation(item.conversation_id)}
                className="w-full rounded-xl border border-white/10 bg-white/5 p-4 text-left transition-colors hover:bg-white/10">
                <span className="text-xs text-violet-300">{item.role} · {new Date(item.created_at).toLocaleDateString()}</span>
                <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-sm text-white/80">{item.content}</p>
              </button>)}
            </div>
          </section>
        ) : (
          <>
            <section>
              <h2 className="mb-1 text-sm font-semibold text-white/70">Pinned facts</h2>
              <p className="mb-3 text-xs text-white/40">You control these notes in Settings. Ayeneh uses a small selection in each reply.</p>
              {pinned.length === 0 && <p className="text-sm text-white/40">No pinned facts yet.</p>}
              <div className="space-y-2">
                {pinned.map((item) => <div key={item.id} className="flex gap-3 rounded-xl border border-violet-400/15 bg-violet-400/5 p-4">
                  <p className="flex-1 whitespace-pre-wrap text-sm text-white/80">{item.content}</p>
                  <button className="text-xs text-red-300" onClick={async () => {
                    try {
                      await removePinnedNote(item.id);
                      setPinned((notes) => notes.filter((note) => note.id !== item.id));
                    } catch (reason) { setError(String(reason)); }
                  }}>Remove</button>
                </div>)}
              </div>
            </section>

            <section>
              <h2 className="mb-1 text-sm font-semibold text-white/70">Conversation highlights</h2>
              <p className="mb-3 text-xs text-white/40">Short, exact excerpts from older messages. Full conversations stay available in Chat.</p>
              {digest.length === 0 && <p className="text-sm text-white/40">Highlights appear as conversations grow.</p>}
              <div className="space-y-2">
                {digest.map((item) => <button key={item.id} onClick={() => openConversation(item.conversation_id)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 p-4 text-left transition-colors hover:bg-white/10">
                  <span className="text-xs text-violet-300">{new Date(item.created_at).toLocaleDateString()}</span>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-white/80">{item.content}</p>
                </button>)}
              </div>
            </section>
          </>
        )}
      </div>
    </PageLayout>
  );
}
