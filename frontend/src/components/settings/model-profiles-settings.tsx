'use client';

import { useEffect, useState } from 'react';
import { SecureModel, secureModelAvailable, type ModelProfile } from '@/lib/secure-model';
import { Button } from '@/components/ui/button';

const DEFAULTS: Record<string, { baseUrl: string; model: string }> = {
  openai: { baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  openrouter: { baseUrl: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini' },
  custom: { baseUrl: '', model: '' },
};

export function ModelProfilesSettings() {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [activeProvider, setActive] = useState('');
  const [provider, setProvider] = useState('openai');
  const [baseUrl, setBaseUrl] = useState(DEFAULTS.openai.baseUrl);
  const [model, setModel] = useState(DEFAULTS.openai.model);
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const supported = secureModelAvailable();

  async function refresh() {
    const result = await SecureModel.listProfiles();
    setProfiles(result.profiles);
    setActive(result.activeProvider);
  }

  useEffect(() => {
    if (supported) refresh().catch((error) => setStatus(String(error)));
  }, [supported]);

  function chooseProvider(value: string) {
    setProvider(value);
    const existing = profiles.find((item) => item.provider === value);
    setBaseUrl(existing?.baseUrl || DEFAULTS[value].baseUrl);
    setModel(existing?.model || DEFAULTS[value].model);
    setApiKey('');
    setStatus('');
  }

  async function save() {
    setBusy(true);
    setStatus('');
    try {
      await SecureModel.saveProfile({
        provider, baseUrl: baseUrl.trim(), model: model.trim(), apiKey: apiKey.trim(),
      });
      if (!activeProvider) await SecureModel.setActiveProvider({ provider });
      setApiKey('');
      await refresh();
      setStatus('Model settings saved securely on this phone.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save model settings');
    } finally {
      setBusy(false);
    }
  }

  async function activate(value: string) {
    try {
      await SecureModel.setActiveProvider({ provider: value });
      setActive(value);
      setStatus(`${value} is now active.`);
    } catch (error) {
      setStatus(String(error));
    }
  }

  async function remove(value: string) {
    if (!window.confirm(`Remove the saved ${value} API key from this phone?`)) return;
    try {
      await SecureModel.removeProfile({ provider: value });
      await refresh();
      setStatus(`${value} key removed.`);
    } catch (error) {
      setStatus(String(error));
    }
  }

  return <div className="rounded-lg p-6" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
    <h3 className="mb-2 text-lg font-medium text-white">Cloud model keys</h3>
    <p className="mb-4 text-sm text-white/45">Keys are encrypted by Android Keystore. They never enter chat backups and are not shown again after saving.</p>
    {!supported ? <p className="text-sm text-amber-200">Secure key storage is available in the Android app.</p> : <>
      <div className="space-y-3">
        <label className="block text-sm text-white/60">Provider
          <select value={provider} onChange={(event) => chooseProvider(event.target.value)}
            className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white">
            <option value="openai">OpenAI</option>
            <option value="openrouter">OpenRouter</option>
            <option value="custom">OpenAI-compatible provider</option>
          </select>
        </label>
        <label className="block text-sm text-white/60">API base URL
          <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} type="url" readOnly={provider !== 'custom'}
            className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
          {provider === 'custom' && <span className="mt-1 block text-xs text-amber-200/70">This provider receives your key and conversation. Use only an endpoint you trust.</span>}
        </label>
        <label className="block text-sm text-white/60">Model
          <input value={model} onChange={(event) => setModel(event.target.value)}
            className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
        </label>
        <label className="block text-sm text-white/60">API key {profiles.some((item) => item.provider === provider) ? '(leave blank to keep current key)' : ''}
          <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password"
            autoComplete="off" spellCheck={false} placeholder="Enter your key on the phone"
            className="mt-1 w-full rounded-md border border-white/10 bg-[#10101b] px-3 py-2 text-white" />
        </label>
        <Button size="sm" onClick={save} disabled={busy || !baseUrl.startsWith('https://') || !model.trim() || (!apiKey.trim() && !profiles.some((item) => item.provider === provider))}>Save securely</Button>
      </div>
      {profiles.length > 0 && <div className="mt-5 space-y-2 border-t border-white/10 pt-4">
        {profiles.map((item) => <div key={item.provider} className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-sm text-white/70">
          <span className="min-w-0 flex-1 truncate">{item.provider} · {item.model} {activeProvider === item.provider ? '· active' : ''}</span>
          {activeProvider !== item.provider && <button onClick={() => activate(item.provider)} className="text-violet-300">Use</button>}
          <button onClick={() => remove(item.provider)} className="text-red-300">Remove</button>
        </div>)}
      </div>}
    </>}
    {status && <p role="status" className="mt-3 text-xs text-white/65">{status}</p>}
  </div>;
}
