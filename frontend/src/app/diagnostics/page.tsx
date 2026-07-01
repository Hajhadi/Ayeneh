'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api-client';
import { PageLayout } from '@/components/layout/page-layout';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/common/skeleton';

interface DiagnosticCheck {
  status: string;
  provider?: string;
  detail?: string;
}

interface DiagnosticsResult {
  status: string;
  checks: Record<string, DiagnosticCheck>;
}

export default function DiagnosticsPage() {
  const [data, setData] = useState<DiagnosticsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await api.get<DiagnosticsResult>('/api/v1/diagnostics');
      setData(resp);
    } catch (e: any) {
      setError(e.message || 'Failed to load diagnostics');
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <PageLayout
      title="Diagnostics"
      description="System health checks and status"
      actions={<Button onClick={load} variant="outline" size="sm" disabled={loading}>Refresh</Button>}
    >
      {loading && <Skeleton className="h-40" />}
      {error && (
        <div className="p-4 rounded-lg" style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>{error}</div>
      )}
      {data && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg" style={{
            background: data.status === 'healthy' ? 'rgba(34,197,94,0.1)' : 'rgba(234,179,8,0.1)',
            color: data.status === 'healthy' ? '#4ade80' : '#facc15',
          }}>
            Overall status: <span className="font-semibold">{data.status}</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {Object.entries(data.checks).map(([name, check]) => (
              <div key={name} className="rounded-lg p-4" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-medium capitalize" style={{ color: '#fff' }}>{name.replace(/_/g, ' ')}</h3>
                  <span className="px-2 py-0.5 rounded text-xs font-medium" style={{
                    background: check.status === 'connected' || check.status === 'initialized' ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.05)',
                    color: check.status === 'connected' || check.status === 'initialized' ? '#4ade80' : 'rgba(255,255,255,0.4)',
                  }}>
                    {check.status}
                  </span>
                </div>
                {check.provider && <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>Provider: {check.provider}</p>}
              </div>
            ))}
          </div>

          <div className="rounded-lg p-4" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
            <h3 className="font-medium mb-2" style={{ color: '#fff' }}>Raw Diagnostics</h3>
            <pre className="text-xs p-3 rounded overflow-auto max-h-40" style={{ background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.6)' }}>
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
