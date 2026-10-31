import { LOCAL_DB_VERSION } from './local-data';

export type HabitFrequency = 'daily' | 'weekly';
export type HabitEntryStatus = 'completed' | 'skipped';

export interface Habit {
  id: string;
  title: string;
  description: string;
  color: string;
  frequency: HabitFrequency;
  target_per_week: number;
  archived: boolean;
  created_at: string;
}

export interface HabitEntry {
  id: string;
  habit_id: string;
  date: string;
  status: HabitEntryStatus;
  note: string;
  created_at: string;
}

export interface HabitSnapshot extends Habit {
  today: HabitEntry | null;
  entries: HabitEntry[];
  completed_count: number;
  strength: number;
  current_streak: number;
  best_streak: number;
  recent_completion_rate: number;
}

const DB_NAME = 'ayeneh-local';
const COLORS = ['orange', 'violet', 'cyan', 'rose', 'emerald', 'amber'] as const;
export type HabitColor = typeof COLORS[number];
const opening: { current?: Promise<IDBDatabase> } = {};

function request<T>(operation: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    operation.onsuccess = () => resolve(operation.result);
    operation.onerror = () => reject(operation.error);
  });
}

function transactionDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error || new Error('Local habit storage failed'));
    tx.onabort = () => reject(tx.error || new Error('Local habit storage aborted'));
  });
}

function database(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') return Promise.reject(new Error('Local storage is unavailable'));
  if (!opening.current) {
    opening.current = new Promise<IDBDatabase>((resolve, reject) => {
      const open = indexedDB.open(DB_NAME, LOCAL_DB_VERSION);
      open.onsuccess = () => { open.result.onversionchange = () => open.result.close(); resolve(open.result); };
      open.onerror = () => reject(open.error);
    }).catch((error) => { opening.current = undefined; throw error; });
  }
  return opening.current;
}

export function todayKey(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function dateKeyOffset(offset: number, from = new Date()): string {
  const date = new Date(from);
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + offset);
  return todayKey(date);
}

export function recentDateKeys(days = 28): string[] {
  return Array.from({ length: days }, (_, index) => dateKeyOffset(index - days + 1));
}

export function habitColorClass(color: string): string {
  return COLORS.includes(color as HabitColor) ? color : 'orange';
}

