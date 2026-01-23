import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { logout } from '../services/authService';
import ExtensionRequests from '../components/ExtensionRequests';


const TeacherDashboard = () => {
  const { currentUser, backendUser } = useAuth();
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const inFlightRef = useRef(false);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [upcomingLoading, setUpcomingLoading] = useState(true);
  const [upcomingRefreshing, setUpcomingRefreshing] = useState(false);
  const [upcomingError, setUpcomingError] = useState('');
  const upcomingInFlightRef = useRef(false);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createCode, setCreateCode] = useState('');
  const [createError, setCreateError] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const [editSubject, setEditSubject] = useState(null);
  const [editName, setEditName] = useState('');
  const [editCode, setEditCode] = useState('');
  const [editError, setEditError] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const [copyState, setCopyState] = useState({ subjectId: null, copiedAt: 0 });

  const resolvePhotoUrl = (photoUrl) => {
    if (!photoUrl) return '';
    const u = String(photoUrl);
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    const root = String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');
    return `${root}${u}`;
  };

  const loadSubjects = async ({ silent } = {}) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
      setLoadError('');
    }
    try {
      const response = await api.get('/subjects');
      setSubjects(response.data || []);
    } catch (err) {
      if (!silent) setLoadError(err?.response?.data?.detail || 'Failed to load classrooms');
    } finally {
      inFlightRef.current = false;
      if (silent) {
        setIsRefreshing(false);
      } else {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    loadSubjects({ silent: false });
  }, []);

  const loadUpcomingTasks = async ({ silent } = {}) => {
    if (upcomingInFlightRef.current) return;
    upcomingInFlightRef.current = true;

    if (silent) {
      setUpcomingRefreshing(true);
    } else {
      setUpcomingLoading(true);
      setUpcomingError('');
    }

    try {
      const res = await api.get('/dashboard/teacher/upcoming', { params: { days: 14, limit: 6 } });
      setUpcomingTasks(res.data?.items || []);
    } catch (err) {
      if (!silent) setUpcomingError(err?.response?.data?.detail || 'Failed to load upcoming tasks');
    } finally {
      upcomingInFlightRef.current = false;
      if (silent) {
        setUpcomingRefreshing(false);
      } else {
        setUpcomingLoading(false);
      }
    }
  };

  useEffect(() => {
    const tick = () => {
      if (document.hidden) return;
      loadSubjects({ silent: true });
    };

    const intervalId = window.setInterval(tick, 5000);
    const onVisibility = () => {
      if (!document.hidden) tick();
    };

    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  useEffect(() => {
    loadUpcomingTasks({ silent: false });
  }, []);

  useEffect(() => {
    const tick = () => {
      if (document.hidden) return;
      loadUpcomingTasks({ silent: true });
    };

    const intervalId = window.setInterval(tick, 5000);
    const onVisibility = () => {
      if (!document.hidden) tick();
    };

    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  const filteredSubjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return subjects;
    return subjects.filter((s) => {
      const hay = `${s.name || ''} ${s.code || ''} ${s.join_code || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [subjects, search]);

  const activeSubjects = subjects.length;
  const enrolledStudents = useMemo(
    () => subjects.reduce((sum, s) => sum + (Number(s?.student_count) || 0), 0),
    [subjects]
  );

  const formatDue = (deadline) => {
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const openEdit = (subject) => {
    setEditSubject(subject);
    setEditName(subject?.name || '');
    setEditCode(subject?.code || '');
    setEditError('');
  };

  const closeEdit = () => {
    setEditSubject(null);
    setEditName('');
    setEditCode('');
    setEditError('');
    setIsEditing(false);
  };

  const handleCopyJoinCode = async (subject) => {
    const value = subject?.join_code || '';
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopyState({ subjectId: subject.id, copiedAt: Date.now() });
      window.setTimeout(() => {
        setCopyState((prev) => (prev.subjectId === subject.id ? { subjectId: null, copiedAt: 0 } : prev));
      }, 1200);
    } catch {
      setCopyState({ subjectId: null, copiedAt: 0 });
    }
  };

  return (
    <div>

      <div className="bg-surface text-slate-900 font-sans antialiased min-h-screen">
        <div className="flex flex-col min-h-screen">
          {/* Header */}
          <nav className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="bg-primary p-1.5 rounded-lg text-white">
                <span className="material-symbols-outlined block">bolt</span>
              </div>
              <span className="font-bold text-lg tracking-tight">Task Scheduling Agent</span>
            </div>
            <div className="hidden lg:flex items-center gap-4 text-sm font-medium text-slate-600 dark:text-slate-400">
              <a className="text-primary" href="#">Dashboard</a>
              <a className="hover:text-primary" href="#">Classrooms</a>
              <a className="hover:text-primary" href="#">Schedule</a>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative hidden sm:block">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">search</span>
              <input
                className="w-64 pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-slate-800 border-none rounded-full text-sm focus:ring-2 focus:ring-primary/20"
                placeholder="Search resources..."
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <button className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
                <span className="material-symbols-outlined">notifications</span>
              </button>
              <button
                className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                onClick={handleLogout}
                type="button"
                title="Logout"
              >
                <span className="material-symbols-outlined">logout</span>
              </button>
              <div className="w-9 h-9 rounded-full bg-slate-200 overflow-hidden border-2 border-white shadow-sm">
                {backendUser?.photo_url ? (
                  <img alt="User avatar" className="w-full h-full object-cover" src={resolvePhotoUrl(backendUser.photo_url)} />
                ) : (
                  <div className="w-full h-full bg-slate-200 flex items-center justify-center">
                    <span className="material-symbols-outlined text-slate-500">person</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-[1440px] mx-auto p-6">
          {(loadError || upcomingError) ? (
            <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50 rounded-lg text-red-600 dark:text-red-400 text-sm">
              {loadError || upcomingError}
            </div>
          ) : null}
          <div className="grid grid-cols-12 grid-rows-6 gap-6 h-auto lg:h-[calc(100vh-140px)] min-h-[850px]">
            {/* Welcome Card */}
            <div className="col-span-12 lg:col-span-8 row-span-2 bento-card p-8 bg-gradient-to-br from-white to-soft-purple/30 flex flex-col justify-between">
              <div>
                <span className="text-primary font-semibold text-sm bg-primary/10 px-3 py-1 rounded-full uppercase tracking-wider">Academic Portal</span>
                <h1 className="text-4xl font-bold text-slate-900 dark:text-white mt-4">Welcome back,<br/>{currentUser?.displayName || currentUser?.email || 'Teacher'}</h1>
                <p className="text-slate-500 mt-2 max-w-md">You have {subjects.length} classes today and 3 pending extension requests that need your immediate attention.</p>
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setIsCreateOpen(true)}
                  className="bg-primary text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 hover:bg-accent-purple transition-all shadow-lg shadow-primary/20">
                  <span className="material-symbols-outlined">add_circle</span>
                  Quick Action
                </button>
                <button
                  onClick={() => navigate('/calendar')}
                  className="bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 px-6 py-3 rounded-xl font-semibold hover:bg-slate-50 transition-all">
                  View Schedule
                </button>
              </div>
            </div>

            {/* AI Assistant Card */}
            <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-4 bento-card p-6 bg-primary dark:bg-primary relative overflow-hidden group flex flex-col">
              <div className="absolute -right-8 -bottom-8 opacity-10 group-hover:scale-110 transition-transform duration-500 pointer-events-none">
                <span className="material-symbols-outlined text-[160px] text-white">smart_toy</span>
              </div>
              <div className="relative z-10 flex justify-between items-center mb-6 border-b border-white/10 pb-4 shrink-0">
                <div className="flex items-center gap-3">
                  <div className="bg-white/20 p-2 rounded-lg text-white">
                    <span className="material-symbols-outlined">chat_bubble</span>
                  </div>
                  <div>
                    <h3 className="text-white font-bold text-lg leading-tight">AI Assistant</h3>
                    <span className="text-white/60 text-xs font-medium uppercase tracking-widest">Always Active</span>
                  </div>
                </div>
                <button className="text-white/70 hover:text-white transition-colors">
                  <span className="material-symbols-outlined">more_horiz</span>
                </button>
              </div>
              <div className="relative z-10 flex-1 overflow-y-auto space-y-4 pr-1 mb-4 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0 mt-1">
                    <span className="material-symbols-outlined text-sm text-white">smart_toy</span>
                  </div>
                  <div className="bg-white/10 p-3 rounded-2xl rounded-tl-none text-white text-sm backdrop-blur-sm shadow-sm">
                    Good morning! You have 3 extension requests pending. Would you like me to draft responses based on the students' history?
                  </div>
                </div>
                <div className="flex gap-3 flex-row-reverse">
                  <div className="bg-white text-primary p-3 rounded-2xl rounded-tr-none text-sm font-medium shadow-sm">
                   Yes, please highlight the ones with medical certificates first.
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0 mt-1">
                    <span className="material-symbols-outlined text-sm text-white">smart_toy</span>
                  </div>
                  <div className="bg-white/10 p-3 rounded-2xl rounded-tl-none text-white text-sm backdrop-blur-sm shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="material-symbols-outlined text-xs animate-spin">sync</span>
                      <span className="text-xs opacity-70">Processing...</span>
                    </div>
                     Checking Sarah Jenkins' attachment...
                  </div>
                </div>
              </div>
              <div className="relative z-10 mt-auto pt-2 shrink-0">
                <div className="relative flex items-center gap-2">
                  <input className="w-full bg-white/10 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-white/50 focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all backdrop-blur-md shadow-lg" placeholder="Type a message..." type="text"/>
                  <button className="absolute right-2 top-1/2 -translate-y-1/2 bg-white text-primary p-1.5 rounded-lg hover:bg-white/90 transition-colors shadow-sm">
                    <span className="material-symbols-outlined text-xl">send</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Upcoming Tasks Card */}
            <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-2 bento-card overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50">
                <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">event_note</span>
                  Upcoming
                </h3>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{upcomingRefreshing ? 'Refreshing…' : '14 Days'}</span>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {upcomingLoading ? (
                  Array.from({ length: 2 }).map((_, idx) => (
                    <div key={idx} className="h-16 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 animate-pulse"></div>
                  ))
                ) : upcomingTasks.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-500 text-center p-4">
                    No upcoming tasks
                  </div>
                ) : (
                  upcomingTasks.map((t) => (
                    <button
                      key={t.task_id}
                      className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 w-full text-left"
                      onClick={() => navigate(`/task/${t.task_id}`)}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-white shrink-0 ${
                          t.band === 'urgent'
                            ? 'bg-red-100 text-red-600'
                            : t.band === 'high'
                              ? 'bg-amber-100 text-amber-600'
                              : 'bg-blue-100 text-blue-600'
                        }`}>
                          <span className="material-symbols-outlined text-lg">
                            {t.band === 'urgent' ? 'assignment_late' : t.band === 'high' ? 'assignment_turned_in' : 'assignment'}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm leading-tight">{t.title}</h4>
                          <p className="text-[11px] text-slate-500">{t.subject_name} • {Number(t?.student_count) || 0} Students</p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded">
                          {formatDue(t.deadline)}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Pending Tasks Card */}
            <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-2 bento-card p-8 bg-slate-900 dark:bg-black text-white flex flex-col justify-between">
              <div>
                <h3 className="text-xl font-bold">Pending Tasks</h3>
                <p className="text-slate-400 text-sm mt-1">Assignments awaiting grading</p>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-6xl font-black text-primary">24</span>
                <span className="text-slate-500 font-medium">submissions</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-primary h-2 rounded-full w-3/4"></div>
              </div>
              <button className="w-full py-2.5 rounded-lg border border-slate-700 text-sm font-semibold hover:bg-slate-800 transition-colors">
                Review All
              </button>
            </div>

            {/* Your Classrooms Card */}
            <div className="col-span-12 lg:col-span-6 row-span-2 bento-card p-6 flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">school</span>
                  Your Classrooms
                </h3>
                <button
                  className="text-primary text-sm font-bold hover:underline"
                  onClick={() => setIsCreateOpen(true)}
                >
                  {isRefreshing ? 'Refreshing…' : 'View All'}
                </button>
              </div>
              <div className="flex-1 flex gap-4 overflow-x-auto pb-2 scroll-smooth">
                {isLoading ? (
                  Array.from({ length: 3 }).map((_, idx) => (
                    <div key={idx} className="min-w-[260px] bg-slate-50 dark:bg-slate-800 rounded-xl p-5 border border-slate-100 dark:border-slate-700 animate-pulse">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
                      <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-full mb-4"></div>
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
                    </div>
                  ))
                ) : filteredSubjects.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center text-slate-500">
                    No classrooms found
                  </div>
                ) : (
                  <>
                    {filteredSubjects.slice(0, 2).map((subject) => (
                      <div key={subject.id} className="min-w-[260px] bg-slate-50 dark:bg-slate-800 rounded-xl p-5 border border-slate-100 dark:border-slate-700 flex flex-col justify-between">
                        <div>
                          <div className="flex justify-between items-start mb-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                              {subject.code || 'NO-CODE'}
                            </span>
                            <button
                              className="text-slate-300 hover:text-slate-500"
                              type="button"
                              onClick={() => openEdit(subject)}
                              title="Edit"
                            >
                              <span className="material-symbols-outlined">more_vert</span>
                            </button>
                          </div>
                          <button
                            className="font-bold text-slate-800 dark:text-white text-left hover:text-primary transition-colors"
                            type="button"
                            onClick={() => navigate(`/subject/${subject.id}`)}
                          >
                            {subject.name}
                          </button>
                          <p className="text-xs text-slate-500 mt-1">Classroom</p>
                        </div>
                        <div className="mt-6 flex items-center justify-between">
                          <div className="flex -space-x-2">
                            <div className="w-6 h-6 rounded-full bg-slate-200 border-2 border-white"></div>
                            <div className="w-6 h-6 rounded-full bg-slate-300 border-2 border-white"></div>
                            <div className="w-6 h-6 rounded-full bg-slate-400 border-2 border-white"></div>
                            <div className="w-6 h-6 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[8px] font-bold">
                              +{Math.max(0, (Number(subject?.student_count) || 0) - 3)}
                            </div>
                          </div>
                          <button
                            className="text-primary font-bold text-xs"
                            onClick={() => handleCopyJoinCode(subject)}
                            type="button"
                          >
                            {copyState.subjectId === subject.id ? (
                              <span className="font-mono">COPIED</span>
                            ) : (
                              <>
                                JOIN CODE: <span className="font-mono">{subject.join_code}</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    ))}
                    <div
                      className="min-w-[180px] border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl flex flex-col items-center justify-center p-5 cursor-pointer hover:bg-slate-50 transition-colors group"
                      onClick={() => setIsCreateOpen(true)}
                    >
                      <div className="w-10 h-10 rounded-full bg-slate-100 group-hover:bg-primary/10 flex items-center justify-center text-slate-400 group-hover:text-primary mb-2 transition-all">
                        <span className="material-symbols-outlined">add</span>
                      </div>
                      <span className="text-sm font-semibold text-slate-500 group-hover:text-primary">Add New</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Stats Cards */}
            <div className="col-span-6 md:col-span-3 lg:col-span-2 row-span-2 space-y-6">
              <div className="h-[calc(50%-12px)] bento-card p-6 flex flex-col justify-center items-center text-center">
                <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-2">
                  <span className="material-symbols-outlined text-2xl">book</span>
                </div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Subjects</p>
                <h3 className="text-2xl font-bold mt-1">{activeSubjects}</h3>
              </div>
              <div className="h-[calc(50%-12px)] bento-card p-6 flex flex-col justify-center items-center text-center">
                <div className="w-10 h-10 rounded-full bg-green-100 text-green-600 flex items-center justify-center mb-2">
                  <span className="material-symbols-outlined text-2xl">groups</span>
                </div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Enrolled</p>
                <h3 className="text-2xl font-bold mt-1">{enrolledStudents}</h3>
              </div>
            </div>

            {/* Extensions Card */}
            <div className="col-span-12 lg:col-span-4 row-span-2 bento-card flex flex-col">
              <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-amber-500">history_edu</span>
                  Extensions
                </h3>
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">3 Active</span>
                </div>
              </div>
              <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                <ExtensionRequests />
              </div>
            </div>
          </div>
        </main>
      </div>
      </div>

      {/* Create Classroom Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => (isCreating ? null : setIsCreateOpen(false))}></div>
          <div className="relative w-full max-w-md rounded-xl bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 p-6">
            <h3 className="text-xl font-black tracking-tight mb-2">Create Classroom</h3>
            <p className="text-sm text-[#5d479e] dark:text-gray-400 mb-4">Students will join using the generated classroom code.</p>
            <div className="grid grid-cols-1 gap-3">
              <input
                value={createName}
                onChange={(e) => {
                  setCreateName(e.target.value);
                  setCreateError('');
                }}
                className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none"
                placeholder="Subject name"
                disabled={isCreating}
              />
              <input
                value={createCode}
                onChange={(e) => {
                  setCreateCode(e.target.value);
                  setCreateError('');
                }}
                className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none"
                placeholder="Subject code (optional)"
                disabled={isCreating}
              />
              {createError ? (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {createError}
                </div>
              ) : null}
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => (isCreating ? null : setIsCreateOpen(false))}
                  className="px-5 py-2 rounded-lg font-bold border border-[#d5cee9] dark:border-white/10"
                  type="button"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    setIsCreating(true);
                    setCreateError('');
                    try {
                      const payload = { name: createName, code: createCode ? createCode : null };
                      const response = await api.post('/subjects', payload);
                      setSubjects((prev) => [response.data, ...prev]);
                      setCreateName('');
                      setCreateCode('');
                      setIsCreateOpen(false);
                    } catch (err) {
                      setCreateError(err?.response?.data?.detail || 'Failed to create classroom');
                    } finally {
                      setIsCreating(false);
                    }
                  }}
                  className="px-6 py-2 rounded-lg font-bold bg-primary text-white disabled:opacity-60"
                  type="button"
                  disabled={!createName.trim() || isCreating}
                >
                  {isCreating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Classroom Modal */}
      {!!editSubject && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => (isEditing ? null : closeEdit())}></div>
          <div className="relative w-full max-w-md rounded-xl bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 p-6">
            <h3 className="text-xl font-black tracking-tight mb-2">Edit Classroom</h3>
            <p className="text-sm text-[#5d479e] dark:text-gray-400 mb-4">Join Code: {editSubject.join_code}</p>
            <div className="grid grid-cols-1 gap-3">
              <input
                value={editName}
                onChange={(e) => {
                  setEditName(e.target.value);
                  setEditError('');
                }}
                className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none"
                placeholder="Subject name"
                disabled={isEditing}
              />
              <input
                value={editCode}
                onChange={(e) => {
                  setEditCode(e.target.value);
                  setEditError('');
                }}
                className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none"
                placeholder="Subject code (optional)"
                disabled={isEditing}
              />
              {editError ? (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {editError}
                </div>
              ) : null}
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={closeEdit}
                  className="px-5 py-2 rounded-lg font-bold border border-[#d5cee9] dark:border-white/10"
                  type="button"
                  disabled={isEditing}
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    setIsEditing(true);
                    setEditError('');
                    try {
                      const payload = { name: editName, code: editCode ? editCode : null };
                      const response = await api.put(`/subjects/${editSubject.id}`, payload);
                      setSubjects((prev) => prev.map((s) => (s.id === editSubject.id ? response.data : s)));
                      closeEdit();
                    } catch (err) {
                      setEditError(err?.response?.data?.detail || 'Failed to update classroom');
                    } finally {
                      setIsEditing(false);
                    }
                  }}
                  className="px-6 py-2 rounded-lg font-bold bg-primary text-white disabled:opacity-60"
                  type="button"
                  disabled={!editName.trim() || isEditing}
                >
                  {isEditing ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherDashboard;
