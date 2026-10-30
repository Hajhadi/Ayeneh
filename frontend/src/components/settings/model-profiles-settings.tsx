'use client';

import { useEffect, useState } from 'react';
import { SecureModel, secureModelAvailable, type ModelProfile } from '@/lib/secure-model';
import { Button } from '@/components/ui/button';

type Service = ModelProfile['service'];

const SERVICE_OPTIONS: { id: Service; name: string; baseUrl: string; model: string }[] = [
  { id: 'openai', name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  { id: 'openrouter', name: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini' },
  { id: 'gemini', name: 'Google Gemini', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-3.8-flash' },
  { id: 'anthropic', name: 'Anthropic Claude', baseUrl: 'https://api.anthropic.com/v1', model: 'claude-sonnet-5-5' },
  { id: 'compatible', name: 'Other OpenAI-compatible service', baseUrl: '', model: '' },
];

function serviceOption(id: Service) {
  return SERVICE_OPTIONS.find((item) => item.id === id) || SERVICE_OPTIONS[4];
}

export function ModelProfilesSettings() {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [activeProvider, setActive] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [service, setService] = useState<Service>('openai');
  const [label, setLabel] = useState('');
  const [baseUrl, setBaseUrl] = useState(SERVICE_OPTIONS[0].baseUrl);
  const [model, setModel] = useState(SERVICE_OPTIONS[0].model);
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const supported = secureModelAvailable();
  const existing = profiles.find((item) => item.provider === editingId);
  const needsKey = !existing || existing.service !== service || existing.baseUrl !== baseUrl.trim();

  async function refresh() {
    const result = await SecureModel.listProfiles();
    setProfiles(result.profiles);
    setActive(result.activeProvider);
  }

  useEffect(() => {
    if (supported) refresh().catch((error) => setStatus(String(error)));
  }, [supported]);

  function newConnection() {
    setEditingId(null);
    setService('openai');
    setLabel('');
    setBaseUrl(serviceOption('openai').baseUrl);
    setModel(serviceOption('openai').model);
    setApiKey('');
    setStatus('');
  }

  function edit(profile: ModelProfile) {
    setEditingId(profile.provider);
    setService(profile.service);
    setLabel(profile.label);
    setBaseUrl(profile.baseUrl);
    setModel(profile.model);
    setApiKey('');
    setStatus('');
  }

  function changeService(value: Service) {
    setService(value);
    setBaseUrl(serviceOption(value).baseUrl);
    setModel(serviceOption(value).model);
    setApiKey('');
    setStatus('');
  }

  async function save() {
    setBusy(true);
    setStatus('');
    try {
      const provider = editingId || `p_${crypto.randomUUID().replace(/-/g, '').slice(0, 20)}`;
      const name = label.trim() || `${serviceOption(service).name} ${profiles.filter((item) => item.service === service).length + 1}`;
      await SecureModel.saveProfile({
        provider, service, label: name, baseUrl: baseUrl.trim(), model: model.trim(), apiKey: apiKey.trim(),
      });
      if (!activeProvider) await SecureModel.setActiveProvider({ provider });
      setEditingId(provider);
      setLabel(name);
      setApiKey('');
      await refresh();
      setStatus('Connection saved on this phone. Select Use to switch models.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save the connection');
    } finally {
      setBusy(false);
    }
  }

  async function activate(provider: string) {
    try {
      await SecureModel.setActiveProvider({ provider });
      await refresh();
      setStatus('Active model changed. New replies will use this connection.');
    } catch (error) {
      setStatus(String(error));
    }
  }

  async function remove(profile: ModelProfile) {
    if (!window.confirm(`Remove ${profile.label} and its saved API key from this phone?`)) return;
    try {
      await SecureModel.removeProfile({ provider: profile.provider });
      if (editingId === profile.provider) newConnection();
      await refresh();
      setStatus('Connection removed.');
    } catch (error) {
      setStatus(String(error));
    }
  }

  return <section className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
    <div className="mb-2 flex items-center justify-between gap-3">
      <h3 className="text-lg font-medium text-white">Model connections</h3>
      {supported && <Button variant="outline" size="sm" onClick={newConnection}>Add another</Button>}
    </div>
    <p className="mb-4 text-sm text-white/45">Save multiple keys and choose which model answers you. Keys are encrypted by Android Keystore and omitted from chat backups.</p>
    {!supported ? <p className="text-sm text-amber-200">Secure key storage is available in the Android app.</p> : <>
      {profiles.length > 0 && <div className="mb-5 space-y-2" aria-label="Saved model connections">
        {profiles.map((profile) => <div key={profile.provider} className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">{profile.label}</p>
              <p className="truncate text-xs text-white/45">{serviceOption(profile.service).name} · {profile.model}</p>
            </div>
            {activeProvider === profile.provider && <span className="shrink-0 rounded-full bg-emerald-400/10 px-2 py-1 text-xs text-emerald-200">Active</span>}
          </div>
          <div className="mt-3 flex gap-3 text-xs">
            {activeProvider !== profile.provider && <button type="button" onClick={() => activate(profile.provider)} className="text-violet-300">Use</button>}
            <button type="button" onClick={() => edit(profile)} className="text-white/65">Edit</button>
            <button type="button" onClick={() => remove(profile)} className="text-red-300">Remove</button>
          </div>
        </div>)}
      </div>}
      <div className="border-t border-white/10 pt-4">
        <p className="mb-3 text-sm font-medium text-white/85">{editingId ? 'Edit connection' : 'Add connection'}</p>
        <div className="space-y-3">
          <label className="block text-sm text-white/60">Name (to distinguish your keys)
            <input value={label} onChange={(event) => setLabel(event.target.value)} maxLength={50} placeholder="Personal, work, backup…"
              className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
          </label>
          <label className="block text-sm text-white/60">Service
            <select value={service} onChange={(event) => changeService(event.target.value as Service)}
              className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white">
              {SERVICE_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          {service === 'compatible' && <label className="block text-sm text-white/60">HTTPS API base URL
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} type="url" placeholder="https://provider.example/v1"
              className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
            <span className="mt-1 block text-xs text-amber-200/70">This endpoint receives your key and conversation. Use one you trust.</span>
          </label>}
          <label className="block text-sm text-white/60">Model ID
            <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Enter the model ID from your provider"
              className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
          </label>
          <label className="block text-sm text-white/60">API key {existing && !needsKey ? '(leave blank to keep saved key)' : ''}
            <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password"
              autoComplete="off" spellCheck={false} placeholder="Enter your key on the phone"
              className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
          </label>
          <Button size="sm" onClick={save} disabled={busy || !baseUrl.startsWith('https://') || !model.trim() || (needsKey && !apiKey.trim())}>Save connection</Button>
        </div>
      </div>
    </>}
    {status && <p role="status" className="mt-3 text-xs text-white/65">{status}</p>}
  </section>;
}
