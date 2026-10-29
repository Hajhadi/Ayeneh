'use client';

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTheme } from '@/providers/theme-provider';
import { PageLayout } from '@/components/layout/page-layout';
import { Button } from '@/components/ui/button';
import { getApiBase } from '@/lib/api-client';
import { Capacitor } from '@capacitor/core';
import { Directory, Encoding, Filesystem } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { addPinnedNote, exportLocalData, getLocalDigest, importLocalData, removePinnedNote, type MemoryExcerpt } from '@/lib/local-data';
import { ModelProfilesSettings } from '@/components/settings/model-profiles-settings';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState('');
  const [saved, setSaved] = useState(false);
  const [notes, setNotes] = useState<MemoryExcerpt[]>([]);
  const [newNote, setNewNote] = useState('');
  const [dataStatus, setDataStatus] = useState('');

  useEffect(() => {
    setApiUrl(getApiBase());
    getLocalDigest('pinned').then(setNotes).catch((error) => setDataStatus(String(error)));
  }, []);

  async function saveNote() {
    try {
      const note = await addPinnedNote(newNote);
      setNotes((items) => [note, ...items]);
      setNewNote('');
      setDataStatus('Memory saved on this device.');
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : 'Could not save memory');
    }
  }

  async function exportData() {
    try {
      const name = `ayeneh-backup-${new Date().toISOString().slice(0, 10)}.json`;
      const data = await exportLocalData();
      if (Capacitor.isNativePlatform()) {
        const { uri } = await Filesystem.writeFile({
          path: name, data, directory: Directory.Cache, encoding: Encoding.UTF8,
        });
        await Share.share({ title: 'Ayeneh backup', files: [uri], dialogTitle: 'Save your backup' });
      } else {
        const file = new File([data], name, { type: 'application/json' });
        if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: 'Ayeneh backup' });
        } else {
          const url = URL.createObjectURL(file);
          const link = document.createElement('a');
          link.href = url;
          link.download = file.name;
          link.click();
          window.setTimeout(() => URL.revokeObjectURL(url), 60000);
        }
      }
      setDataStatus('Backup exported. Store it somewhere private.');
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : 'Export failed');
    }
  }

  async function importData(file?: File) {
    if (!file) return;
    try {
      if (file.size > 50 * 1024 * 1024) throw new Error('Backup is larger than 50 MB');
      await importLocalData(await file.text());
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
      await queryClient.invalidateQueries({ queryKey: ['messages'] });
      setNotes(await getLocalDigest('pinned'));
      setDataStatus('Backup imported on this device.');
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : 'Import failed');
    }
  }

  function saveApiUrl() {
    const normalized = apiUrl.trim().replace(/\/$/, '');
    if (!normalized) return;
    localStorage.setItem('ayeneh_api_url', normalized);
    setApiUrl(normalized);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2200);
  }

  return (
    <PageLayout title="Settings" description="Configure your Ayeneh experience">
      <div className="max-w-2xl space-y-6">
        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Appearance</h3>
          <div className="space-y-3">
            <label className="block text-sm font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>Theme</label>
            <div className="flex gap-2">
              {(['light', 'dark', 'system'] as const).map((t) => (
                <Button
                  key={t}
                  variant={theme === t ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme(t)}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <ModelProfilesSettings />

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-2" style={{ color: '#fff' }}>Legacy backend (optional)</h3>
          <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Older library and dashboard screens still use this connection. Chat on Android uses the cloud model key saved above and does not need this server.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={apiUrl}
              onChange={(event) => { setApiUrl(event.target.value); setSaved(false); }}
              placeholder="https://your-ayeneh-server.example.com"
              aria-label="Ayeneh backend URL"
              className="min-w-0 flex-1 rounded-md px-3 py-2 text-sm"
              style={{ border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: '#fff' }}
            />
            <Button size="sm" onClick={saveApiUrl} disabled={!apiUrl.trim()}>
              {saved ? 'Saved' : 'Save URL'}
            </Button>
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Pinned memories</h3>
          <p className="text-sm mb-3" style={{ color: 'rgba(255,255,255,0.4)' }}>Facts you want Ayeneh to remember. Stored only on this device and included in a small context when relevant.</p>
          <div className="flex gap-2">
            <input value={newNote} onChange={(event) => setNewNote(event.target.value)} maxLength={500}
              aria-label="New memory" placeholder="A preference or fact worth remembering"
              className="min-w-0 flex-1 rounded-md px-3 py-2 text-sm"
              style={{ border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: '#fff' }} />
            <Button size="sm" onClick={saveNote} disabled={!newNote.trim()}>Remember</Button>
          </div>
          <div className="mt-3 space-y-2">
            {notes.map((note) => <div key={note.id} className="flex items-start gap-2 rounded-lg p-2 text-sm" style={{ background: 'rgba(255,255,255,0.04)', color: '#ddd' }}>
              <span className="flex-1 whitespace-pre-wrap">{note.content}</span>
              <button aria-label="Remove memory" onClick={async () => {
                await removePinnedNote(note.id);
                setNotes((items) => items.filter((item) => item.id !== note.id));
              }} style={{ color: '#fca5a5' }}>Remove</button>
            </div>)}
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Notifications</h3>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Configure notification preferences for reflections, pattern updates, and blind spot alerts.</p>
          <div className="mt-3 space-y-2">
            {['Reflections ready', 'New patterns detected', 'Blind spots identified'].map((item) => (
              <label key={item} className="flex items-center gap-2 text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>
                <input type="checkbox" defaultChecked className="rounded" />
                {item}
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>Data & Privacy</h3>
          <p className="text-sm mb-3" style={{ color: 'rgba(255,255,255,0.4)' }}>Conversations and memories are saved in this app on this device. Back up before uninstalling or clearing app data.</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={exportData}>Export backup</Button>
            <label className="inline-flex cursor-pointer items-center rounded-md border border-white/15 px-3 text-sm text-white/70">
              Import backup
              <input type="file" accept="application/json,.json" className="sr-only" onChange={(event) => {
                void importData(event.target.files?.[0]);
                event.target.value = '';
              }} />
            </label>
          </div>
          {dataStatus && <p role="status" className="mt-3 text-xs text-white/60">{dataStatus}</p>}
        </div>

        <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: '#fff' }}>About</h3>
          <div className="text-sm space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <p>Ayeneh — Cognitive Companion</p>
            <p>Version 0.1.0</p>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
