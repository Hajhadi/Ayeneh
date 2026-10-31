'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Archive, Check, Flame, Plus, RotateCcw, Target, X } from 'lucide-react';
import { archiveHabit, createHabit, dateKeyOffset, getHabitSnapshots, habitColorClass, recentDateKeys, setHabitEntry, type HabitColor, type HabitFrequency, type HabitSnapshot, todayKey } from '@/lib/habit-data';

const COLORS: { id: HabitColor; className: string }[] = [
  { id: 'orange', className: 'habit-color-orange' }, { id: 'violet', className: 'habit-color-violet' },
  { id: 'cyan', className: 'habit-color-cyan' }, { id: 'rose', className: 'habit-color-rose' },
  { id: 'emerald', className: 'habit-color-emerald' },
];

function dayLabel(date: string): string {
  return new Intl.DateTimeFormat('en', { weekday: 'short' }).format(new Date(`${date}T12:00:00`)).slice(0, 1);
}

function HabitCard({ habit, onRefresh }: { habit: HabitSnapshot; onRefresh: () => void }) {
  const keys = useMemo(() => recentDateKeys(28), []);
  const statuses = new Map(habit.entries.map((entry) => [entry.date, entry.status]));
  const [busy, setBusy] = useState(false);
  const completeToday = async () => {
    setBusy(true);
    try {
      await setHabitEntry(habit.id, todayKey(), habit.today?.status === 'completed' ? 'skipped' : 'completed');
      onRefresh();
    } finally { setBusy(false); }
  };
  const color = habitColorClass(habit.color);
  return (
    <motion.article layout className={`habit-card habit-card-${color}`}>
      <div className="habit-card-topline">
        <div className="habit-title-wrap"><span className="habit-color-dot" /><div><h3>{habit.title}</h3>{habit.description && <p>{habit.description}</p>}</div></div>
        <button className={`habit-check-button ${habit.today?.status === 'completed' ? 'is-complete' : ''}`} onClick={completeToday} disabled={busy} aria-label={`Mark ${habit.title} today`}>
          {habit.today?.status === 'completed' ? <Check size={18} /> : <Plus size={18} />}
        </button>
      </div>
      <div className="habit-metrics"><span><strong>{habit.strength}%</strong> strength</span><span><Flame size={13} /> {habit.current_streak} day streak</span><span>{habit.frequency === 'daily' ? 'Daily' : `${habit.target_per_week}× / week`}</span></div>
      <div className="habit-calendar" aria-label={`${habit.title} recent activity`}>
        {keys.map((date) => <span key={date} title={date} className={`habit-day habit-day-${statuses.get(date) || 'empty'} ${date === todayKey() ? 'is-today' : ''}`}>{dayLabel(date)}</span>)}
      </div>
      <div className="habit-card-footer"><span>{habit.completed_count} completions · best {habit.best_streak} days</span><span>{habit.recent_completion_rate}% this month</span></div>
    </motion.article>
  );
}

export default function HabitsPage() {
  const [habits, setHabits] = useState<HabitSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [frequency, setFrequency] = useState<HabitFrequency>('daily');
  const [target, setTarget] = useState('3');
  const [color, setColor] = useState<HabitColor>('orange');
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try { setHabits(await getHabitSnapshots()); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await createHabit({ title, description, frequency, targetPerWeek: Number(target), color });
      setTitle(''); setDescription(''); setShowForm(false); await refresh();
    } finally { setSaving(false); }
  };

  const activeToday = habits.filter((habit) => habit.today?.status === 'completed').length;
  const averageStrength = habits.length ? Math.round(habits.reduce((sum, habit) => sum + habit.strength, 0) / habits.length) : 0;

  return (
    <div className="page-layout flex h-full min-h-0 flex-col">
      <div className="page-heading"><div><p className="eyebrow"><Target size={13} /> PATTERNS IN PRACTICE</p><h1 className="mt-2 text-2xl font-semibold">Habits & rhythms</h1><p className="mt-1 text-sm text-white/40">Small repetitions become visible patterns.</p></div><button className="app-primary-button" onClick={() => setShowForm(true)}><Plus size={16} /> New habit</button></div>
      <main className="page-scroll-area flex-1 p-8">
        <div className="habits-summary-grid">
          <div className="habits-summary-card"><span>Today’s rhythm</span><strong>{activeToday}<small> / {habits.length}</small></strong><em>completed practices</em></div>
          <div className="habits-summary-card"><span>Pattern strength</span><strong>{averageStrength}%</strong><em>across active habits</em></div>
          <div className="habits-summary-card habits-summary-insight"><Flame size={20} /><div><strong>Consistency over intensity</strong><em>Ayeneh watches the long view, not perfection.</em></div></div>
        </div>

        <AnimatePresence>{showForm && <motion.form className="habit-form-card" onSubmit={save} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
          <div className="habit-form-header"><div><p className="eyebrow"><Plus size={13} /> CREATE A RHYTHM</p><h2>What would you like to notice?</h2></div><button type="button" className="habit-close" onClick={() => setShowForm(false)}><X size={17} /></button></div>
          <div className="habit-form-grid"><label>Habit name<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Write one honest sentence" autoFocus /></label><label>Why it matters <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional reminder to your future self" /></label></div>
          <div className="habit-form-options"><div><span className="habit-option-label">Cadence</span><div className="habit-segmented"><button type="button" className={frequency === 'daily' ? 'active' : ''} onClick={() => setFrequency('daily')}>Every day</button><button type="button" className={frequency === 'weekly' ? 'active' : ''} onClick={() => setFrequency('weekly')}>Weekly target</button></div></div>{frequency === 'weekly' && <label className="habit-target">Times per week<input type="number" min="1" max="7" value={target} onChange={(e) => setTarget(e.target.value)} /></label>}<div><span className="habit-option-label">Signal color</span><div className="habit-color-picker">{COLORS.map((item) => <button type="button" key={item.id} className={`${item.className} ${color === item.id ? 'selected' : ''}`} onClick={() => setColor(item.id)} aria-label={item.id} />)}</div></div></div>
          <div className="habit-form-actions"><button type="button" className="app-secondary-button" onClick={() => setShowForm(false)}>Cancel</button><button className="app-primary-button" disabled={saving || !title.trim()}>{saving ? 'Saving…' : 'Add habit'}</button></div>
        </motion.form>}</AnimatePresence>

        {loading ? <div className="habit-empty"><RotateCcw className="animate-spin" size={20} /> Reading your local patterns…</div> : habits.length === 0 ? <div className="habit-empty habit-empty-large"><div className="habit-empty-orbit"><Target size={24} /></div><h2>Give a pattern somewhere to begin</h2><p>Track a small, meaningful practice. The goal is noticing—not becoming perfect.</p><button className="app-primary-button" onClick={() => setShowForm(true)}><Plus size={16} /> Create your first habit</button></div> : <motion.div layout className="habits-list">{habits.map((habit) => <HabitCard key={habit.id} habit={habit} onRefresh={() => void refresh()} />)}</motion.div>}
        {habits.length > 0 && <p className="habit-privacy-note"><span /> Stored only on this device · summarized before it reaches the cloud model</p>}
      </main>
    </div>
  );
}
