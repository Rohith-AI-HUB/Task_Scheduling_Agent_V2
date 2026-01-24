import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const TeacherClassrooms = () => {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copyState, setCopyState] = useState({ id: null, copiedAt: 0 });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await api.get('/subjects');
        if (cancelled) return;
        setSubjects(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        if (cancelled) return;
        setError(err?.response?.data?.detail || 'Failed to load classrooms');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredSubjects = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return subjects;
    return subjects.filter((s) => {
      const name = String(s?.name || '').toLowerCase();
      const code = String(s?.code || '').toLowerCase();
      const join = String(s?.join_code || '').toLowerCase();
      return name.includes(q) || code.includes(q) || join.includes(q);
    });
  }, [subjects, query]);

  const copyJoinCode = async (subject) => {
    const joinCode = String(subject?.join_code || '').trim();
    if (!joinCode) return;
    try {
      await navigator.clipboard.writeText(joinCode);
      setCopyState({ id: subject.id, copiedAt: Date.now() });
      window.setTimeout(() => {
        setCopyState((prev) => (prev.id === subject.id ? { id: null, copiedAt: 0 } : prev));
      }, 1500);
    } catch {
      setError('Failed to copy join code');
    }
  };

  return (
    <div className="min-h-screen bg-surface text-slate-900 font-sans antialiased">
      <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-[1440px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-primary p-1.5 rounded-lg text-white">
              <span className="material-symbols-outlined block">school</span>
            </div>
            <div>
              <div className="font-bold text-lg tracking-tight">Classrooms</div>
              <div className="text-xs text-slate-500">{filteredSubjects.length} total</div>
            </div>
          </div>
          <button
            className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-primary"
            onClick={() => navigate('/teacher/dashboard')}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
            Back
          </button>
        </div>
      </header>

      <main className="max-w-[1440px] mx-auto p-6">
        {error ? (
          <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 text-sm">
            {error}
          </div>
        ) : null}

        <div className="mb-6 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-md">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
              search
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search classrooms..."
              className="w-full pl-9 pr-4 py-2.5 bg-slate-100 border border-slate-200/0 rounded-xl text-sm focus:ring-2 focus:ring-primary/20 outline-none"
            />
          </div>
          <button
            className="h-10 px-4 rounded-xl bg-primary text-white font-semibold hover:bg-primary/90"
            onClick={() => navigate('/teacher/dashboard')}
            type="button"
          >
            Create Classroom
          </button>
        </div>

        {loading ? (
          <div className="text-slate-600">Loading...</div>
        ) : filteredSubjects.length === 0 ? (
          <div className="bento-card p-10 text-center">
            <div className="mx-auto mb-3 w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <span className="material-symbols-outlined text-3xl">school</span>
            </div>
            <div className="font-bold text-slate-800">No classrooms found</div>
            <div className="text-sm text-slate-500 mt-1">Try a different search.</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSubjects.map((subject) => (
              <div key={subject.id} className="bento-card p-6 flex flex-col gap-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                        {subject.code || 'NO CODE'}
                      </span>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        {Number(subject.task_count) || 0} tasks
                      </span>
                    </div>
                    <button
                      className="mt-2 text-left font-bold text-slate-800 hover:text-primary transition-colors line-clamp-1"
                      onClick={() => navigate(`/subject/${subject.id}`)}
                      type="button"
                    >
                      {subject.name}
                    </button>
                    <div className="mt-1 text-xs text-slate-500">
                      {Number(subject.student_count) || 0} students
                    </div>
                  </div>
                  <button
                    className="shrink-0 h-9 w-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 hover:text-primary"
                    onClick={() => navigate(`/subject/${subject.id}`)}
                    type="button"
                    title="Open"
                  >
                    <span className="material-symbols-outlined text-lg">arrow_forward</span>
                  </button>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-3 py-2 rounded-lg">
                    JOIN: {subject.join_code}
                  </div>
                  <button
                    className="text-xs font-bold text-primary hover:underline"
                    onClick={() => copyJoinCode(subject)}
                    type="button"
                  >
                    {copyState.id === subject.id ? 'COPIED' : 'COPY'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default TeacherClassrooms;