export async function listHabits(includeArchived = false): Promise<Habit[]> {
  const db = await database();
  const habits = await request<Habit[]>(db.transaction('habits').objectStore('habits').getAll());
  return habits.filter((habit) => includeArchived || !habit.archived)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function createHabit(input: {
  title: string;
  description?: string;
  color?: string;
  frequency?: HabitFrequency;
  targetPerWeek?: number;
}): Promise<Habit> {
  const title = input.title.trim();
  if (!title || title.length > 100) throw new Error('Habit title must be between 1 and 100 characters');
  const habit: Habit = {
    id: crypto.randomUUID(), title, description: input.description?.trim().slice(0, 240) || '',
    color: habitColorClass(input.color || 'orange'), frequency: input.frequency || 'daily',
    target_per_week: Math.min(7, Math.max(1, Math.round(input.targetPerWeek || 3))),
    archived: false, created_at: new Date().toISOString(),
  };
  const db = await database();
  const tx = db.transaction('habits', 'readwrite');
  const done = transactionDone(tx);
  tx.objectStore('habits').put(habit);
  await done;
  return habit;
}

export async function archiveHabit(id: string): Promise<void> {
  const db = await database();
  const tx = db.transaction('habits', 'readwrite');
  const store = tx.objectStore('habits');
  const done = transactionDone(tx);
  const habit = await request<Habit | undefined>(store.get(id));
  if (habit) store.put({ ...habit, archived: true });
  await done;
}

export async function listHabitEntries(habitId?: string, from?: string, to?: string): Promise<HabitEntry[]> {
  const db = await database();
  const entries = await request<HabitEntry[]>(db.transaction('habit_entries').objectStore('habit_entries').getAll());
  return entries.filter((entry) => (!habitId || entry.habit_id === habitId)
    && (!from || entry.date >= from) && (!to || entry.date <= to))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export async function setHabitEntry(habitId: string, date = todayKey(), status: HabitEntryStatus = 'completed', note = ''): Promise<HabitEntry> {
  const entry: HabitEntry = { id: `${habitId}:${date}`, habit_id: habitId, date, status, note: note.trim().slice(0, 240), created_at: new Date().toISOString() };
  const db = await database();
  const tx = db.transaction('habit_entries', 'readwrite');
  const done = transactionDone(tx);
  tx.objectStore('habit_entries').put(entry);
  await done;
  return entry;
}

export async function removeHabitEntry(habitId: string, date = todayKey()): Promise<void> {
  const db = await database();
  const tx = db.transaction('habit_entries', 'readwrite');
  const done = transactionDone(tx);
  tx.objectStore('habit_entries').delete(`${habitId}:${date}`);
  await done;
}

function calculateStreak(entries: HabitEntry[], endDate: string): number {
  const completed = new Set(entries.filter((entry) => entry.status === 'completed').map((entry) => entry.date));
  let streak = 0;
  for (let offset = 0; ; offset -= 1) {
    if (!completed.has(dateKeyOffset(offset, new Date(`${endDate}T12:00:00`)))) break;
    streak += 1;
  }
  return streak;
}

function calculateBestStreak(entries: HabitEntry[]): number {
  const completed = new Set(entries.filter((entry) => entry.status === 'completed').map((entry) => entry.date));
  let best = 0;
  for (const date of completed) best = Math.max(best, calculateStreak(entries, date));
  return best;
}

export function calculateStrength(habit: Habit, entries: HabitEntry[], now = new Date()): number {
  const created = new Date(habit.created_at);
  const elapsedDays = Math.max(1, Math.floor((now.getTime() - created.getTime()) / 86400000) + 1);
  const completed = entries.filter((entry) => entry.status === 'completed').length;
  const expected = habit.frequency === 'daily' ? elapsedDays : Math.max(1, Math.ceil(elapsedDays / 7) * habit.target_per_week);
  return Math.min(100, Math.round((completed / expected) * 100));
}

export async function getHabitSnapshots(): Promise<HabitSnapshot[]> {
  const habits = await listHabits();
  const from = dateKeyOffset(-83);
  const allEntries = await listHabitEntries(undefined, from, todayKey());
  return habits.map((habit) => {
    const entries = allEntries.filter((entry) => entry.habit_id === habit.id);
    const completed = entries.filter((entry) => entry.status === 'completed').length;
    const recent = entries.filter((entry) => entry.date >= dateKeyOffset(-27));
    return {
      ...habit, today: entries.find((entry) => entry.date === todayKey()) || null, entries,
      completed_count: completed, strength: calculateStrength(habit, entries),
      current_streak: calculateStreak(entries, todayKey()), best_streak: calculateBestStreak(entries),
      recent_completion_rate: Math.round((recent.filter((entry) => entry.status === 'completed').length / (habit.frequency === 'daily' ? 28 : 4 * habit.target_per_week)) * 100),
    };
  });
}

export async function buildHabitContext(): Promise<string> {
  const snapshots = await getHabitSnapshots();
  if (!snapshots.length) return '';
  const lines = snapshots.slice(0, 12).map((habit) => {
    const state = habit.today?.status === 'completed' ? 'completed today' : habit.today?.status === 'skipped' ? 'skipped today' : 'not recorded today';
    return `Pattern ${habit.title}: ${state}; strength ${habit.strength}%; current streak ${habit.current_streak} days; 28-day completion ${Math.min(100, habit.recent_completion_rate)}%.`;
  });
  return `Local behavior patterns (summarized, not diagnosis):\n${lines.join('\n')}`;
}
