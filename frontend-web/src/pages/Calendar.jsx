import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import MonthCalendar, { toDayKey } from '../components/calendar/MonthCalendar';

const Calendar = () => {
  const navigate = useNavigate();
  const { userRole } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [monthDate, setMonthDate] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(() => new Date());

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

  const tasksWithDeadlines = useMemo(() => {
    return (tasks || [])
      .filter((t) => t?.deadline)
      .map((t) => {
        const d = new Date(t.deadline);
        return { ...t, _deadlineDate: d };
      })
      .filter((t) => !Number.isNaN(t._deadlineDate.getTime()))
      .sort((a, b) => a._deadlineDate.getTime() - b._deadlineDate.getTime());
  }, [tasks]);

  const eventsByDayKey = useMemo(() => {
    const map = {};
    for (const t of tasksWithDeadlines) {
      const key = toDayKey(t._deadlineDate);
      if (!map[key]) map[key] = [];
      map[key].push(t);
    }
    return map;
  }, [tasksWithDeadlines]);

  const selectedKey = useMemo(() => toDayKey(selectedDate), [selectedDate]);
  const selectedEvents = useMemo(() => {
    const list = eventsByDayKey?.[selectedKey];
    return Array.isArray(list) ? list : [];
  }, [eventsByDayKey, selectedKey]);

  const formatTime = (value) => {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  };

  const monthTitle = useMemo(() => {
    const d = new Date(monthDate);
    d.setDate(1);
    return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }, [monthDate]);

  const jumpToToday = () => {
    const now = new Date();
    setMonthDate(now);
    setSelectedDate(now);
  };

  const prevMonth = () => {
    const d = new Date(monthDate);
    d.setDate(1);
    d.setMonth(d.getMonth() - 1);
    setMonthDate(d);
  };

  const nextMonth = () => {
    const d = new Date(monthDate);
    d.setDate(1);
    d.setMonth(d.getMonth() + 1);
    setMonthDate(d);
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
        ) : (
          <div className="space-y-4">
            {tasksWithDeadlines.length === 0 ? (
              <div className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 p-5 text-sm text-[#5d479e] dark:text-gray-400">
                No dated tasks yet. Add deadlines to tasks to see them on the calendar.
              </div>
            ) : null}

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
              <MonthCalendar
                monthDate={monthDate}
                selectedDate={selectedDate}
                onSelectDate={(d) => {
                  setSelectedDate(d);
                  const md = new Date(monthDate);
                  if (d.getMonth() !== md.getMonth() || d.getFullYear() !== md.getFullYear()) {
                    setMonthDate(d);
                  }
                }}
                onPrevMonth={prevMonth}
                onNextMonth={nextMonth}
                onToday={jumpToToday}
                eventsByDayKey={eventsByDayKey}
              />

              <div className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 overflow-hidden h-fit">
                <div className="px-5 py-4 border-b border-[#d5cee9] dark:border-white/10 bg-background-light/30 dark:bg-white/5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-bold text-[#110d1c] dark:text-white truncate">Agenda</div>
                      <div className="text-xs text-[#5d479e] dark:text-gray-400 truncate">
                        {selectedDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}{' '}
                        • {monthTitle}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="text-sm font-bold text-primary hover:opacity-80"
                      onClick={jumpToToday}
                    >
                      Today
                    </button>
                  </div>
                </div>

                {selectedEvents.length === 0 ? (
                  <div className="p-5 text-sm text-[#5d479e] dark:text-gray-400">No tasks due this day.</div>
                ) : (
                  <div className="divide-y divide-[#eeeaf6] dark:divide-white/10">
                    {selectedEvents.map((t) => (
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
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Calendar;
