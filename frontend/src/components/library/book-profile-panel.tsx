'use client';

import { useState } from 'react';
import { useBookProfile, useRegenerateProfile } from '@/hooks/use-api';
import type { EpistemicProfile } from '@/types/api';

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium"
      style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
    >
      {label}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-2 text-left"
        style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}
      >
        {title}
        <span style={{ fontSize: '9px', transform: open ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>▾</span>
      </button>
      {open && <div className="pb-3" style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', lineHeight: '1.6' }}>{children}</div>}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 mb-1">
      <span style={{ color: 'rgba(255,255,255,0.3)', minWidth: '90px', fontSize: '11px' }}>{label}</span>
      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px' }}>{value}</span>
    </div>
  );
}

function StringList({ items }: { items: string[] }) {
  if (!items.length) return <span style={{ color: 'rgba(255,255,255,0.2)' }}>—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item, i) => (
        <span key={i} className="rounded px-1.5 py-0.5" style={{ background: 'rgba(255,255,255,0.04)', fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>
          {item}
        </span>
      ))}
    </div>
  );
}

function ReliabilityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.7 ? '#22C55E' : score >= 0.4 ? '#EAB308' : '#EF4444';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: '11px', color, fontVariantNumeric: 'tabular-nums' }}>{pct}%</span>
    </div>
  );
}

export function BookProfilePanel({ bookId, bookTitle }: { bookId: string; bookTitle: string }) {
  const { data: profile, isLoading, error } = useBookProfile(bookId);
  const regenerate = useRegenerateProfile();

  if (isLoading) {
    return (
      <div className="rounded-lg p-4" style={{ background: '#0D0D14', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 rounded w-1/3" style={{ background: 'rgba(255,255,255,0.06)' }} />
          <div className="h-3 rounded w-2/3" style={{ background: 'rgba(255,255,255,0.04)' }} />
          <div className="h-3 rounded w-1/2" style={{ background: 'rgba(255,255,255,0.04)' }} />
        </div>
      </div>
    );
  }

  if (error || !profile || 'error' in profile) {
    return (
      <div className="rounded-lg p-4" style={{ background: '#0D0D14', border: '1px solid rgba(255,255,255,0.06)' }}>
        <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '12px' }}>پروفایل شناختی یافت نشد</p>
      </div>
    );
  }

  const p = profile as EpistemicProfile;
  const fwColor = p.framework === 'rationalist' ? '#6366F1' :
                  p.framework === 'empiricist' ? '#3B82F6' :
                  p.framework === 'phenomenological' ? '#8B5CF6' :
                  p.framework === 'intuitionist' ? '#A855F7' :
                  p.framework === 'pragmatist' ? '#14B8A6' : '#71717A';

  return (
    <div className="rounded-lg overflow-hidden" style={{ background: '#0D0D14', border: '1px solid rgba(255,255,255,0.06)' }}>
      {/* Header */}
      <div className="p-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div className="flex items-start justify-between">
          <div>
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>پروفایل شناختی</h3>
            <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', marginTop: '2px' }}>{bookTitle}</p>
          </div>
          <button
            onClick={() => regenerate.mutate(bookId)}
            disabled={regenerate.isPending}
            className="rounded-md px-3 py-1.5 text-[11px] font-medium transition-colors"
            style={{
              background: regenerate.isPending ? 'rgba(124,58,237,0.1)' : 'rgba(124,58,237,0.15)',
              color: '#A78BFA',
              border: '1px solid rgba(124,58,237,0.2)',
              opacity: regenerate.isPending ? 0.6 : 1,
            }}
          >
            {regenerate.isPending ? 'در حال بازتولید...' : 'بازتولید'}
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-3">
          <Badge label={p.framework} color={fwColor} />
          <Badge label={p.discipline} color="#22C55E" />
          <Badge label={p.evidence_level} color="#EAB308" />
          <Badge label={p.reasoning_style} color="#F97316" />
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-0" style={{ maxHeight: '500px', overflowY: 'auto' }}>
        <Section title="اعتبار و قابلیت اطمینان">
          <Field label="可靠性" value={<ReliabilityBar score={p.source_reliability?.score || 0} />} />
          <Field label="مبنای" value={p.source_reliability?.basis || '—'} />
          <Field label="سطح" value={p.authority} />
        </Section>

        <Section title="موضوعات">
          <div className="mb-2">
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>اصلی:</span>
            <StringList items={p.primary_topics} />
          </div>
          <div>
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>ثانویه:</span>
            <StringList items={p.secondary_topics} />
          </div>
        </Section>

        <Section title="نوع ادعاها">
          <StringList items={p.claim_types} />
        </Section>

        <Section title="محدودیت‌ها">
          {p.limitations.length ? p.limitations.map((lim, i) => (
            <div key={i} className="mb-1.5">
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>{lim.description}</span>
              <span className="ml-1.5 rounded px-1 py-0.5" style={{
                fontSize: '9px',
                background: lim.severity === 'significant' ? 'rgba(239,68,68,0.15)' : lim.severity === 'moderate' ? 'rgba(234,179,8,0.15)' : 'rgba(255,255,255,0.05)',
                color: lim.severity === 'significant' ? '#F87171' : lim.severity === 'moderate' ? '#FACC15' : 'rgba(255,255,255,0.4)',
              }}>{lim.severity}</span>
            </div>
          )) : <span style={{ color: 'rgba(255,255,255,0.2)' }}>—</span>}
        </Section>

        <Section title="مرز پوشش">
          <div className="mb-2">
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>شامل:</span>
            <StringList items={p.scope_boundary?.included_topics || []} />
          </div>
          <div>
            <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>خارج از:</span>
            <StringList items={p.scope_boundary?.excluded_topics || []} />
          </div>
        </Section>

        <Section title="سیاست ارجاع">
          <Field label="الزامی" value={p.citation_policy?.required ? 'بله' : 'خیر'} />
          <Field label="فرمت" value={p.citation_policy?.format || '—'} />
          <Field label="حداقل اطمینان" value={p.citation_policy?.min_confidence?.toFixed(2) || '—'} />
        </Section>

        <Section title="سوالات پشتیبانی شده">
          <StringList items={p.supported_questions} />
        </Section>

        <Section title="سوالات پشتیبانی نشده">
          <StringList items={p.unsupported_questions} />
        </Section>
      </div>

      {/* Regenerate result */}
      {regenerate.isSuccess && regenerate.data && (
        <div className="p-3 mx-4 mb-4 rounded" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.15)' }}>
          <p style={{ fontSize: '11px', color: '#4ade80' }}>
            بازتولید شد ({regenerate.data.duration_ms.toFixed(0)}ms) — {regenerate.data.is_valid ? '✓ معتبر' : '✗ نامعتبر'}
          </p>
        </div>
      )}
    </div>
  );
}
