import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';

const normalizeTaskType = (value) => {
  const v = String(value || '').trim().toLowerCase();
  if (!v) return 'Assignment';
  if (v === 'quiz') return 'Quiz';
  if (v === 'assignment') return 'Assignment';
  if (v === 'project') return 'Project';
  if (v === 'extra credit' || v === 'extracredit' || v === 'extra_credit') return 'Extra Credit';
  return 'Assignment';
};

const formatDateTime = (value) => {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString();
};

const formatFixed2 = (value) => {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return '0.00';
  return n.toFixed(2);
};

const getErrorMessage = (err, fallback) => err?.userMessage || err?.response?.data?.detail || err?.message || fallback;

const TeacherStudentMarks = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { subjectId, studentUid } = useParams();

  const [activeTab, setActiveTab] = useState('Quiz');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [subject, setSubject] = useState(null);
  const [student, setStudent] = useState(location?.state?.student || null);
  const [items, setItems] = useState([]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!subjectId || !studentUid) return;
      setLoading(true);
      setError('');
      try {
        const [subjectRes, marksRes, studentRes] = await Promise.all([
          api.get(`/subjects/${subjectId}`),
          api.get('/submissions/student-marks', { params: { subject_id: subjectId, student_uid: studentUid } }),
          student ? Promise.resolve(null) : api.get(`/auth/users/${studentUid}`),
        ]);

        if (cancelled) return;

        setSubject(subjectRes?.data || null);
        setItems(Array.isArray(marksRes?.data) ? marksRes.data : []);
        if (!student && studentRes?.data) {
          setStudent(studentRes.data);
        }
      } catch (err) {
        if (cancelled) return;
        setError(getErrorMessage(err, 'Failed to load marks'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [subjectId, studentUid, student]);

  const tabs = useMemo(() => ['Quiz', 'Assignment', 'Project', 'Extra Credit'], []);

  const tabCounts = useMemo(() => {
    const counts = { Quiz: 0, Assignment: 0, Project: 0, 'Extra Credit': 0 };
    for (const it of items) {
      const key = normalizeTaskType(it?.task_type);
      if (counts[key] === undefined) continue;
      counts[key] += 1;
    }
    return counts;
  }, [items]);

  useEffect(() => {
    const activeCount = tabCounts[activeTab] || 0;
    if (activeCount > 0) return;
    const firstNonEmpty = tabs.find((t) => (tabCounts[t] || 0) > 0);
    if (firstNonEmpty && firstNonEmpty !== activeTab) setActiveTab(firstNonEmpty);
  }, [activeTab, tabCounts, tabs]);

  const filtered = useMemo(() => {
    return items.filter((it) => normalizeTaskType(it?.task_type) === activeTab);
  }, [items, activeTab]);

  const studentName = student?.name || String(studentUid || '');
  const studentEmail = student?.email || '';

  return (
    <div className="min-h-screen bg-surface text-slate-900 font-sans antialiased">
      <nav className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <button
            className="flex items-center justify-center rounded-lg size-10 bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
            onClick={() => navigate(`/subject/${subjectId}`)}
            type="button"
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <div className="min-w-0">
            <div className="font-bold text-slate-900 truncate">
              {subject?.name ? `${subject.name} • Marks` : 'Marks'}
            </div>
            <div className="text-xs text-slate-500 truncate">{studentName}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-bold text-slate-700 hover:border-primary/40 transition-colors"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(String(studentUid || ''));
              } catch {}
            }}
            type="button"
          >
            Copy UID
          </button>
        </div>
      </nav>

      <main className="max-w-[1200px] mx-auto p-6">
        {error ? (
          <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 text-sm">{error}</div>
        ) : null}

        <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
              {(String(studentName || '').slice(0, 2) || 'ST').toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="font-bold text-[#110d1c] truncate">{studentName}</div>
              {studentEmail ? <div className="text-xs text-gray-500 truncate">{studentEmail}</div> : null}
              <div className="text-xs text-gray-500 truncate">{studentUid}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {tabs.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setActiveTab(t)}
                className={`px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${
                  activeTab === t
                    ? 'bg-primary text-white border-primary'
                    : 'bg-white/60 border-slate-200 text-slate-700 hover:border-primary/40'
                }`}
              >
                {t}
                <span className={`ml-2 text-xs font-extrabold ${activeTab === t ? 'text-white/90' : 'text-slate-500'}`}>
                  {tabCounts[t] || 0}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-[#1c1633] rounded-xl border border-[#eae6f4] dark:border-[#2d2644] overflow-hidden">
          <div className="p-6 border-b border-[#eae6f4] dark:border-[#2d2644] flex items-center justify-between gap-3">
            <div className="font-bold text-[#110d1c] dark:text-white">{activeTab}</div>
            {loading ? <div className="text-xs text-gray-500 dark:text-gray-400">Loading...</div> : null}
          </div>
          <div className="p-6">
            {loading ? (
              <div className="text-gray-600 dark:text-gray-300">Loading marks...</div>
            ) : filtered.length === 0 ? (
              <div className="text-gray-600 dark:text-gray-300">No items found.</div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {filtered.map((it) => {
                  const points = typeof it?.task_points === 'number' ? it.task_points : null;
                  const score = typeof it?.score === 'number' ? it.score : null;
                  const aiScore = typeof it?.ai_score === 'number' ? it.ai_score : null;
                  const isGraded = score !== null;
                  const maxText = formatFixed2(points);
                  const markText = score !== null ? `${formatFixed2(score)} / ${maxText}` : `— / ${maxText}`;
                  const statusText = isGraded ? 'Graded' : 'Ungraded';

                  return (
                    <div
                      key={it?.task_id}
                      className="p-4 rounded-xl border border-[#eae6f4] dark:border-[#2d2644] bg-white/50 dark:bg-white/5 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <div className="font-bold text-[#110d1c] dark:text-white truncate">{it?.task_title || 'Untitled'}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {it?.submitted_at ? `Submitted: ${formatDateTime(it.submitted_at)}` : 'Not submitted'}
                        </div>
                        {aiScore !== null ? (
                          <div className="text-xs text-gray-500 dark:text-gray-400">AI Score: {aiScore} / 100</div>
                        ) : null}
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-bold">
                          Marks: {markText}
                        </span>
                        <span
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
                            isGraded
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                          }`}
                        >
                          {statusText}
                        </span>
                        <button
                          type="button"
                          className="px-3 py-2 rounded-lg border border-[#eae6f4] dark:border-[#2d2644] text-xs font-bold text-gray-600 dark:text-gray-300 hover:border-primary/40 transition-colors"
                          onClick={() => navigate(`/task/${it.task_id}`)}
                        >
                          View Task
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default TeacherStudentMarks;
