import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import aiService from '../services/aiService';
import { logout } from '../services/authService';
import ChatAssistant from '../components/ChatAssistant';

const TeacherDashboard = () => {
  const { currentUser, backendUser } = useAuth();
  const navigate = useNavigate();

  // Data States
  const [subjects, setSubjects] = useState([]);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [extensions, setExtensions] = useState([]);
  const [stats, setStats] = useState({ active: 0, enrolled: 0 });
  const [upcomingDays, setUpcomingDays] = useState(14);
  const [subjectRoster, setSubjectRoster] = useState({});
  const subjectRosterLoadingRef = useRef({});
  
  // Loading States
  const [_isLoading, setIsLoading] = useState(true);
  const [_isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');
  
  // Action States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createData, setCreateData] = useState({ name: '', code: '' });
  const [createError, setCreateError] = useState('');

  const [editSubject, setEditSubject] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({ name: '', code: '' });
  const [editError, setEditError] = useState('');

  const [processingExt, setProcessingExt] = useState({});
  const [copyState, setCopyState] = useState({ subjectId: null, copiedAt: 0 });
  const [search, setSearch] = useState('');

  const inFlightRef = useRef(false);

  // Helper: Resolve Photo URL
  const resolvePhotoUrl = (photoUrl) => {
    if (!photoUrl) return '';
    const u = String(photoUrl);
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    const root = String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');
    return `${root}${u}`;
  };

  const displayName = useMemo(() => {
    const candidate = String(backendUser?.name || currentUser?.displayName || '').trim();
    return candidate || 'Teacher';
  }, [backendUser?.name, currentUser?.displayName]);

  const fallbackAvatarUrl = useMemo(() => {
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=random`;
  }, [displayName]);

  const avatarSrc = backendUser?.photo_url ? resolvePhotoUrl(backendUser.photo_url) : fallbackAvatarUrl;

  const welcomeSubtext = useMemo(() => {
    const classCount = Number(subjects?.length || 0);
    const extCount = Number(extensions?.length || 0);

    const classesLabel =
      classCount === 0 ? 'no active classes' : classCount === 1 ? '1 active class' : `${classCount} active classes`;

    const extLabel =
      extCount === 0
        ? 'no pending extension requests'
        : extCount === 1
          ? '1 pending extension request'
          : `${extCount} pending extension requests`;

    if (extCount > 0) return `You have ${classesLabel} and ${extLabel} that need your immediate attention.`;
    return `You have ${classesLabel} and ${extLabel}.`;
  }, [subjects?.length, extensions?.length]);

  // Helper: Format Dates
  const formatDue = (deadline) => {
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return '';
    // Calculate days remaining
    const now = new Date();
    const diff = d - now;
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    
    if (days < 0) return 'Overdue';
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    return `${days} Days`;
  };

  const _formatExtDate = (deadline) => {
     const d = new Date(deadline);
     return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const getInitials = (value) => {
    const v = String(value || '').trim();
    if (!v) return '?';
    const parts = v.split(/\s+/).filter(Boolean);
    const chars = parts.slice(0, 2).map((p) => p[0]).filter(Boolean);
    if (chars.length === 0) return v[0]?.toUpperCase?.() || '?';
    return chars.join('').toUpperCase();
  };

  // Data Fetching
  const loadAllData = useCallback(async ({ silent } = {}) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    if (!silent) setIsLoading(true);
    else setIsRefreshing(true);

    try {
      const [subjectsRes, upcomingRes, extensionsRes] = await Promise.allSettled([
        api.get('/subjects'),
        api.get('/dashboard/teacher/upcoming', { params: { days: upcomingDays, limit: 10 } }),
        aiService.getExtensionRequests('pending')
      ]);

      // Handle Subjects
      if (subjectsRes.status === 'fulfilled') {
        const subs = subjectsRes.value.data || [];
        setSubjects(subs);
        const enrolled = subs.reduce((acc, s) => acc + (Number(s.student_count) || 0), 0);
        setStats({ active: subs.length, enrolled });
      }

      // Handle Upcoming
      if (upcomingRes.status === 'fulfilled') {
        setUpcomingTasks(upcomingRes.value.data?.items || []);
      }

      // Handle Extensions
      if (extensionsRes.status === 'fulfilled') {
        setExtensions(extensionsRes.value.items || []);
      }

      setError('');
    } catch (err) {
      if (!silent) setError('Failed to refresh dashboard data');
      console.error(err);
    } finally {
      inFlightRef.current = false;
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [upcomingDays]);

  const loadSubjectRoster = useCallback(
    async (subjectId) => {
      if (!subjectId) return;
      if (subjectRoster[subjectId]) return;
      if (subjectRosterLoadingRef.current[subjectId]) return;
      subjectRosterLoadingRef.current[subjectId] = true;
      try {
        const res = await api.get(`/subjects/${subjectId}/roster`);
        const items = Array.isArray(res.data) ? res.data : [];
        setSubjectRoster((prev) => ({ ...prev, [subjectId]: items }));
      } catch (_err) {
        setSubjectRoster((prev) => ({ ...prev, [subjectId]: [] }));
      } finally {
        subjectRosterLoadingRef.current[subjectId] = false;
      }
    },
    [subjectRoster]
  );

  useEffect(() => {
    loadAllData({ silent: false });
    
    // Auto-refresh every 30s
    const interval = setInterval(() => {
      if (!document.hidden) loadAllData({ silent: true });
    }, 30000);

    const onVisChange = () => {
      if (!document.hidden) loadAllData({ silent: true });
    };

    document.addEventListener('visibilitychange', onVisChange);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisChange);
    };
  }, [loadAllData]);

  // Filtered Subjects
  const filteredSubjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return subjects;
    return subjects.filter(s => 
      (s.name || '').toLowerCase().includes(q) || 
      (s.code || '').toLowerCase().includes(q)
    );
  }, [subjects, search]);

  useEffect(() => {
    filteredSubjects.slice(0, 5).forEach((s) => {
      loadSubjectRoster(s?.id);
    });
  }, [filteredSubjects, loadSubjectRoster]);

  // Actions
  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleCopyCode = async (subject) => {
    const value = subject?.join_code;
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopyState({ subjectId: subject.id, copiedAt: Date.now() });
      setTimeout(() => setCopyState(prev => prev.subjectId === subject.id ? { subjectId: null, copiedAt: 0 } : prev), 1500);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleCreateSubject = async () => {
    if (!createData.name.trim()) return;
    setIsCreating(true);
    setCreateError('');
    try {
      await api.post('/subjects', { 
        name: createData.name, 
        code: createData.code || null 
      });
      await loadAllData({ silent: true });
      setIsCreateOpen(false);
      setCreateData({ name: '', code: '' });
    } catch (err) {
      setCreateError(err?.response?.data?.detail || 'Failed to create classroom');
    } finally {
      setIsCreating(false);
    }
  };

  const handleUpdateSubject = async () => {
    if (!editData.name.trim() || !editSubject) return;
    setIsEditing(true);
    setEditError('');
    try {
      await api.put(`/subjects/${editSubject.id}`, {
        name: editData.name,
        code: editData.code || null
      });
      await loadAllData({ silent: true });
      setEditSubject(null);
    } catch (err) {
      setEditError(err?.response?.data?.detail || 'Failed to update classroom');
    } finally {
      setIsEditing(false);
    }
  };

  const handleExtension = async (extId, action) => {
    setProcessingExt(prev => ({ ...prev, [extId]: true }));
    try {
      if (action === 'approve') await aiService.approveExtension(extId, {});
      else await aiService.denyExtension(extId, {});
      
      // Optimistic update
      setExtensions(prev => prev.filter(e => e.id !== extId));
      
      // Background refresh
      loadAllData({ silent: true });
    } catch (err) {
      alert(`Failed to ${action} extension`);
    } finally {
      setProcessingExt(prev => ({ ...prev, [extId]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-surface text-slate-900 font-sans antialiased">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <div className="bg-primary p-1.5 rounded-lg text-white">
              <span className="material-symbols-outlined block">bolt</span>
            </div>
            <span className="font-bold text-lg tracking-tight">Task Scheduling Agent</span>
          </div>
          <div className="hidden lg:flex items-center gap-4 text-sm font-medium text-slate-600">
            <button
              className="text-primary"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              type="button"
            >
              Dashboard
            </button>
            <button className="hover:text-primary" onClick={() => navigate('/teacher/classrooms')} type="button">
              Classrooms
            </button>
            <button className="hover:text-primary" onClick={() => navigate('/calendar')} type="button">
              Schedule
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative hidden sm:block">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">search</span>
            <input 
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search resources..." 
              className="w-64 pl-9 pr-4 py-1.5 bg-slate-100 border-none rounded-full text-sm focus:ring-2 focus:ring-primary/20 outline-none"
            />
          </div>
          <div className="flex items-center gap-3">
            <button className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <button 
              onClick={handleLogout}
              className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
              title="Logout"
            >
              <span className="material-symbols-outlined">logout</span>
            </button>
            <button
              className="w-9 h-9 rounded-full bg-slate-200 overflow-hidden border-2 border-white shadow-sm"
              onClick={() => navigate('/profile')}
              title="Profile settings"
              type="button"
            >
              <img 
                src={avatarSrc} 
                alt="User avatar" 
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = fallbackAvatarUrl;
                }}
              />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-[1440px] mx-auto p-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-xl border border-red-100 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-12 grid-rows-6 gap-6 h-auto lg:h-[calc(100vh-140px)] min-h-[850px]">
          
          {/* Welcome Card */}
          <div className="col-span-12 lg:col-span-8 row-span-2 bento-card p-8 bg-gradient-to-br from-white to-soft-purple/30 flex flex-col justify-between relative overflow-hidden">
            <div className="relative z-10">
              <span className="text-primary font-semibold text-sm bg-primary/10 px-3 py-1 rounded-full uppercase tracking-wider">Academic Portal</span>
              <h1 className="text-4xl font-bold text-slate-900 mt-4">
                Welcome back,<br/>
                {displayName}
              </h1>
              <p className="text-slate-500 mt-2 max-w-md">
                {welcomeSubtext}
              </p>
            </div>
            <div className="flex gap-4 mt-6 relative z-10">
              <button 
                onClick={() => setIsCreateOpen(true)}
                className="bg-primary text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 hover:bg-accent-purple transition-all shadow-lg shadow-primary/20"
              >
                <span className="material-symbols-outlined">add_circle</span>
                Create Classroom
              </button>
              <button 
                onClick={() => navigate('/calendar')}
                className="bg-white text-slate-700 border border-slate-200 px-6 py-3 rounded-xl font-semibold hover:bg-slate-50 transition-all"
              >
                View Schedule
              </button>
            </div>
          </div>

          <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-3 min-h-[557px]">
            <ChatAssistant height="100%" className="h-full" minimizedHeight={56} />
          </div>

          {/* Upcoming Tasks */}
          <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-2 bento-card overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">event_note</span>
                Upcoming
              </h3>
              <select
                className="text-xs font-semibold text-slate-400 uppercase tracking-wider bg-transparent focus:outline-none"
                value={upcomingDays}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setUpcomingDays(Number.isFinite(next) ? next : 14);
                }}
              >
                <option value={7}>7 Days</option>
                <option value={14}>14 Days</option>
                <option value={30}>30 Days</option>
                <option value={60}>60 Days</option>
              </select>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {upcomingTasks.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-slate-400 text-sm">
                  <span className="material-symbols-outlined mb-2">event_busy</span>
                  No upcoming tasks
                </div>
              ) : (
                upcomingTasks.map((task) => (
                  <button
                    key={task.task_id}
                    className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-primary/40 hover:bg-slate-100/70 transition-colors text-left"
                    onClick={() => {
                      if (!task?.task_id) return;
                      navigate(`/task/${task.task_id}`);
                    }}
                    type="button"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                        task.band === 'urgent' ? 'bg-red-100 text-red-600' :
                        task.band === 'high' ? 'bg-amber-100 text-amber-600' :
                        'bg-blue-100 text-blue-600'
                      }`}>
                        <span className="material-symbols-outlined text-lg">
                           {task.band === 'urgent' ? 'assignment_late' : 'assignment'}
                        </span>
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm leading-tight line-clamp-1">{task.title}</h4>
                        <p className="text-[11px] text-slate-500 line-clamp-1">{task.subject_name}</p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        task.band === 'urgent' ? 'bg-red-50 text-red-500' : 'bg-slate-100 text-slate-500'
                      }`}>
                        {formatDue(task.deadline)}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Pending Tasks (Static/Placeholder) */}
          <div className="col-span-12 md:col-span-6 lg:col-span-4 row-span-2 bento-card p-8 flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-bold">Pending Tasks</h3>
              <p className="text-slate-500 text-sm mt-1">Assignments awaiting grading</p>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-6xl font-black text-primary">--</span>
              <span className="text-slate-600 font-medium">submissions</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="bg-primary h-2 rounded-full w-0"></div>
            </div>
            <button className="w-full py-2.5 rounded-lg border border-slate-200 text-sm font-semibold hover:bg-slate-50 transition-colors">
              Review All
            </button>
          </div>

          {/* Your Classrooms */}
          <div id="classrooms" className="col-span-12 lg:col-span-6 row-span-2 bento-card p-6 flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">school</span>
                Your Classrooms
              </h3>
              <button 
                className="text-primary text-sm font-bold hover:underline"
                onClick={() => navigate('/teacher/classrooms')}
              >
                View All
              </button>
            </div>
            <div className="flex-1 flex gap-4 overflow-x-auto pb-2 scroll-smooth">
              {filteredSubjects.slice(0, 5).map(subject => (
                <div
                  key={subject.id}
                  className="min-w-[260px] bg-slate-50 rounded-xl p-5 border border-slate-100 flex flex-col justify-between cursor-pointer hover:border-primary/30 hover:bg-white transition-colors"
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/subject/${subject.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(`/subject/${subject.id}`);
                    }
                  }}
                >
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                        {subject.code || 'NO CODE'}
                      </span>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditSubject(subject);
                          setEditData({ name: subject.name, code: subject.code });
                        }}
                        className="text-slate-300 hover:text-slate-500"
                      >
                        <span className="material-symbols-outlined">more_vert</span>
                      </button>
                    </div>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/subject/${subject.id}`);
                      }}
                      className="font-bold text-slate-800 text-left hover:text-primary transition-colors line-clamp-1"
                    >
                      {subject.name}
                    </button>
                    <p className="text-xs text-slate-500 mt-1">Classroom</p>
                  </div>
                  <div className="mt-6 flex items-center justify-between">
                    <div className="flex -space-x-2">
                      {(() => {
                        const total = Number(subject.student_count) || 0;
                        const roster = subjectRoster?.[subject.id];
                        const rosterItems = Array.isArray(roster) ? roster : null;
                        const actualCount = rosterItems ? Math.min(2, rosterItems.length) : 0;
                        const placeholderCount = rosterItems ? Math.max(0, Math.min(2, total) - actualCount) : Math.min(2, total);
                        const extra = Math.max(0, total - (actualCount + placeholderCount));

                        return (
                          <>
                            {rosterItems &&
                              rosterItems.slice(0, actualCount).map((m, idx) => (
                                <div
                                  key={m?.uid || `${subject.id}-student-${idx}`}
                                  className="w-6 h-6 rounded-full bg-primary/10 text-primary border-2 border-white flex items-center justify-center text-[8px] font-bold"
                                  title={m?.name || m?.email || ''}
                                >
                                  {getInitials(m?.name || m?.email)}
                                </div>
                              ))}
                            {Array.from({ length: placeholderCount }).map((_, idx) => (
                              <div
                                key={`${subject.id}-placeholder-${idx}`}
                                className="w-6 h-6 rounded-full bg-slate-200 border-2 border-white"
                              ></div>
                            ))}
                            {extra > 0 && (
                              <div className="w-6 h-6 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[8px] font-bold">
                                +{extra}
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopyCode(subject);
                      }}
                      className="text-primary font-bold text-xs"
                    >
                      {copyState.subjectId === subject.id ? (
                        <span className="text-green-600">COPIED!</span>
                      ) : (
                        <>JOIN CODE: <span className="font-mono">{subject.join_code}</span></>
                      )}
                    </button>
                  </div>
                </div>
              ))}

              {/* Add New Card */}
              <div 
                onClick={() => setIsCreateOpen(true)}
                className="min-w-[180px] border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center p-5 cursor-pointer hover:bg-slate-50 transition-colors group"
              >
                <div className="w-10 h-10 rounded-full bg-slate-100 group-hover:bg-primary/10 flex items-center justify-center text-slate-400 group-hover:text-primary mb-2 transition-all">
                  <span className="material-symbols-outlined">add</span>
                </div>
                <span className="text-sm font-semibold text-slate-500 group-hover:text-primary">Add New</span>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="col-span-6 md:col-span-3 lg:col-span-2 row-span-2 space-y-6">
            <div className="h-[calc(50%-12px)] bento-card p-6 flex flex-col justify-center items-center text-center">
              <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-2">
                <span className="material-symbols-outlined text-2xl">book</span>
              </div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Subjects</p>
              <h3 className="text-2xl font-bold mt-1">{stats.active}</h3>
            </div>
            <div className="h-[calc(50%-12px)] bento-card p-6 flex flex-col justify-center items-center text-center">
              <div className="w-10 h-10 rounded-full bg-green-100 text-green-600 flex items-center justify-center mb-2">
                <span className="material-symbols-outlined text-2xl">groups</span>
              </div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Enrolled</p>
              <h3 className="text-2xl font-bold mt-1">{stats.enrolled}</h3>
            </div>
          </div>

          {/* Extensions */}
          <div className="col-span-12 lg:col-span-4 row-span-2 bento-card flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-500">history_edu</span>
                Extensions
              </h3>
              <div className="flex gap-1 items-center">
                {extensions.length > 0 && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>}
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">{extensions.length} Active</span>
              </div>
            </div>
            <div className="flex-1 p-4 space-y-4 overflow-y-auto">
              {extensions.length === 0 ? (
                <div className="text-center text-slate-400 py-8 text-sm">No pending extensions</div>
              ) : (
                extensions.map(ext => (
                  <div key={ext.id} className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="w-8 h-8 rounded-full bg-slate-200 shrink-0 flex items-center justify-center text-xs font-bold text-slate-500">
                      {/* Initials */}
                      {(ext.student_name || 'S').charAt(0)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold">
                        {ext.student_name || 'Student'}{' '}
                        <span className="text-slate-400 font-normal">requested {ext.extension_days} days for</span>{' '}
                        {ext.task_title || 'Task'}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5 italic">
                        "{ext.reason}"
                      </p>
                      {/* AI Tip */}
                      {ext.ai_analysis && (
                        <div className="mt-1 flex items-center gap-1.5">
                           <span className="material-symbols-outlined text-[10px] text-primary">smart_toy</span>
                           <span className={`text-[10px] font-bold uppercase ${
                             ext.ai_analysis.recommendation === 'approve' ? 'text-green-600' : 
                             ext.ai_analysis.recommendation === 'deny' ? 'text-red-500' : 'text-amber-500'
                           }`}>AI Recommends: {ext.ai_analysis.recommendation}</span>
                        </div>
                      )}
                      
                      <div className="mt-2 flex gap-2">
                        <button 
                          onClick={() => handleExtension(ext.id, 'approve')}
                          disabled={processingExt[ext.id]}
                          className="text-[10px] font-bold text-primary bg-primary/10 px-3 py-1 rounded hover:bg-primary/20 disabled:opacity-50"
                        >
                          {processingExt[ext.id] ? '...' : 'APPROVE'}
                        </button>
                        <button 
                          onClick={() => handleExtension(ext.id, 'deny')}
                          disabled={processingExt[ext.id]}
                          className="text-[10px] font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded hover:bg-slate-200 disabled:opacity-50"
                        >
                          {processingExt[ext.id] ? '...' : 'DENY'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Create Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsCreateOpen(false)}></div>
          <div className="relative w-full max-w-md rounded-xl bg-white border border-slate-200 p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold tracking-tight mb-2">Create Classroom</h3>
            <p className="text-sm text-slate-500 mb-6">Students will join using the generated classroom code.</p>
            <div className="space-y-4">
              <input 
                value={createData.name}
                onChange={e => setCreateData({...createData, name: e.target.value})}
                placeholder="Subject name" 
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
              />
              <input 
                value={createData.code}
                onChange={e => setCreateData({...createData, code: e.target.value})}
                placeholder="Subject code (e.g. CS101)" 
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
              />
              {createError && <p className="text-xs text-red-500">{createError}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <button 
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-50 text-sm"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleCreateSubject}
                  disabled={isCreating || !createData.name}
                  className="px-4 py-2 rounded-lg font-semibold bg-primary text-white hover:bg-primary/90 text-sm disabled:opacity-50"
                >
                  {isCreating ? 'Creating...' : 'Create Classroom'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {!!editSubject && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setEditSubject(null)}></div>
          <div className="relative w-full max-w-md rounded-xl bg-white border border-slate-200 p-6 shadow-2xl">
            <h3 className="text-xl font-bold tracking-tight mb-2">Edit Classroom</h3>
            <div className="space-y-4 mt-6">
              <input 
                value={editData.name}
                onChange={e => setEditData({...editData, name: e.target.value})}
                placeholder="Subject name" 
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
              />
              <input 
                value={editData.code}
                onChange={e => setEditData({...editData, code: e.target.value})}
                placeholder="Subject code" 
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 outline-none"
              />
              {editError && <p className="text-xs text-red-500">{editError}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <button 
                  onClick={() => setEditSubject(null)}
                  className="px-4 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-50 text-sm"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleUpdateSubject}
                  disabled={isEditing || !editData.name}
                  className="px-4 py-2 rounded-lg font-semibold bg-primary text-white hover:bg-primary/90 text-sm disabled:opacity-50"
                >
                  {isEditing ? 'Saving...' : 'Save Changes'}
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
