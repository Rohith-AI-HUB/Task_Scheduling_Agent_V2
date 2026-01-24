import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const DueSoon = ({ days = 7, limit = 5 }) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');
  const inFlightRef = useRef(false);

  const items = useMemo(() => data?.items || [], [data]);

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
      const response = await api.get('/dashboard/due-soon', { params: { days, limit } });
      setData(response.data);
      setError('');
    } catch (err) {
      if (!silent) setError('Failed to load tasks');
    } finally {
      inFlightRef.current = false;
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, [days, limit]);

  const formatDue = (deadline) => {
    if (!deadline) return '';
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return '';
    const deltaMs = d.getTime() - Date.now();
    const mins = Math.floor(deltaMs / 60000);
    if (mins < 0) {
      const over = Math.abs(mins);
      if (over < 60) return `Overdue by ${over}m`;
      const hrs = Math.floor(over / 60);
      if (hrs < 24) return `Overdue by ${hrs}h`;
      const days = Math.floor(hrs / 24);
      return `Overdue by ${days}d`;
    }
    if (mins < 60) return `Due in ${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `Due in ${hrs}h`;
    const days = Math.floor(hrs / 24);
    return `Due in ${days}d`;
  };

  return (
    <div className="bento-card p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
          <span className="material-symbols-outlined text-orange-500">warning</span>
          Due Soon
        </h3>
        <button
          onClick={() => load({ silent: false })}
          className="text-primary text-sm font-bold hover:underline flex items-center gap-2 disabled:opacity-60"
          disabled={isLoading}
          type="button"
        >
          <span className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : isRefreshing ? 'bg-primary' : 'bg-green-500'} ${isRefreshing ? 'animate-pulse' : ''}`}></span>
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="text-sm text-slate-500 py-8 text-center">Loading...</div>
      ) : error ? (
        <div className="text-sm text-red-600 py-6 text-center">{error}</div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center">
          <div className="text-slate-800 font-semibold">No urgent tasks</div>
          <div className="text-xs text-slate-500 mt-1">You're all caught up.</div>
        </div>
      ) : (
        <div className="space-y-2">
          {items.slice(0, 3).map((item) => (
            <button
              key={item.task_id}
              className="w-full text-left p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white hover:border-primary/30 transition-colors"
              onClick={() => navigate(`/task/${item.task_id}`)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-bold text-sm text-slate-800 truncate">{item.title}</div>
                  <div className="text-xs text-slate-500 mt-1">{formatDue(item.deadline)}</div>
                </div>
                <span className="material-symbols-outlined text-orange-500 text-[18px]">event</span>
              </div>
            </button>
          ))}
        </div>
      )}

      <button
        className="mt-4 w-full rounded-lg py-2 text-sm font-bold text-primary hover:bg-primary/5 transition-colors"
        onClick={() => navigate('/calendar')}
        type="button"
      >
        View Calendar
      </button>
    </div>
  );
};

export default DueSoon;
