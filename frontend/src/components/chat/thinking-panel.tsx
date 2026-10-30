'use client';

import { useState } from 'react';

export interface ThinkingStep {
  stage: string;
  status: 'running' | 'done' | 'error';
  confidence: number;
  duration_ms: number;
  message?: string;
  details?: Record<string, any>;
}

const STAGE_CONFIG: Record<string, { label: string; group: string }> = {
  conversation_agent:  { label: 'ورود پیام',        group: 'input' },
  dialogue_intention:  { label: 'تشخیص قصد',        group: 'analysis' },
  ai_router_local:     { label: 'مسیریابی اولیه',   group: 'analysis' },
  query_analysis:      { label: 'تحلیل پرسش',       group: 'analysis' },
  knowledge_graph:     { label: 'جستجوی دانش',      group: 'knowledge' },
  graph_reasoning:     { label: 'استدلال',           group: 'knowledge' },
  interpretation:      { label: 'تفسیر',            group: 'knowledge' },
  epistemic_safety:    { label: 'ایمنی شناختی',      group: 'safety' },
  ai_router_final:     { label: 'انتخاب مدل',        group: 'generation' },
  llm_generation:      { label: 'تولید پاسخ',        group: 'generation' },
  response_builder:    { label: 'ساخت پاسخ',         group: 'generation' },
  final_response:      { label: 'پاسخ نهایی',        group: 'output' },
  safety_postcheck:    { label: 'بررسی نهایی',       group: 'output' },
};

interface ThinkingPanelProps {
  steps: ThinkingStep[];
  isComplete: boolean;
  totalMs?: number;
  isActive: boolean;
}

export function ThinkingPanel({ steps, isComplete, totalMs, isActive }: ThinkingPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return '#3B82F6';
      case 'done':    return '#22C55E';
      case 'error':   return '#EF4444';
      default:        return '#3F3F46';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return '◉';
      case 'done':    return '✓';
      case 'error':   return '✕';
      default:        return '○';
    }
  };

  return (
    <div className="thinking-panel" style={{
      background: '#0D0D14',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      maxHeight: '400px',
      overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '12px', paddingBottom: '10px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isActive && !isComplete && (
            <div style={{
              width: '8px', height: '8px', borderRadius: '50%',
              border: '1.5px solid rgba(59,130,246,0.2)', borderTopColor: '#3B82F6',
              animation: 'spinner-spin 0.8s linear infinite',
            }} />
          )}
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#71717A', letterSpacing: '0.05em' }}>
            {isComplete ? 'فکر کردن کامل شد' : isActive ? 'در حال فکر کردن...' : 'مراحل پردازش'}
          </span>
        </div>
        {isComplete && totalMs && (
          <span style={{
            fontSize: '10px', fontWeight: 600, color: '#22C55E',
            background: 'rgba(34,197,94,0.12)', padding: '2px 6px', borderRadius: '4px',
          }}>
            {(totalMs / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {steps.map((step, i) => {
          const config = STAGE_CONFIG[step.stage] || { label: step.stage, group: 'other' };
          const color = getStatusColor(step.status);
          const icon = getStatusIcon(step.status);
          const isExpanded = expanded === step.stage;

          return (
            <div key={`${step.stage}-${i}`}>
              {/* Step row */}
              <div className="thinking-step"
                onClick={() => setExpanded(isExpanded ? null : step.stage)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '6px 8px', borderRadius: '6px',
                  cursor: 'pointer', transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                {/* Status icon */}
                <span style={{
                  fontSize: '10px', color, width: '14px', textAlign: 'center',
                  animation: step.status === 'running' ? 'dot-pulse 1.2s ease-in-out infinite' : 'none',
                }}>
                  {icon}
                </span>

                {/* Stage label */}
                <span style={{
                  fontSize: '12px', fontWeight: 500,
                  color: step.status === 'done' ? '#e2e8f0' : step.status === 'running' ? '#fff' : '#71717A',
                  flex: 1,
                }}>
                  {config.label}
                </span>

                {/* Message preview */}
                {step.message && step.status === 'done' && (
                  <span style={{
                    fontSize: '11px', color: '#52525B',
                    maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {step.message}
                  </span>
                )}

                {/* Duration */}
                {step.duration_ms > 0 && step.status === 'done' && (
                  <span style={{
                    fontSize: '10px', color: '#52525B',
                    fontVariantNumeric: 'tabular-nums',
                  }}>
                    {step.duration_ms < 1000 ? `${step.duration_ms.toFixed(0)}ms` : `${(step.duration_ms / 1000).toFixed(1)}s`}
                  </span>
                )}

                {/* Chevron */}
                {(step.message || step.details) && (
                  <span style={{
                    fontSize: '9px', color: '#52525B',
                    transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)',
                    transition: 'transform 0.2s',
                  }}>▾</span>
                )}
              </div>

              {/* Expanded details */}
              {isExpanded && (step.message || step.details) && (
                <div style={{
                  padding: '6px 8px 6px 28px',
                  fontSize: '11px', color: '#71717A', lineHeight: '1.5',
                  animation: 'fadeIn 0.15s ease-out',
                }}>
                  {step.message && <div style={{ color: '#a1a1aa', marginBottom: '4px' }}>{step.message}</div>}
                  {step.details && Object.entries(step.details).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', gap: '8px', marginBottom: '2px' }}>
                      <span style={{ color: '#52525B', minWidth: '80px' }}>{key}:</span>
                      <span style={{ color: '#a1a1aa' }}>{JSON.stringify(val)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
