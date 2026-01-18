import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { logout } from '../services/authService';

const TeacherDashboard = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');

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

  const gradients = [
    'from-primary to-indigo-800',
    'from-blue-600 to-cyan-600',
    'from-indigo-600 to-purple-600',
    'from-fuchsia-600 to-purple-700',
    'from-emerald-600 to-teal-700',
    'from-amber-600 to-orange-700',
  ];

  const loadSubjects = async () => {
    setIsLoading(true);
    setLoadError('');
    try {
      const response = await api.get('/subjects');
      setSubjects(response.data || []);
    } catch (err) {
      setLoadError(err?.response?.data?.detail || 'Failed to load classrooms');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSubjects();
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
    <div className="bg-background-light dark:bg-background-dark font-display text-[#110d1c] dark:text-white antialiased min-h-screen">
      <div className="flex flex-col min-h-screen">
        <header className="sticky top-0 z-50 w-full border-b border-[#eae6f4] dark:border-white/10 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md px-6 md:px-10 py-3 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="text-primary size-8">
                <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M8.57829 8.57829C5.52816 11.6284 3.451 15.5145 2.60947 19.7452C1.76794 23.9758 2.19984 28.361 3.85056 32.3462C5.50128 36.3314 8.29667 39.7376 11.8832 42.134C15.4698 44.5305 19.6865 45.8096 24 45.8096C28.3135 45.8096 32.5302 44.5305 36.1168 42.134C39.7033 39.7375 42.4987 36.3314 44.1494 32.3462C45.8002 28.361 46.2321 23.9758 45.3905 19.7452C44.549 15.5145 42.4718 11.6284 39.4217 8.57829L24 24L8.57829 8.57829Z"
                    fill="currentColor"
                  ></path>
                </svg>
              </div>
              <h2 className="text-xl font-bold tracking-tight hidden md:block">Task Scheduling Agent</h2>
            </div>
            <div className="hidden lg:flex w-72 h-10">
              <div className="flex w-full items-stretch rounded-lg bg-[#eae6f4] dark:bg-white/5 border-none">
                <div className="flex items-center justify-center pl-4 text-[#5d479e] dark:text-gray-400">
                  <span className="material-symbols-outlined text-xl">search</span>
                </div>
                <input
                  className="w-full bg-transparent border-none focus:ring-0 text-sm placeholder:text-[#5d479e] dark:placeholder:text-gray-500 pl-2"
                  placeholder="Search classrooms..."
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <nav className="hidden md:flex items-center gap-6">
              <button className="text-sm font-semibold text-primary" onClick={() => navigate('/teacher/dashboard')}>
                Dashboard
              </button>
              <button className="text-sm font-medium hover:text-primary transition-colors">Calendar</button>
              <button className="text-sm font-medium hover:text-primary transition-colors">Reports</button>
            </nav>
            <div className="h-8 w-px bg-gray-200 dark:bg-white/10 hidden md:block"></div>
            <button
              onClick={handleLogout}
              className="bg-primary text-white text-sm font-bold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">logout</span>
              <span className="hidden sm:inline">Logout</span>
            </button>
            <div className="h-10 w-10 rounded-full border-2 border-primary/20 bg-gradient-to-br from-primary/20 to-primary/5"></div>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          <aside className="hidden lg:flex flex-col w-64 border-r border-[#eae6f4] dark:border-white/10 p-6 gap-8 bg-white dark:bg-background-dark/50">
            <div className="flex flex-col">
              <p className="text-xs font-bold uppercase tracking-wider text-[#5d479e] dark:text-gray-400 mb-4">
                Management
              </p>
              <nav className="flex flex-col gap-1">
                <button className="flex items-center gap-3 px-3 py-2 rounded-lg bg-primary/10 text-primary font-semibold">
                  <span className="material-symbols-outlined">home</span>
                  <span>Dashboard</span>
                </button>
                <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors">
                  <span className="material-symbols-outlined">school</span>
                  <span>My Classes</span>
                </button>
                <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors">
                  <span className="material-symbols-outlined">assignment</span>
                  <span>Assignments</span>
                </button>
                <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors">
                  <span className="material-symbols-outlined">trending_up</span>
                  <span>Student Progress</span>
                </button>
              </nav>
            </div>
            <div className="flex flex-col mt-auto">
              <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors">
                <span className="material-symbols-outlined">settings</span>
                <span>Settings</span>
              </button>
              <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors">
                <span className="material-symbols-outlined">help</span>
                <span>Support</span>
              </button>
            </div>
          </aside>

          <main className="flex-1 overflow-y-auto px-6 md:px-10 py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
              <div>
                <h1 className="text-3xl font-black tracking-tight mb-2">Teacher Dashboard</h1>
                <p className="text-[#5d479e] dark:text-gray-400">
                  Welcome back, {currentUser?.displayName || currentUser?.email || 'Teacher'}.
                </p>
              </div>
              <button
                onClick={() => {
                  setIsCreateOpen(true);
                  setCreateError('');
                }}
                className="bg-primary text-white font-bold px-6 py-3 rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all flex items-center gap-2"
              >
                <span className="material-symbols-outlined">add_circle</span>
                Create Classroom
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
              <div className="bg-white dark:bg-white/5 p-6 rounded-xl border border-[#d5cee9] dark:border-white/10 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide">
                    Active Subjects
                  </p>
                  <span className="material-symbols-outlined text-primary">book</span>
                </div>
                <p className="text-3xl font-black tracking-tight">{activeSubjects}</p>
              </div>
              <div className="bg-white dark:bg-white/5 p-6 rounded-xl border border-[#d5cee9] dark:border-white/10 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide">
                    Enrolled Students
                  </p>
                  <span className="material-symbols-outlined text-primary">group</span>
                </div>
                <p className="text-3xl font-black tracking-tight">0</p>
              </div>
              <div className="bg-white dark:bg-white/5 p-6 rounded-xl border border-[#d5cee9] dark:border-white/10 flex flex-col gap-1 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide">
                    Pending Tasks
                  </p>
                  <span className="material-symbols-outlined text-primary">pending_actions</span>
                </div>
                <p className="text-3xl font-black tracking-tight">0</p>
              </div>
            </div>

            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold">Your Classrooms</h3>
              <div className="flex gap-2">
                <button
                  onClick={loadSubjects}
                  className="p-2 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5"
                  disabled={isLoading}
                >
                  <span className="material-symbols-outlined">refresh</span>
                </button>
                <button className="p-2 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5">
                  <span className="material-symbols-outlined">grid_view</span>
                </button>
              </div>
            </div>

            {loadError && (
              <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {loadError}
              </div>
            )}

            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="bg-white dark:bg-white/5 rounded-xl border border-[#d5cee9] dark:border-white/10 overflow-hidden"
                  >
                    <div className="h-24 bg-[#eae6f4] dark:bg-white/5"></div>
                    <div className="p-6 space-y-4">
                      <div className="h-5 w-3/4 bg-[#eae6f4] dark:bg-white/10 rounded"></div>
                      <div className="h-10 bg-[#eae6f4] dark:bg-white/10 rounded"></div>
                      <div className="h-9 bg-[#eae6f4] dark:bg-white/10 rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredSubjects.length === 0 ? (
              <div className="bg-white dark:bg-white/5 rounded-xl border border-[#d5cee9] dark:border-white/10 p-10 text-center">
                <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-3xl">school</span>
                </div>
                <p className="text-xl font-bold">No classrooms yet</p>
                <p className="text-sm text-[#5d479e] dark:text-gray-400 mt-2">
                  Create your first classroom and share the join code with students.
                </p>
                <button
                  onClick={() => setIsCreateOpen(true)}
                  className="mt-6 bg-primary text-white font-bold px-6 py-3 rounded-xl hover:opacity-90 transition-opacity"
                >
                  Create Classroom
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredSubjects.map((subject, idx) => (
                  <div
                    key={subject.id}
                    className="group bg-white dark:bg-white/5 rounded-xl border border-[#d5cee9] dark:border-white/10 overflow-hidden hover:shadow-xl hover:shadow-primary/10 transition-all"
                  >
                    <div className={`h-24 bg-gradient-to-r ${gradients[idx % gradients.length]} p-6 flex flex-col justify-end`}>
                      <div className="flex justify-between items-start">
                        <span className="bg-white/20 backdrop-blur-md text-white text-[10px] font-bold uppercase px-2 py-0.5 rounded tracking-widest">
                          {(subject.code || 'NO-CODE').slice(0, 14)}
                        </span>
                        <button
                          className="text-white opacity-60 hover:opacity-100"
                          onClick={() => openEdit(subject)}
                          type="button"
                        >
                          <span className="material-symbols-outlined">more_vert</span>
                        </button>
                      </div>
                      <h4 className="text-white font-black text-xl leading-tight">{subject.name}</h4>
                    </div>
                    <div className="p-6 space-y-5">
                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-bold text-[#5d479e] dark:text-gray-400 uppercase">
                          Class Join Code
                        </span>
                        <div className="flex items-center justify-between bg-primary/5 dark:bg-white/5 p-3 rounded-lg border border-dashed border-primary/30">
                          <span className="font-mono text-lg font-bold text-primary tracking-widest">
                            {subject.join_code}
                          </span>
                          <button
                            onClick={() => handleCopyJoinCode(subject)}
                            className="text-primary hover:scale-110 transition-transform flex items-center gap-1 text-xs font-bold"
                            type="button"
                          >
                            <span className="material-symbols-outlined text-base">content_copy</span>
                            {copyState.subjectId === subject.id ? 'COPIED' : 'COPY'}
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-sm">group</span> 0 Students
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-sm">assignment</span> 0 Tasks
                        </span>
                      </div>
                      <div className="pt-4 border-t border-[#eae6f4] dark:border-white/10 flex gap-2">
                        <button
                          onClick={() => navigate(`/subject/${subject.id}`)}
                          className="flex-1 bg-[#eae6f4] dark:bg-white/10 text-primary dark:text-white font-bold py-2 rounded-lg text-sm hover:bg-primary hover:text-white transition-all"
                        >
                          View
                        </button>
                        <button
                          onClick={() => openEdit(subject)}
                          className="p-2 border border-[#eae6f4] dark:border-white/10 text-gray-500 rounded-lg hover:text-blue-600 hover:border-blue-600 transition-all"
                          type="button"
                        >
                          <span className="material-symbols-outlined text-xl">edit</span>
                        </button>
                        <button
                          onClick={async () => {
                            const ok = window.confirm(`Delete "${subject.name}"?`);
                            if (!ok) return;
                            try {
                              await api.delete(`/subjects/${subject.id}`);
                              setSubjects((prev) => prev.filter((s) => s.id !== subject.id));
                            } catch (err) {
                              setLoadError(err?.response?.data?.detail || 'Failed to delete classroom');
                            }
                          }}
                          className="p-2 border border-[#eae6f4] dark:border-white/10 text-gray-500 rounded-lg hover:text-red-600 hover:border-red-600 transition-all"
                          type="button"
                        >
                          <span className="material-symbols-outlined text-xl">delete</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </main>
        </div>
      </div>

      {isCreateOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => {
              if (isCreating) return;
              setIsCreateOpen(false);
            }}
          ></div>
          <div className="relative w-full max-w-xl rounded-xl bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-black tracking-tight">Create Classroom</h3>
                <p className="text-sm text-[#5d479e] dark:text-gray-400 mt-1">
                  Students will join using the generated classroom code.
                </p>
              </div>
              <button
                className="p-2 rounded-lg hover:bg-[#eae6f4] dark:hover:bg-white/5"
                onClick={() => {
                  if (isCreating) return;
                  setIsCreateOpen(false);
                }}
                type="button"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {createError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {createError}
              </div>
            )}

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide mb-2">
                  Subject Name
                </label>
                <input
                  value={createName}
                  onChange={(e) => {
                    setCreateName(e.target.value);
                    setCreateError('');
                  }}
                  className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="e.g., Advanced Mathematics"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide mb-2">
                  Subject Code
                </label>
                <input
                  value={createCode}
                  onChange={(e) => {
                    setCreateCode(e.target.value);
                    setCreateError('');
                  }}
                  className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="e.g., MATH-101"
                  disabled={isCreating}
                />
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  if (isCreating) return;
                  setIsCreateOpen(false);
                }}
                className="px-5 py-2 rounded-lg font-bold border border-[#d5cee9] dark:border-white/10 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors"
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
                    const payload = {
                      name: createName,
                      code: createCode ? createCode : null,
                    };
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
                className="px-6 py-2 rounded-lg font-bold bg-primary text-white hover:opacity-90 transition-opacity disabled:opacity-60"
                type="button"
                disabled={!createName.trim() || isCreating}
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {!!editSubject && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => (isEditing ? null : closeEdit())}></div>
          <div className="relative w-full max-w-xl rounded-xl bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-black tracking-tight">Edit Classroom</h3>
                <p className="text-sm text-[#5d479e] dark:text-gray-400 mt-1">Join Code: {editSubject.join_code}</p>
              </div>
              <button
                className="p-2 rounded-lg hover:bg-[#eae6f4] dark:hover:bg-white/5"
                onClick={() => (isEditing ? null : closeEdit())}
                type="button"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {editError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {editError}
              </div>
            )}

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide mb-2">
                  Subject Name
                </label>
                <input
                  value={editName}
                  onChange={(e) => {
                    setEditName(e.target.value);
                    setEditError('');
                  }}
                  className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  disabled={isEditing}
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-[#5d479e] dark:text-gray-400 uppercase tracking-wide mb-2">
                  Subject Code
                </label>
                <input
                  value={editCode}
                  onChange={(e) => {
                    setEditCode(e.target.value);
                    setEditError('');
                  }}
                  className="w-full h-12 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-background-light dark:bg-white/5 px-4 text-[#110d1c] dark:text-white placeholder:text-[#5d479e]/50 dark:placeholder:text-gray-500 outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  disabled={isEditing}
                />
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={closeEdit}
                className="px-5 py-2 rounded-lg font-bold border border-[#d5cee9] dark:border-white/10 hover:bg-[#eae6f4] dark:hover:bg-white/5 transition-colors"
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
                className="px-6 py-2 rounded-lg font-bold bg-primary text-white hover:opacity-90 transition-opacity disabled:opacity-60"
                type="button"
                disabled={!editName.trim() || isEditing}
              >
                {isEditing ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherDashboard;
