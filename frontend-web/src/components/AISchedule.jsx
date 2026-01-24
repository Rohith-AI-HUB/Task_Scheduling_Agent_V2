import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const AISchedule = () => {
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const inFlightRef = useRef(false);

  const load = async ({ silent = false } = {}) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    if (!silent) {
      setIsLoading(true);
      setError('');
    }
    try {
      const response = await api.get('/ai/schedule');
      setSchedule(response.data);
      setError('');
    } catch (err) {
      if (!silent) setError('Failed to load AI schedule');
    } finally {
      inFlightRef.current = false;
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const items = useMemo(() => schedule?.tasks || [], [schedule]);

  const stats = useMemo(() => {
    const out = { urgent: 0, high: 0, normal: 0 };
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
    if (deltaMin < 60) return `${deltaMin} mins ago`;
    const deltaHr = Math.floor(deltaMin / 60);
    if (deltaHr < 24) return `${deltaHr} hours ago`;
    return '1 day+ ago';
  };

  const formatDeadline = (deadline) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString();
  };

  return (
    <div className="bento-card p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">auto_awesome</span>
          AI Schedule
        </h2>
        <button
          className={`size-9 flex items-center justify-center rounded-lg hover:bg-slate-50 text-slate-500 transition-colors ${isLoading ? 'animate-spin' : ''}`}
          onClick={() => load({ silent: false })}
          title="Refresh"
          type="button"
        >
          <span className="material-symbols-outlined text-[18px]">sync</span>
        </button>
      </div>

      <div className="text-[10px] font-bold uppercase tracking-widest flex items-center gap-2 mb-4 text-slate-500">
        <span className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'}`}></span>
        {error ? 'Error' : 'AI optimized'}
        <span className="opacity-60">•</span>
        <span className="truncate">{formatRelative(schedule?.generated_at)?.toUpperCase() || 'UNKNOWN'}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-red-50 p-3 rounded-2xl border border-red-100">
          <p className="text-[9px] font-bold text-red-600 uppercase tracking-wider mb-1">Urgent</p>
          <p className="text-2xl font-bold text-red-700">{stats.urgent}</p>
        </div>
        <div className="bg-orange-50 p-3 rounded-2xl border border-orange-100">
          <p className="text-[9px] font-bold text-orange-600 uppercase tracking-wider mb-1">High</p>
          <p className="text-2xl font-bold text-orange-700">{stats.high}</p>
        </div>
        <div className="bg-indigo-50 p-3 rounded-2xl border border-indigo-100">
          <p className="text-[9px] font-bold text-indigo-600 uppercase tracking-wider mb-1">Normal</p>
          <p className="text-2xl font-bold text-indigo-700">{stats.normal}</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-[160px] space-y-3 mb-4 pr-1 custom-scrollbar">
        {isLoading && !schedule ? (
          <div className="text-center text-slate-500 text-sm py-10">Loading schedule...</div>
        ) : items.length === 0 ? (
          <div className="text-center text-slate-500 text-sm py-10">No tasks scheduled.</div>
        ) : (
          items.slice(0, 5).map((row, idx) => {
            const task = row?.task;
            if (!task) return null;
            const isUrgent = row.band === 'urgent';
            const isHigh = row.band === 'high';
            const iconColor = isUrgent ? 'text-red-500' : isHigh ? 'text-orange-500' : 'text-primary';
            const icon = isUrgent ? 'error' : isHigh ? 'warning' : 'fiber_manual_record';

            return (
              <button
                key={task.id || idx}
                className="w-full text-left p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white hover:border-primary/30 transition-colors"
                onClick={() => navigate(`/task/${task.id}`)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-primary">{Math.round(Number(row.priority) * 100)}</span>
                      <p className="font-bold text-sm text-slate-800 truncate">{task.title}</p>
                    </div>
                    <p className="text-[11px] text-slate-500 truncate">
                      Due {formatDeadline(task.deadline)} {typeof task.points === 'number' ? `• ${task.points} pts` : ''}
                    </p>
                  </div>
                  <span className={`material-symbols-outlined ${iconColor} text-[18px]`}>{icon}</span>
                </div>
              </button>
            );
          })
        )}
      </div>

      <button
        className="w-full rounded-lg py-2 text-sm font-bold text-primary hover:bg-primary/5 transition-colors mt-auto"
        onClick={() => navigate('/calendar')}
        type="button"
      >
        View Calendar
      </button>
    </div>
  );
};

export default AISchedule;
