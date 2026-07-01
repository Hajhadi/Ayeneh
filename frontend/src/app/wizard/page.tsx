'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api-client';

interface SetupStep {
  step: string;
  completed: boolean;
  detail: string;
}

interface WizardStatus {
  current_step: string;
  completed_steps: string[];
  is_complete: boolean;
  steps: SetupStep[];
}

interface DiagnosticCheck {
  valid: boolean;
  provider?: string;
  detail?: string;
}

const STEP_LABELS: Record<string, string> = {
  select_profile: 'Select Product Profile',
  configure_llm: 'Configure LLM Provider',
  configure_embeddings: 'Configure Embeddings',
  configure_storage: 'Configure Storage',
  validate: 'Validate Setup',
};

const PRODUCTS = [
  { id: 'ayeneh', name: 'Ayeneh', desc: 'Cognitive Companion for self-observation and growth' },
  { id: 'career', name: 'Career Mentor', desc: 'AI-powered career guidance and professional development' },
  { id: 'business', name: 'Business Advisor', desc: 'Strategic business analysis and decision support' },
];

export default function WizardPage() {
  const [status, setStatus] = useState<WizardStatus | null>(null);
  const [diagnostics, setDiagnostics] = useState<Record<string, DiagnosticCheck> | null>(null);
  const [selectedProfile, setSelectedProfile] = useState('ayeneh');
  const [loading, setLoading] = useState(true);

  const loadStatus = async () => {
    try {
      const resp = await api.get<{ current_step: string; completed_steps: string[]; is_complete: boolean; steps: SetupStep[] }>('/api/v1/wizard/status');
      setStatus(resp);
    } catch {
      // first run — show wizard
    }
    setLoading(false);
  };

  const runDiagnostics = async () => {
    try {
      const resp = await api.post<{ checks: Record<string, DiagnosticCheck> }>('/api/v1/wizard/run-full-check', {});
      setDiagnostics(resp.checks);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadStatus(); }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center" style={{ background: '#0A0A12' }}>
        <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (status?.is_complete && !diagnostics) {
    return (
      <div className="flex h-screen items-center justify-center" style={{ background: '#0A0A12' }}>
        <div className="max-w-lg w-full rounded-xl shadow-lg p-8" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
          <h1 className="text-2xl font-bold mb-2" style={{ color: '#fff' }}>Welcome to Ayeneh</h1>
          <p className="mb-6" style={{ color: 'rgba(255,255,255,0.5)' }}>Your system is configured and ready.</p>
          <div className="space-y-3 mb-6">
            {status.steps.map((s) => (
              <div key={s.step} className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full flex items-center justify-center text-sm" style={{
                  background: s.completed ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.05)',
                  color: s.completed ? '#4ade80' : 'rgba(255,255,255,0.3)',
                }}>
                  {s.completed ? '✓' : '○'}
                </span>
                <span className="text-sm" style={{ color: '#fff' }}>{STEP_LABELS[s.step] || s.step}</span>
                <span className="text-xs ml-auto" style={{ color: 'rgba(255,255,255,0.3)' }}>{s.detail}</span>
              </div>
            ))}
          </div>
          <button onClick={runDiagnostics} className="w-full py-2 rounded-lg text-white" style={{ background: '#7C3AED' }}>
            Run Diagnostics
          </button>
        </div>
      </div>
    );
  }

  if (diagnostics) {
    return (
      <div className="flex h-screen items-center justify-center" style={{ background: '#0A0A12' }}>
        <div className="max-w-2xl w-full rounded-xl shadow-lg p-8" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
          <h1 className="text-2xl font-bold mb-2" style={{ color: '#fff' }}>System Diagnostics</h1>
          <p className="mb-6" style={{ color: 'rgba(255,255,255,0.5)' }}>Health check results for all services.</p>
          <div className="space-y-3">
            {Object.entries(diagnostics).map(([name, check]) => (
              <div key={name} className="flex items-center justify-between p-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <span className="font-medium capitalize" style={{ color: '#fff' }}>{name.replace(/_/g, ' ')}</span>
                <span className="px-3 py-1 rounded-full text-sm" style={{
                  background: check.valid ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                  color: check.valid ? '#4ade80' : '#f87171',
                }}>
                  {check.valid ? 'Healthy' : 'Unavailable'}
                  {check.provider ? ` (${check.provider})` : ''}
                </span>
              </div>
            ))}
          </div>
          <button onClick={() => { setDiagnostics(null); loadStatus(); }} className="mt-6 w-full py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.6)' }}>
            Back to Setup
          </button>
        </div>
      </div>
    );
  }

  // Setup wizard
  const completedCount = status?.completed_steps.length || 0;
  const totalSteps = status?.steps.length || 5;
  const currentIdx = status?.steps.findIndex(s => !s.completed) ?? 0;

  return (
    <div className="flex h-screen items-center justify-center" style={{ background: '#0A0A12' }}>
      <div className="max-w-lg w-full rounded-xl shadow-lg p-8" style={{ background: '#1A1A2E', border: '1px solid rgba(255,255,255,0.06)' }}>
        <h1 className="text-2xl font-bold mb-2" style={{ color: '#fff' }}>Setup Wizard</h1>
        <p className="mb-6" style={{ color: 'rgba(255,255,255,0.5)' }}>Step {currentIdx + 1} of {totalSteps}</p>

        <div className="w-full rounded-full h-2 mb-6" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <div className="h-2 rounded-full transition-all" style={{ width: `${(completedCount / totalSteps) * 100}%`, background: '#7C3AED' }} />
        </div>

        {currentIdx === 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold" style={{ color: '#fff' }}>Select Product Profile</h2>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Choose how Ayeneh will behave.</p>
            {PRODUCTS.map(p => (
              <button key={p.id} onClick={() => setSelectedProfile(p.id)}
                className="w-full text-left p-4 rounded-lg transition-colors" style={{
                  border: `2px solid ${selectedProfile === p.id ? 'rgba(124,58,237,0.5)' : 'rgba(255,255,255,0.06)'}`,
                  background: selectedProfile === p.id ? 'rgba(124,58,237,0.1)' : 'transparent',
                }}>
                <div className="font-medium" style={{ color: '#fff' }}>{p.name}</div>
                <div className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>{p.desc}</div>
              </button>
            ))}
          </div>
        )}

        {currentIdx > 0 && status?.steps[currentIdx] && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold" style={{ color: '#fff' }}>{STEP_LABELS[status.steps[currentIdx].step]}</h2>
            <div className="p-4 rounded-lg" style={{ background: 'rgba(34,197,94,0.1)', color: '#4ade80' }}>
              <p className="text-sm">✓ {status.steps[currentIdx].detail}</p>
            </div>
          </div>
        )}

        <button onClick={runDiagnostics}
          className="mt-6 w-full py-2 rounded-lg text-white" style={{ background: '#7C3AED' }}>
          {currentIdx >= totalSteps - 1 ? 'Run Full Diagnostics' : 'Continue'}
        </button>
      </div>
    </div>
  );
}
