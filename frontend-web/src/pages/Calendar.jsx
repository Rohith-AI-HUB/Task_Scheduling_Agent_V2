import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const Calendar = () => {
  const navigate = useNavigate();
  const { userRole } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first?.msg === 'string') return first.msg;
      return JSON.stringify(first);
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    if (typeof err?.message === 'string' && err.message) return err.message;
    return fallback;
  };

  const load = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await api.get('/tasks');
      setTasks(response.data || []);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load tasks'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const grouped = useMemo(() => {
    const list = (tasks || [])
      .filter((t) => t?.deadline)
      .map((t) => ({ ...t, _deadlineDate: new Date(t.deadline) }))
      .filter((t) => !Number.isNaN(t._deadlineDate.getTime()))
      .sort((a, b) => a._deadlineDate.getTime() - b._deadlineDate.getTime());

    const map = new Map();
    for (const t of list) {
      const key = t._deadlineDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(t);
    }
    return Array.from(map.entries());
  }, [tasks]);

  const formatTime = (value) => {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen text-[#110d1c] dark:text-white font-display">
      <header className="sticky top-0 z-50 w-full border-b border-[#d5cee9] bg-background-light/80 backdrop-blur-md dark:border-white/10 dark:bg-background-dark/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <span className="material-symbols-outlined">calendar_month</span>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Calendar</h1>
              <div className="text-xs text-[#5d479e] dark:text-gray-400">{userRole || ''}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="text-sm font-bold text-primary hover:opacity-80" onClick={load} type="button">
              Refresh
            </button>
            <button className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors" onClick={() => navigate(-1)}>
              <span className="material-symbols-outlined text-lg">arrow_back</span>
              Back
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {error ? (
          <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        ) : null}

        {isLoading ? (
          <div className="text-sm text-[#5d479e] dark:text-gray-400">Loading...</div>
        ) : grouped.length === 0 ? (
          <div className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 p-6 text-sm text-[#5d479e] dark:text-gray-400">
            No dated tasks yet.
          </div>
        ) : (
          <div className="space-y-6">
            {grouped.map(([day, rows]) => (
              <div key={day} className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 overflow-hidden">
                <div className="px-5 py-3 border-b border-[#d5cee9] dark:border-white/10 bg-background-light/30 dark:bg-white/5">
                  <div className="font-bold text-[#110d1c] dark:text-white">{day}</div>
                </div>
                <div className="divide-y divide-[#eeeaf6] dark:divide-white/10">
                  {rows.map((t) => (
                    <button
                      key={t.id}
                      className="w-full text-left px-5 py-4 hover:bg-background-light dark:hover:bg-white/5 transition-colors"
                      onClick={() => navigate(`/task/${t.id}`)}
                      type="button"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="font-bold truncate">{t.title || 'Task'}</div>
                          <div className="text-xs text-[#5d479e] dark:text-gray-400 mt-1">
                            {formatTime(t.deadline)}
                            {typeof t.points === 'number' ? ` • ${t.points} pts` : ''}
                          </div>
                        </div>
                        <div className="text-xs font-bold text-primary whitespace-nowrap">{t.type || 'task'}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Calendar;

