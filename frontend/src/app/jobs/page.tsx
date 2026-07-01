'use client';

import { useQueueStatus, useWorkers, useRuntimeStatus, useExecutionHistory } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { Skeleton } from '@/components/common/skeleton';
import { Button } from '@/components/ui/button';

function MetricCard({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) {
  return (
    <div className="rounded-lg p-4" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
      <div className="text-xs uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</div>
      <div className="text-2xl font-bold mt-1" style={{ color: '#fff' }}>{value}</div>
      {subtext && <div className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>{subtext}</div>}
    </div>
  );
}

export default function JobsPage() {
  const { data: queueStatus, isLoading: qLoading } = useQueueStatus();
  const { data: workers, isLoading: wLoading } = useWorkers();
  const { data: runtime, isLoading: rLoading } = useRuntimeStatus();
  const { data: executions, isLoading: eLoading } = useExecutionHistory(10);

  return (
    <PageLayout title="Jobs & Runtime" description="Monitor distributed jobs and runtime status">
      <div className="space-y-6">
        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>Queue Status</h2>
          {qLoading ? <Skeleton className="h-24" /> : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricCard label="Queue Depth" value={queueStatus?.depth ?? 0} />
              <MetricCard label="Throughput" value={`${queueStatus?.throughput_per_second ?? 0}/s`} />
              <MetricCard label="Success Rate" value={queueStatus ? `${(queueStatus.success_rate * 100).toFixed(1)}%` : '—'} />
              <MetricCard label="Avg Latency" value={queueStatus ? `${queueStatus.avg_latency_ms.toFixed(0)}ms` : '—'} />
            </div>
          )}
        </section>

        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>Workers</h2>
          {wLoading ? <Skeleton className="h-20" /> : (
            <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
              <table className="w-full text-sm">
                <thead style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Worker</th>
                    <th className="px-4 py-2 text-left text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Status</th>
                    <th className="px-4 py-2 text-right text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Active</th>
                    <th className="px-4 py-2 text-right text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Done</th>
                    <th className="px-4 py-2 text-right text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Failed</th>
                  </tr>
                </thead>
                <tbody>
                  {(workers || []).map((w) => (
                    <tr key={w.worker_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>{w.worker_id}</td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" style={{
                          background: w.status === 'running' ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.05)',
                          color: w.status === 'running' ? '#4ade80' : 'rgba(255,255,255,0.4)',
                        }}>{w.status}</span>
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: 'rgba(255,255,255,0.6)' }}>{w.active_jobs}</td>
                      <td className="px-4 py-2 text-right" style={{ color: 'rgba(255,255,255,0.6)' }}>{w.completed_jobs}</td>
                      <td className="px-4 py-2 text-right" style={{ color: 'rgba(255,255,255,0.6)' }}>{w.failed_jobs}</td>
                    </tr>
                  ))}
                  {(!workers || workers.length === 0) && (
                    <tr><td colSpan={5} className="px-4 py-4 text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>No workers registered</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>Runtime Status</h2>
          {rLoading ? <Skeleton className="h-16" /> : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricCard label="Status" value={runtime?.status || '—'} />
              <MetricCard label="Active" value={runtime?.active_executions ?? 0} />
              <MetricCard label="Uptime" value={runtime ? `${Math.floor(runtime.uptime_seconds / 60)}m` : '—'} />
              <MetricCard label="Version" value={runtime?.version || '—'} />
            </div>
          )}
        </section>

        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>Recent Executions</h2>
          {eLoading ? <Skeleton className="h-32" /> : (
            <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1A1A2E' }}>
              <table className="w-full text-sm">
                <thead style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Status</th>
                    <th className="px-4 py-2 text-right text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Duration</th>
                    <th className="px-4 py-2 text-left text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {(executions?.data || []).map((e) => (
                    <tr key={e.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td className="px-4 py-2 font-mono text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>{e.id.slice(0, 8)}...</td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium" style={{
                          background: e.status === 'completed' ? 'rgba(34,197,94,0.1)' :
                            e.status === 'failed' ? 'rgba(239,68,68,0.1)' : 'rgba(234,179,8,0.1)',
                          color: e.status === 'completed' ? '#4ade80' :
                            e.status === 'failed' ? '#f87171' : '#facc15',
                        }}>{e.status}</span>
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: 'rgba(255,255,255,0.6)' }}>{e.duration_ms ? `${e.duration_ms.toFixed(0)}ms` : '—'}</td>
                      <td className="px-4 py-2 text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{new Date(e.started_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                  {(!executions?.data || executions.data.length === 0) && (
                    <tr><td colSpan={4} className="px-4 py-4 text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>No executions yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </PageLayout>
  );
}
