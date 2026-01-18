import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const AISchedule = () => {
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const inFlightRef = useRef(false);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first?.msg === 'string') return first.msg;
      return JSON.stringify(first);
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return fallback;
  };

  const load = async ({ silent = false } = {}) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    if (!silent) {
      setIsLoading(true);
      setError('');
    } else {
      setIsRefreshing(true);
    }
    try {
      const response = await api.get('/ai/schedule');
      setSchedule(response.data);
      setError('');
    } catch (err) {
      if (!silent) setError(getErrorMessage(err, 'Failed to load AI schedule'));
    } finally {
      inFlightRef.current = false;
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState !== 'visible') return;
      load({ silent: true });
    };

    const intervalId = window.setInterval(tick, 5000);
    const onVis = () => {
      if (document.visibilityState === 'visible') tick();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  const items = useMemo(() => schedule?.tasks || [], [schedule]);

  const stats = useMemo(() => {
    const out = { urgent: 0, high: 0, normal: 0, low: 0 };
    for (const t of items) {
      const band = t?.band;
      if (band && Object.prototype.hasOwnProperty.call(out, band)) out[band] += 1;
    }
    return out;
  }, [items]);

  const formatRelative = (value) => {
    if (!value) return null;
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    const deltaMs = Date.now() - d.getTime();
    const deltaMin = Math.floor(deltaMs / 60000);
    if (deltaMin <= 0) return 'Just now';
    if (deltaMin === 1) return '1 min ago';
    if (deltaMin < 60) return `${deltaMin} mins ago`;
    const deltaHr = Math.floor(deltaMin / 60);
    if (deltaHr === 1) return '1 hour ago';
    if (deltaHr < 24) return `${deltaHr} hours ago`;
    const deltaDay = Math.floor(deltaHr / 24);
    if (deltaDay === 1) return '1 day ago';
    return `${deltaDay} days ago`;
  };

  const rowUi = (band) => {
    if (band === 'urgent') {
      return {
        scoreCls: 'bg-primary text-white',
        icon: { name: 'error', cls: 'text-red-500', title: 'Urgent' },
        barCls: 'bg-primary',
        rowBorder: 'hover:border-primary',
      };
    }
    if (band === 'high') {
      return {
        scoreCls: 'bg-primary/20 text-primary dark:bg-primary/30 dark:text-white',
        icon: { name: 'warning', cls: 'text-orange-500', title: 'High Priority' },
        barCls: 'bg-primary/60',
        rowBorder: 'hover:border-primary',
      };
    }
    if (band === 'normal') {
      return {
        scoreCls: 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-slate-300',
        icon: { name: 'fiber_manual_record', cls: 'text-primary/40', title: 'Normal' },
        barCls: 'bg-primary/30',
        rowBorder: 'hover:border-primary',
      };
    }
    return {
      scoreCls: 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-slate-300',
      icon: { name: 'low_priority', cls: 'text-primary/40', title: 'Low' },
      barCls: 'bg-primary/30',
      rowBorder: 'hover:border-primary',
    };
  };

  const formatDeadline = (deadline) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString();
  };

  return (
    <div className="w-full h-fit bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-[#eae6f4] dark:border-slate-800 flex flex-col overflow-hidden">
      <style>{`.custom-scrollbar::-webkit-scrollbar{width:4px}.custom-scrollbar::-webkit-scrollbar-track{background:transparent}.custom-scrollbar::-webkit-scrollbar-thumb{background:#d5cee9;border-radius:10px}`}</style>

      <div className="px-4 pt-5 pb-3 flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <h2 className="text-[#110d1c] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
            AI Schedule
          </h2>
          <div className="flex gap-1">
            <button
              className="size-8 flex items-center justify-center rounded-lg hover:bg-background-light dark:hover:bg-slate-800 text-[#5d479e] dark:text-slate-400 disabled:opacity-60"
              onClick={() => load({ silent: false })}
              disabled={isLoading}
              type="button"
            >
              <span className="material-symbols-outlined text-[18px]">sync</span>
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`flex h-2 w-2 rounded-full ${
              error ? 'bg-red-500' : isRefreshing ? 'bg-primary' : 'bg-green-500'
            }`}
          ></span>
          <p className="text-[#5d479e] dark:text-slate-400 text-xs font-medium uppercase tracking-wider">
            {error ? 'AI Error' : 'AI Optimized'} • {formatRelative(schedule?.generated_at) || '—'}
          </p>
        </div>
        {error ? (
          <div className="mt-3 p-3 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        ) : null}
      </div>

      <div className="px-4 py-3 flex gap-2 border-b border-[#eae6f4] dark:border-slate-800">
        <div className="flex-1 flex flex-col gap-0.5 p-2 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50">
          <span className="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase">Urgent</span>
          <span className="text-lg font-bold text-red-700 dark:text-red-300">{stats.urgent}</span>
        </div>
        <div className="flex-1 flex flex-col gap-0.5 p-2 rounded-lg bg-orange-50 dark:bg-orange-950/30 border border-orange-100 dark:border-orange-900/50">
          <span className="text-[10px] font-bold text-orange-600 dark:text-orange-400 uppercase">High</span>
          <span className="text-lg font-bold text-orange-700 dark:text-orange-300">{stats.high}</span>
        </div>
        <div className="flex-1 flex flex-col gap-0.5 p-2 rounded-lg bg-primary/5 dark:bg-primary/10 border border-primary/10 dark:border-primary/20">
          <span className="text-[10px] font-bold text-primary dark:text-primary/80 uppercase">Normal</span>
          <span className="text-lg font-bold text-primary dark:text-white">{stats.normal}</span>
        </div>
      </div>

      <div className="flex flex-col custom-scrollbar overflow-y-auto max-h-[500px]">
        {isLoading ? (
          <div className="p-4 text-[#5d479e] dark:text-slate-400 text-sm">Loading schedule...</div>
        ) : items.length === 0 ? (
          <div className="p-4 text-[#5d479e] dark:text-slate-400 text-sm">No pending tasks to schedule.</div>
        ) : (
          items.map((row) => {
            const task = row?.task;
            if (!task?.id) return null;
            const pct = Math.round((Number(row?.priority || 0) || 0) * 100);
            const ui = rowUi(row?.band);
            return (
              <div
                key={task.id}
                className={`group flex items-start gap-3 p-4 border-l-4 border-transparent transition-all cursor-pointer border-b border-[#f1eff7] dark:border-slate-800 ${ui.rowBorder}`}
                onClick={() => navigate(`/task/${task.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(`/task/${task.id}`);
                  }
                }}
              >
                <div className={`shrink-0 flex flex-col items-center justify-center size-10 rounded font-bold text-sm shadow-sm ${ui.scoreCls}`}>
                  {pct}
                </div>
                <div className="flex flex-col flex-1 min-w-0">
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-[#110d1c] dark:text-slate-100 text-sm font-semibold truncate">{task.title || 'Task'}</p>
                    <span
                      className={`material-symbols-outlined ${ui.icon.cls} text-[14px] shrink-0`}
                      title={ui.icon.title}
                    >
                      {ui.icon.name}
                    </span>
                  </div>
                  <p className="text-[#5d479e] dark:text-slate-400 text-xs mt-0.5">
                    {formatDeadline(task.deadline) ? `Due ${formatDeadline(task.deadline)}` : 'No deadline'}
                    {typeof task.points === 'number' ? ` • ${task.points} pts` : ''}
                  </p>
                  <div className="mt-2 w-full bg-[#eae6f4] dark:bg-slate-700 h-1 rounded-full overflow-hidden">
                    <div className={`${ui.barCls} h-full`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="p-3 bg-background-light/50 dark:bg-slate-800/50 flex justify-center">
        <button
          className="flex items-center gap-2 text-primary dark:text-primary hover:text-primary/80 text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-60"
          onClick={() => load({ silent: false })}
          disabled={isLoading}
          type="button"
        >
          View Full Schedule
          <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
        </button>
      </div>
    </div>
  );
};

export default AISchedule;

