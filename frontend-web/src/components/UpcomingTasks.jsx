import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const UpcomingTasks = ({ days = 14, limit = 8 }) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');
  const inFlightRef = useRef(false);

  const items = useMemo(() => data?.items || [], [data]);

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

  const formatDue = (deadline) => {
    if (!deadline) return '';
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return '';
    const deltaMs = d.getTime() - Date.now();
    const mins = Math.floor(deltaMs / 60000);
    if (mins < 60) return `Due in ${Math.max(mins, 0)}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `Due in ${hrs}h`;
    const days = Math.floor(hrs / 24);
    return `Due in ${days}d`;
  };

  const barCls = (band) => {
    if (band === 'urgent') return 'bg-red-500';
    if (band === 'high') return 'bg-orange-500';
    return 'bg-primary';
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
      const response = await api.get('/dashboard/upcoming', { params: { days, limit } });
      setData(response.data);
      setError('');
    } catch (err) {
      if (!silent) setError(getErrorMessage(err, 'Failed to load upcoming tasks'));
    } finally {
      inFlightRef.current = false;
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, [days, limit]);

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
  }, [days, limit]);

  return (
    <div className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 overflow-hidden">
      <div className="bg-primary/5 px-5 py-4 border-b border-[#d5cee9] dark:border-white/10">
        <div className="flex items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 font-bold text-[#110d1c] dark:text-white">
            <span className="material-symbols-outlined">calendar_today</span>Upcoming Tasks
          </h3>
          <div className="flex items-center gap-2">
            <span className={`flex h-2 w-2 rounded-full ${error ? 'bg-red-500' : isRefreshing ? 'bg-primary' : 'bg-green-500'}`}></span>
            <button
              className="text-xs font-bold text-primary hover:opacity-80 transition-opacity disabled:opacity-60"
              onClick={() => load({ silent: false })}
              disabled={isLoading}
              type="button"
            >
              Refresh
            </button>
          </div>
        </div>
        {error ? <div className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</div> : null}
      </div>

      <div className="p-2">
        {isLoading ? (
          <div className="p-4 text-[#5d479e] dark:text-gray-400 text-sm">Loading...</div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center px-4">
            <div className="h-12 w-12 rounded-full bg-background-light dark:bg-white/5 flex items-center justify-center text-[#5d479e]/30 mb-2">
              <span className="material-symbols-outlined text-3xl">pending_actions</span>
            </div>
            <p className="text-xs font-medium text-[#5d479e] dark:text-gray-400">Upcoming tasks will show up here.</p>
          </div>
        ) : (
          items.map((it) => (
            <div
              key={it.task_id}
              className="flex items-center gap-4 p-3 rounded-lg hover:bg-background-light transition-colors dark:hover:bg-white/5 cursor-pointer"
              onClick={() => navigate(`/task/${it.task_id}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  navigate(`/task/${it.task_id}`);
                }
              }}
            >
              <div className={`h-10 w-1 ${barCls(it.band)} rounded-full`}></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold dark:text-white truncate">{it.title || 'Task'}</p>
                <p className="text-xs text-[#5d479e] dark:text-gray-400">{formatDue(it.deadline)}</p>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-4 border-t border-[#d5cee9] dark:border-white/10 bg-background-light/30 dark:bg-white/5">
        <button
          className="w-full rounded-lg py-2 text-sm font-bold text-primary hover:bg-primary/5 transition-colors"
          onClick={() => navigate('/calendar')}
          type="button"
        >
          View Calendar
        </button>
      </div>
    </div>
  );
};

export default UpcomingTasks;

