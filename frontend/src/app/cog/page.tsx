'use client';

import { useState } from 'react';
import { useAnalyzeCOG, useCOGHealth } from '@/hooks/use-api';
import { PageLayout } from '@/components/layout/page-layout';
import { Button } from '@/components/ui/button';
import type { CognitiveAnalysisResponse } from '@/types/api';

function AnalysisCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
      <div className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</div>
      <div className="text-2xl font-bold mt-1" style={{ color }}>{value}</div>
    </div>
  );
}

function AnalysisResult({ data }: { data: CognitiveAnalysisResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <AnalysisCard label="Evidence" value={data.evidence_count} color="#a78bfa" />
        <AnalysisCard label="Narratives" value={data.narratives_extracted} color="#60a5fa" />
        <AnalysisCard label="Beliefs" value={data.beliefs_extracted} color="#34d399" />
        <AnalysisCard label="Values" value={data.values_extracted} color="#fbbf24" />
        <AnalysisCard label="Goals" value={data.goals_extracted} color="#f87171" />
        <AnalysisCard label="Identity" value={data.identity_components} color="#c084fc" />
        <AnalysisCard label="Decisions" value={data.decisions} color="#fb923c" />
        <AnalysisCard label="Patterns" value={data.patterns} color="#22d3ee" />
        <AnalysisCard label="Reflections" value={data.reflections} color="#e879f9" />
        <AnalysisCard label="Meta-Cognitive" value={data.meta_cognitive_objects} color="#a3e635" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
          <div className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>Awakening Level</div>
          <div className="mt-2 h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${(data.awakening_level * 100).toFixed(0)}%`, background: 'linear-gradient(90deg, #7c3aed, #a78bfa)' }}
            />
          </div>
          <div className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>{(data.awakening_level * 100).toFixed(1)}%</div>
        </div>
        <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
          <div className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>Reality Calibration</div>
          <div className="mt-2 h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${(data.reality_calibration * 100).toFixed(0)}%`, background: 'linear-gradient(90deg, #2563eb, #60a5fa)' }}
            />
          </div>
          <div className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>{(data.reality_calibration * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
        <div className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>Conversation ID</div>
        <div className="font-mono text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>{data.conversation_id}</div>
      </div>
    </div>
  );
}

export default function COGPage() {
  const [input, setInput] = useState('');
  const analyzeMutation = useAnalyzeCOG();
  const { data: health } = useCOGHealth();

  const handleAnalyze = () => {
    if (!input.trim()) return;
    analyzeMutation.mutate({
      user_id: 'current-user',
      messages: [{ role: 'user', content: input }],
      language: 'en',
    });
  };

  const healthColor = health?.status === 'healthy' ? '#34d399' : '#f87171';

  return (
    <PageLayout
      title="Cognitive Analysis (COG)"
      description="Run the full cognitive pipeline on a conversation"
      actions={
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full" style={{ background: healthColor }} />
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>
              {health ? `COG v${health.version}` : 'Checking...'}
            </span>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(22,22,30,0.8)' }}>
          <textarea
            className="w-full p-3 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
            style={{ background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}
            rows={4}
            placeholder="Enter a conversation to analyze..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAnalyze();
            }}
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {input.length > 0 ? `${input.length} characters` : 'Ctrl+Enter to analyze'}
            </span>
            <Button
              onClick={handleAnalyze}
              disabled={!input.trim() || analyzeMutation.isPending}
            >
              {analyzeMutation.isPending ? 'Analyzing...' : 'Run COG Analysis'}
            </Button>
          </div>
        </div>

        {analyzeMutation.isError && (
          <div className="rounded-lg border p-4" style={{ borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.1)' }}>
            <p className="text-sm" style={{ color: '#f87171' }}>
              Analysis failed: {analyzeMutation.error?.message || 'Unknown error'}
            </p>
          </div>
        )}

        {analyzeMutation.data && <AnalysisResult data={analyzeMutation.data} />}
      </div>
    </PageLayout>
  );
}
