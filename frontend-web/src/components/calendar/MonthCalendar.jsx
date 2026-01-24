import { useMemo } from 'react';

const toDayKey = (d) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const startOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);

const isSameDay = (a, b) => {
  if (!a || !b) return false;
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
};

const getMondayIndex = (d) => (d.getDay() + 6) % 7;

const MonthCalendar = ({
  monthDate,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  onToday,
  eventsByDayKey,
} = {}) => {
  const monthStart = useMemo(() => startOfMonth(monthDate || new Date()), [monthDate]);

  const monthLabel = useMemo(() => {
    return monthStart.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }, [monthStart]);

  const weekLabels = useMemo(() => {
    const base = new Date(2024, 0, 1);
    return Array.from({ length: 7 }).map((_, idx) => {
      const d = new Date(base);
      d.setDate(base.getDate() + idx);
      return d.toLocaleDateString(undefined, { weekday: 'short' });
    });
  }, []);

  const gridDays = useMemo(() => {
    const first = monthStart;
    const firstOffset = getMondayIndex(first);
    const start = new Date(first);
    start.setDate(first.getDate() - firstOffset);
    return Array.from({ length: 42 }).map((_, idx) => {
      const d = new Date(start);
      d.setDate(start.getDate() + idx);
      return d;
    });
  }, [monthStart]);

  const todayKey = useMemo(() => toDayKey(new Date()), []);

  return (
    <div className="rounded-xl border border-[#d5cee9] bg-white dark:bg-white/5 dark:border-white/10 overflow-hidden">
      <div className="px-5 py-4 border-b border-[#d5cee9] dark:border-white/10 bg-background-light/30 dark:bg-white/5 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="font-bold text-[#110d1c] dark:text-white truncate">{monthLabel}</div>
          <div className="text-xs text-[#5d479e] dark:text-gray-400">Click a day to see tasks</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            className="h-9 px-3 rounded-lg border border-[#d5cee9] dark:border-white/10 text-sm font-semibold hover:bg-background-light dark:hover:bg-white/5 transition-colors"
            onClick={onToday}
          >
            Today
          </button>
          <button
            type="button"
            className="size-9 flex items-center justify-center rounded-lg border border-[#d5cee9] dark:border-white/10 hover:bg-background-light dark:hover:bg-white/5 transition-colors"
            onClick={onPrevMonth}
            title="Previous month"
          >
            <span className="material-symbols-outlined text-[20px]">chevron_left</span>
          </button>
          <button
            type="button"
            className="size-9 flex items-center justify-center rounded-lg border border-[#d5cee9] dark:border-white/10 hover:bg-background-light dark:hover:bg-white/5 transition-colors"
            onClick={onNextMonth}
            title="Next month"
          >
            <span className="material-symbols-outlined text-[20px]">chevron_right</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 border-b border-[#eeeaf6] dark:border-white/10">
        {weekLabels.map((label) => (
          <div
            key={label}
            className="px-3 py-2 text-[11px] font-bold text-[#5d479e] dark:text-gray-400 uppercase tracking-wider"
          >
            {label}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {gridDays.map((d) => {
          const key = toDayKey(d);
          const isInMonth = d.getMonth() === monthStart.getMonth();
          const isToday = key === todayKey;
          const isSelected = isSameDay(d, selectedDate);
          const events = eventsByDayKey?.[key] || [];
          const eventCount = Array.isArray(events) ? events.length : 0;

          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelectDate?.(d)}
              className={[
                'min-h-[88px] px-2 py-2 text-left border-b border-r border-[#eeeaf6] dark:border-white/10 transition-colors',
                'hover:bg-background-light dark:hover:bg-white/5',
                isSelected ? 'bg-primary/5' : '',
              ].join(' ')}
            >
              <div className="flex items-start justify-between gap-2">
                <div
                  className={[
                    'h-7 w-7 flex items-center justify-center rounded-full text-sm font-bold',
                    isInMonth ? 'text-[#110d1c] dark:text-white' : 'text-[#5d479e] dark:text-gray-400 opacity-60',
                    isToday ? 'ring-2 ring-primary/40' : '',
                    isSelected ? 'bg-primary text-white ring-0' : '',
                  ].join(' ')}
                >
                  {d.getDate()}
                </div>
                {eventCount > 0 ? (
                  <div className="text-[11px] font-bold text-primary">{eventCount}</div>
                ) : null}
              </div>

              {eventCount > 0 ? (
                <div className="mt-2 space-y-1">
                  {events.slice(0, 2).map((e) => (
                    <div
                      key={e.id}
                      className="text-[11px] text-[#5d479e] dark:text-gray-400 truncate"
                      title={e.title || 'Task'}
                    >
                      {e.title || 'Task'}
                    </div>
                  ))}
                  {eventCount > 2 ? (
                    <div className="text-[11px] text-[#5d479e] dark:text-gray-400 font-semibold">
                      +{eventCount - 2} more
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="mt-2 text-[11px] text-[#5d479e] dark:text-gray-400 opacity-0">.</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export { toDayKey };
export default MonthCalendar;

