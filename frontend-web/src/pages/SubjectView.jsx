import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const SubjectView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userRole } = useAuth();
  const [subject, setSubject] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState('');

  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskDeadline, setTaskDeadline] = useState('');
  const [taskPoints, setTaskPoints] = useState('');
  const [taskType, setTaskType] = useState('');
  const [taskCreateError, setTaskCreateError] = useState('');
  const [taskCreating, setTaskCreating] = useState(false);
  const [sortMode, setSortMode] = useState('deadline');
  const [taskSearch, setTaskSearch] = useState('');
  const [studentTab, setStudentTab] = useState('all');
  const [mySubmissions, setMySubmissions] = useState([]);
  const [mySubmissionsLoading, setMySubmissionsLoading] = useState(false);
  const [mySubmissionsError, setMySubmissionsError] = useState('');
  const [roster, setRoster] = useState([]);
  const [rosterLoading, setRosterLoading] = useState(false);
  const [rosterError, setRosterError] = useState('');

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first?.msg === 'string') return first.msg;
      return JSON.stringify(first);
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return fallback;
  };

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const response = await api.get(`/subjects/${id}`);
        setSubject(response.data);
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to load subject'));
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      load();
    }
  }, [id]);

  const loadTasks = async () => {
    if (!id) return;
    setTasksLoading(true);
    setTasksError('');
    try {
      const response = await api.get('/tasks', { params: { subject_id: id } });
      setTasks(response.data || []);
    } catch (err) {
      setTasksError(getErrorMessage(err, 'Failed to load tasks'));
    } finally {
      setTasksLoading(false);
    }
  };

  const loadMySubmissions = async () => {
    if (!id) return;
    if (userRole !== 'student') return;
    setMySubmissionsLoading(true);
    setMySubmissionsError('');
    try {
      const response = await api.get('/submissions/mine', { params: { subject_id: id } });
      setMySubmissions(response.data || []);
    } catch (err) {
      setMySubmissionsError(getErrorMessage(err, 'Failed to load submissions'));
    } finally {
      setMySubmissionsLoading(false);
    }
  };

  const loadRoster = async () => {
    if (!id) return;
    if (userRole !== 'teacher') return;
    setRosterLoading(true);
    setRosterError('');
    try {
      const response = await api.get(`/subjects/${id}/roster`);
      setRoster(response.data || []);
    } catch (err) {
      setRosterError(getErrorMessage(err, 'Failed to load roster'));
    } finally {
      setRosterLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [id]);

  useEffect(() => {
    loadMySubmissions();
  }, [id, userRole]);

  useEffect(() => {
    loadRoster();
  }, [id, userRole]);

  const mySubmissionByTaskId = useMemo(() => {
    const map = new Map();
    for (const s of mySubmissions) {
      if (s?.task_id) map.set(s.task_id, s);
    }
    return map;
  }, [mySubmissions]);

  const isResourceTask = (task) => {
    const v = String(task?.task_type || '').toLowerCase();
    return v.includes('reading') || v.includes('resource');
  };

  const getStudentTaskStatus = (task) => {
    const submission = mySubmissionByTaskId.get(task.id);
    if (submission) {
      if (submission.score !== null && submission.score !== undefined) return 'graded';
      return 'submitted';
    }

    if (task.deadline) {
      const t = new Date(task.deadline).getTime();
      if (!Number.isNaN(t) && t < Date.now()) return 'missing';
    }
    return 'pending';
  };

  const studentTabCounts = useMemo(() => {
    const counts = { all: 0, pending: 0, completed: 0, resources: 0 };
    for (const task of tasks) {
      counts.all += 1;
      if (isResourceTask(task)) {
        counts.resources += 1;
        continue;
      }
      const status = getStudentTaskStatus(task);
      if (status === 'graded') counts.completed += 1;
      else counts.pending += 1;
    }
    return counts;
  }, [tasks, mySubmissionByTaskId]);

  const visibleTasks = useMemo(() => {
    const q = taskSearch.trim().toLowerCase();
    const list = tasks.filter((t) => {
      if (!q) return true;
      const hay = `${t.title || ''} ${t.description || ''} ${t.task_type || ''}`.toLowerCase();
      return hay.includes(q);
    });

    const filtered =
      userRole === 'student'
        ? list.filter((t) => {
            const resource = isResourceTask(t);
            if (studentTab === 'resources') return resource;
            if (resource) return false;
            const status = getStudentTaskStatus(t);
            if (studentTab === 'completed') return status === 'graded';
            if (studentTab === 'pending') return status !== 'graded';
            return true;
          })
        : list;

    const sorted = [...list].sort((a, b) => {
      if (sortMode === 'title') return String(a.title || '').localeCompare(String(b.title || ''));
      if (sortMode === 'points') return (Number(b.points || 0) || 0) - (Number(a.points || 0) || 0);
      const ad = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
      const bd = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
      return ad - bd;
    });

    if (userRole === 'student') return filtered.sort((a, b) => {
      const ad = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
      const bd = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
      return ad - bd;
    });

    return sorted;
  }, [sortMode, taskSearch, tasks, userRole, studentTab, mySubmissionByTaskId]);

  const formatDeadline = (deadline) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString();
  };

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen font-display text-[#110d1c] dark:text-white">
      {userRole === 'teacher' ? (
        <>
          <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#eae6f4] dark:border-b-[#2d2644] bg-white dark:bg-[#1c1633] px-6 md:px-10 py-3 sticky top-0 z-10">
            <div className="flex items-center gap-4 text-primary">
              <div className="size-6">
                <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                  <g clipPath="url(#clip0_6_319)">
                    <path
                      d="M8.57829 8.57829C5.52816 11.6284 3.451 15.5145 2.60947 19.7452C1.76794 23.9758 2.19984 28.361 3.85056 32.3462C5.50128 36.3314 8.29667 39.7376 11.8832 42.134C15.4698 44.5305 19.6865 45.8096 24 45.8096C28.3135 45.8096 32.5302 44.5305 36.1168 42.134C39.7033 39.7375 42.4987 36.3314 44.1494 32.3462C45.8002 28.361 46.2321 23.9758 45.3905 19.7452C44.549 15.5145 42.4718 11.6284 39.4217 8.57829L24 24L8.57829 8.57829Z"
                      fill="currentColor"
                    ></path>
                  </g>
                  <defs>
                    <clipPath id="clip0_6_319">
                      <rect fill="white" height="48" width="48"></rect>
                    </clipPath>
                  </defs>
                </svg>
              </div>
              <h2 className="text-[#110d1c] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
                Task Scheduling Agent
              </h2>
            </div>
            <div className="flex flex-1 justify-end gap-6 items-center">
              <nav className="hidden md:flex items-center gap-9">
                <button
                  className="text-[#110d1c] dark:text-gray-300 text-sm font-medium leading-normal hover:text-primary transition-colors"
                  onClick={() => navigate('/teacher/dashboard')}
                >
                  Dashboard
                </button>
                <button className="text-primary text-sm font-bold leading-normal">Subjects</button>
                <button className="text-[#110d1c] dark:text-gray-300 text-sm font-medium leading-normal hover:text-primary transition-colors">
                  Tasks
                </button>
              </nav>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setIsCreateTaskOpen(true);
                    setTaskCreateError('');
                  }}
                  className="flex min-w-[120px] cursor-pointer items-center justify-center rounded-lg h-10 px-4 bg-primary text-white text-sm font-bold transition-opacity hover:opacity-90"
                  disabled={!subject}
                >
                  <span>Create Task</span>
                </button>
                <div className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 border border-gray-200 dark:border-white/10 bg-gradient-to-br from-primary/20 to-primary/5"></div>
              </div>
            </div>
          </header>

          <main className="flex-1 px-6 md:px-10 lg:px-16 py-8 mx-auto max-w-[1440px] w-full">
            <div className="flex flex-wrap items-center gap-2 mb-6">
              <button className="text-primary text-base font-medium hover:underline" onClick={() => navigate('/teacher/dashboard')}>
                Dashboard
              </button>
              <span className="text-gray-400 font-medium">/</span>
              <span className="text-[#110d1c] dark:text-white text-base font-semibold">
                {subject?.name || 'Subject'}
              </span>
            </div>

            {(error || tasksError || rosterError) && (
              <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error || tasksError || rosterError}
              </div>
            )}

            {isLoading ? (
              <div className="text-gray-600 dark:text-gray-300">Loading...</div>
            ) : !subject ? (
              <div className="text-gray-600 dark:text-gray-300">Subject not found.</div>
            ) : (
              <>
                <div className="mb-10">
                  <div className="bg-white dark:bg-[#1c1633] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] overflow-hidden border border-[#eae6f4] dark:border-[#2d2644]">
                    <div className="flex flex-col lg:flex-row">
                      <div className="w-full lg:w-1/3 h-48 lg:h-auto bg-gradient-to-br from-primary/20 to-primary/5"></div>
                      <div className="flex flex-1 flex-col p-6 md:p-8">
                        <div className="flex justify-between items-start mb-4 gap-4">
                          <div>
                            <p className="text-primary text-sm font-semibold uppercase tracking-wider mb-1">Subject Overview</p>
                            <h1 className="text-[#110d1c] dark:text-white text-3xl font-extrabold tracking-tight">
                              {subject.name}
                            </h1>
                            <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
                              {subject.code || 'No code'}
                            </p>
                          </div>
                          <button
                            onClick={async () => {
                              try {
                                await navigator.clipboard.writeText(subject.join_code);
                              } catch {}
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-lg font-semibold text-sm hover:bg-primary/20 transition-colors"
                          >
                            <span className="material-symbols-outlined text-[20px]">share</span>
                            <span>Share Join Code</span>
                          </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 border-t border-gray-100 dark:border-gray-700 pt-6">
                          <div className="flex flex-col gap-1">
                            <p className="text-gray-500 dark:text-gray-400 text-sm font-medium">Join Code</p>
                            <div className="flex items-center gap-2">
                              <p className="text-[#110d1c] dark:text-white text-lg font-bold">{subject.join_code}</p>
                              <button
                                onClick={async () => {
                                  try {
                                    await navigator.clipboard.writeText(subject.join_code);
                                  } catch {}
                                }}
                                className="text-gray-400 cursor-pointer hover:text-primary transition-colors"
                                type="button"
                              >
                                <span className="material-symbols-outlined text-[18px]">content_copy</span>
                              </button>
                            </div>
                          </div>
                          <div className="flex flex-col gap-1 md:border-l border-gray-100 dark:border-gray-700 md:pl-6">
                            <p className="text-gray-500 dark:text-gray-400 text-sm font-medium">Teacher ID</p>
                            <p className="text-[#110d1c] dark:text-white text-lg font-bold">{subject.teacher_uid}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between mb-6 gap-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-[#110d1c] dark:text-white text-2xl font-bold tracking-tight">Tasks</h2>
                    <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-bold text-gray-600 dark:text-gray-300">
                      {tasksLoading ? 'Loading' : `${tasks.length} Active`}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="hidden md:flex items-center gap-2 text-sm font-medium text-gray-500">
                      <span>Sort by:</span>
                      <select
                        value={sortMode}
                        onChange={(e) => setSortMode(e.target.value)}
                        className="bg-transparent border-none focus:ring-0 cursor-pointer font-bold text-[#110d1c] dark:text-white"
                      >
                        <option value="deadline">Deadline (Soonest)</option>
                        <option value="title">Title (A-Z)</option>
                        <option value="points">Points (High-Low)</option>
                      </select>
                    </div>
                    <button
                      onClick={loadTasks}
                      className="flex items-center justify-center rounded-lg size-10 bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
                      disabled={tasksLoading}
                      type="button"
                    >
                      <span className="material-symbols-outlined">refresh</span>
                    </button>
                  </div>
                </div>

                {tasksLoading ? (
                  <div className="text-gray-600 dark:text-gray-300">Loading tasks...</div>
                ) : visibleTasks.length === 0 ? (
                  <div className="text-gray-600 dark:text-gray-300">No tasks yet.</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {visibleTasks.map((task) => (
                      <button
                        key={task.id}
                        onClick={() => navigate(`/task/${task.id}`)}
                        className="bg-white dark:bg-[#1c1633] border border-[#eae6f4] dark:border-[#2d2644] rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow text-left"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-[10px] font-bold rounded uppercase">
                            {(task.task_type || 'Task').slice(0, 24)}
                          </span>
                          {typeof task.points === 'number' ? (
                            <div className="flex items-center gap-1 text-primary font-bold">
                              <span className="text-lg">{task.points}</span>
                              <span className="text-[10px] uppercase">pts</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 text-gray-400 font-bold">
                              <span className="text-[10px] uppercase">No pts</span>
                            </div>
                          )}
                        </div>
                        <h3 className="text-[#110d1c] dark:text-white font-bold text-lg mb-2 hover:text-primary transition-colors">
                          {task.title}
                        </h3>
                        {task.description ? (
                          <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
                            {task.description}
                          </p>
                        ) : (
                          <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">No description.</p>
                        )}
                        <div className="flex items-center gap-2 pt-4 border-t border-gray-50 dark:border-gray-800">
                          <span className="material-symbols-outlined text-gray-400 text-[20px]">calendar_today</span>
                          <span className="text-gray-600 dark:text-gray-300 text-xs font-medium">
                            {formatDeadline(task.deadline) ? `Due ${formatDeadline(task.deadline)}` : 'No deadline'}
                          </span>
                        </div>
                      </button>
                    ))}
                    <button
                      onClick={() => {
                        setIsCreateTaskOpen(true);
                        setTaskCreateError('');
                      }}
                      className="border-2 border-dashed border-[#d5cee9] dark:border-[#2d2644] rounded-xl p-5 flex flex-col items-center justify-center min-h-[180px] hover:border-primary/50 transition-colors cursor-pointer"
                      type="button"
                    >
                      <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                        <span className="material-symbols-outlined text-primary">add</span>
                      </div>
                      <p className="text-primary font-bold text-sm">Create New Task</p>
                    </button>
                  </div>
                )}

                <div className="mt-10 bg-white dark:bg-[#1c1633] rounded-xl border border-[#eae6f4] dark:border-[#2d2644] overflow-hidden">
                  <div className="p-6 flex items-center justify-between gap-4 border-b border-[#eae6f4] dark:border-[#2d2644]">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-primary">group</span>
                      <h3 className="text-lg font-bold text-[#110d1c] dark:text-white">Students</h3>
                      <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-bold text-gray-600 dark:text-gray-300">
                        {rosterLoading ? 'Loading' : roster.length}
                      </span>
                    </div>
                    <button
                      onClick={loadRoster}
                      className="flex items-center justify-center rounded-lg size-10 bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/10 transition-colors disabled:opacity-60"
                      disabled={rosterLoading}
                      type="button"
                    >
                      <span className="material-symbols-outlined">refresh</span>
                    </button>
                  </div>
                  <div className="p-6">
                    {rosterLoading ? (
                      <div className="text-gray-600 dark:text-gray-300">Loading roster...</div>
                    ) : roster.length === 0 ? (
                      <div className="text-gray-600 dark:text-gray-300">
                        No students enrolled yet. Share the join code to invite students.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {roster.slice(0, 20).map((s) => (
                          <div
                            key={s.uid}
                            className="flex items-center justify-between gap-4 p-4 rounded-xl border border-[#eae6f4] dark:border-[#2d2644] bg-white/50 dark:bg-white/5"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="size-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
                                {(String(s.name || s.uid || '').slice(0, 2) || 'ST').toUpperCase()}
                              </div>
                              <div className="min-w-0">
                                <div className="font-bold text-[#110d1c] dark:text-white truncate">
                                  {s.name || s.uid}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                  {s.email || s.uid}
                                </div>
                              </div>
                            </div>
                            <button
                              onClick={async () => {
                                try {
                                  await navigator.clipboard.writeText(s.uid);
                                } catch {}
                              }}
                              className="px-3 py-2 rounded-lg border border-[#eae6f4] dark:border-[#2d2644] text-xs font-bold text-gray-600 dark:text-gray-300 hover:border-primary/40 transition-colors"
                              type="button"
                            >
                              Copy UID
                            </button>
                          </div>
                        ))}
                        {roster.length > 20 ? (
                          <div className="text-xs text-gray-500 dark:text-gray-400 md:col-span-2">
                            Showing 20 of {roster.length} students.
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </main>
        </>
      ) : (
        <>
          <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-slate-200 dark:border-slate-800 bg-white dark:bg-background-dark px-6 md:px-10 py-3 sticky top-0 z-50">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-4 text-slate-900 dark:text-white">
                <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white">
                  <span className="material-symbols-outlined">event_upcoming</span>
                </div>
                <h2 className="text-slate-900 dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
                  Task Scheduling Agent
                </h2>
              </div>
              <nav className="hidden md:flex items-center gap-9">
                <button
                  className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors"
                  onClick={() => navigate('/student/dashboard')}
                >
                  Dashboard
                </button>
                <button className="text-primary text-sm font-bold leading-normal">My Subjects</button>
                <button className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors">
                  Calendar
                </button>
                <button className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors">
                  Reports
                </button>
              </nav>
            </div>
            <div className="flex flex-1 justify-end gap-6">
              <label className="hidden md:flex flex-col min-w-40 h-10 max-w-64">
                <div className="flex w-full flex-1 items-stretch rounded-lg h-full overflow-hidden border border-slate-200 dark:border-slate-700">
                  <div className="text-slate-400 flex bg-slate-50 dark:bg-slate-800 items-center justify-center pl-4">
                    <span className="material-symbols-outlined text-xl">search</span>
                  </div>
                  <input
                    className="form-input flex w-full min-w-0 flex-1 border-none bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-0 placeholder:text-slate-400 px-4 text-sm font-normal"
                    placeholder="Search tasks..."
                    value={taskSearch}
                    onChange={(e) => setTaskSearch(e.target.value)}
                  />
                </div>
              </label>
              <div className="flex gap-2">
                <button className="flex items-center justify-center rounded-lg size-10 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                  <span className="material-symbols-outlined">notifications</span>
                </button>
                <button className="flex items-center justify-center rounded-lg size-10 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                  <span className="material-symbols-outlined">settings</span>
                </button>
              </div>
              <div className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 ring-2 ring-slate-100 dark:ring-slate-800 bg-gradient-to-br from-primary/20 to-primary/5"></div>
            </div>
          </header>

          <main className="max-w-[1200px] mx-auto px-6 py-8">
            <nav className="flex items-center gap-2 mb-6">
              <button
                className="text-slate-500 hover:text-primary text-sm font-medium transition-colors"
                onClick={() => navigate('/student/dashboard')}
              >
                My Subjects
              </button>
              <span className="text-slate-400 material-symbols-outlined text-sm">chevron_right</span>
              <span className="text-slate-900 dark:text-white text-sm font-semibold">{subject?.name || 'Subject'}</span>
            </nav>

            {(error || tasksError || mySubmissionsError) && (
              <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error || tasksError || mySubmissionsError}
              </div>
            )}

            {isLoading ? (
              <div className="text-slate-600 dark:text-slate-400">Loading...</div>
            ) : !subject ? (
              <div className="text-slate-600 dark:text-slate-400">Subject not found.</div>
            ) : (
              <>
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 mb-8 shadow-sm">
                  <div className="flex flex-col md:flex-row md:items-center gap-6">
                    <div className="bg-primary/10 rounded-xl size-32 flex items-center justify-center overflow-hidden">
                      <div className="bg-gradient-to-br from-primary/20 to-primary/5 size-full"></div>
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-3 mb-1">
                        <h1 className="text-slate-900 dark:text-white text-3xl font-extrabold tracking-tight">
                          {subject.name}
                        </h1>
                        <span className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs font-bold px-2 py-1 rounded-full uppercase tracking-wider">
                          Active Subject
                        </span>
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                          <span className="material-symbols-outlined text-lg">person</span>
                          <span className="text-base font-medium leading-normal">{subject.teacher_uid}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-500">
                          <span className="material-symbols-outlined text-lg">fingerprint</span>
                          <span className="text-sm font-mono bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                            Join Code: {subject.join_code}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <button className="px-5 py-2.5 bg-primary text-white font-bold rounded-lg shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all flex items-center gap-2">
                        <span className="material-symbols-outlined">forum</span>
                        Contact Teacher
                      </button>
                    </div>
                  </div>
                </div>

                <div className="border-b border-slate-200 dark:border-slate-800 mb-8 overflow-x-auto">
                  <div className="flex gap-8 min-w-max">
                    {[
                      { key: 'all', label: 'All Tasks', count: studentTabCounts.all },
                      { key: 'pending', label: 'Pending', count: studentTabCounts.pending },
                      { key: 'completed', label: 'Completed', count: studentTabCounts.completed },
                      { key: 'resources', label: 'Resources', count: studentTabCounts.resources },
                    ].map((t) => (
                      <button
                        key={t.key}
                        className={`flex flex-col items-center justify-center border-b-2 pb-3 transition-all ${
                          studentTab === t.key
                            ? 'border-primary text-primary'
                            : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-primary'
                        }`}
                        onClick={() => setStudentTab(t.key)}
                      >
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-bold leading-normal tracking-wide">{t.label}</p>
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                            {t.count}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-slate-900 dark:text-white text-xl font-bold">
                    {studentTab === 'all'
                      ? 'All Tasks'
                      : studentTab === 'pending'
                      ? 'Pending Tasks'
                      : studentTab === 'completed'
                      ? 'Completed Tasks'
                      : 'Resources'}
                  </h2>
                  <div className="flex items-center gap-2 text-slate-500 text-sm font-medium cursor-pointer hover:text-primary">
                    <span>View Full Calendar</span>
                    <span className="material-symbols-outlined text-lg">calendar_month</span>
                  </div>
                </div>

                {tasksLoading || mySubmissionsLoading ? (
                  <div className="text-slate-600 dark:text-slate-400">Loading tasks...</div>
                ) : visibleTasks.length === 0 ? (
                  <div className="text-slate-600 dark:text-slate-400">No tasks yet.</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {visibleTasks.map((task) => {
                      const resource = isResourceTask(task);
                      const status = getStudentTaskStatus(task);
                      const submission = mySubmissionByTaskId.get(task.id);
                      const badge = resource
                        ? {
                            className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
                            icon: 'menu_book',
                            label: task.task_type || 'Reading',
                          }
                        : status === 'graded'
                        ? {
                            className:
                              'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
                            icon: 'check_circle',
                            label: 'Completed',
                          }
                        : status === 'submitted'
                        ? {
                            className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
                            icon: 'pending',
                            label: 'Submitted',
                          }
                        : status === 'missing'
                        ? {
                            className: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
                            icon: 'error',
                            label: 'Missing',
                          }
                        : {
                            className: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
                            icon: 'schedule',
                            label: 'Not Started',
                          };

                      return (
                        <button
                          key={task.id}
                          onClick={() => navigate(`/task/${task.id}`)}
                          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm transition-all hover:border-primary/40 hover:bg-primary/[0.02] text-left"
                        >
                          <div className="flex justify-between items-start mb-4">
                            <div
                              className={`${badge.className} px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider flex items-center gap-1`}
                            >
                              <span className="material-symbols-outlined text-sm">{badge.icon}</span>
                              {badge.label}
                            </div>
                            <span className="text-slate-400 material-symbols-outlined hover:text-primary transition-colors">
                              more_horiz
                            </span>
                          </div>
                          <h3 className="text-slate-900 dark:text-white font-bold text-lg mb-2 leading-tight">
                            {task.title}
                          </h3>
                          <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">
                            {task.description || 'No description.'}
                          </p>
                          <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                              <span className="material-symbols-outlined text-sm">event</span>
                              <span className="text-xs font-bold">
                                {formatDeadline(task.deadline) ? `Due ${formatDeadline(task.deadline)}` : 'No deadline'}
                              </span>
                            </div>
                            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                              {status === 'graded' && submission ? (
                                <span className="text-primary text-xs font-bold">
                                  Grade: {submission.score ?? '—'}
                                  {typeof task.points === 'number' ? `/${task.points}` : ''}
                                </span>
                              ) : (
                                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                                  {status === 'missing' ? 'Overdue' : ' '}
                                </span>
                              )}
                              <div
                                className="bg-primary text-white px-4 py-2 rounded-lg text-xs font-bold hover:bg-primary/90 transition-all cursor-pointer select-none"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/task/${task.id}`);
                                }}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    navigate(`/task/${task.id}`);
                                  }
                                }}
                              >
                                {status === 'graded' ? 'Review' : 'View Details'}
                              </div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </main>
        </>
      )}

      {userRole === 'teacher' && isCreateTaskOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/60 backdrop-blur-sm">
          <div
            className="absolute inset-0"
            onClick={() => {
              if (taskCreating) return;
              setIsCreateTaskOpen(false);
            }}
          ></div>
          <div className="relative bg-white dark:bg-[#1c1633] w-full max-w-[600px] rounded-2xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
              <h2 className="text-xl font-bold text-[#110d1c] dark:text-white">Create New Task</h2>
              <button
                className="text-gray-400 hover:text-gray-600 transition-colors"
                onClick={() => {
                  if (taskCreating) return;
                  setIsCreateTaskOpen(false);
                }}
                type="button"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="p-6 space-y-6">
              {taskCreateError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {taskCreateError}
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Task Title
                  </label>
                  <input
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                    placeholder="e.g. Weekly Quiz 4"
                    type="text"
                    value={taskTitle}
                    onChange={(e) => {
                      setTaskTitle(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Deadline</label>
                  <input
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                    type="datetime-local"
                    value={taskDeadline}
                    onChange={(e) => {
                      setTaskDeadline(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Points</label>
                  <input
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                    type="number"
                    value={taskPoints}
                    onChange={(e) => {
                      setTaskPoints(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Task Type</label>
                  <select
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                    value={taskType}
                    onChange={(e) => {
                      setTaskType(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  >
                    <option value="">Select</option>
                    <option value="Quiz">Quiz</option>
                    <option value="Assignment">Assignment</option>
                    <option value="Project">Project</option>
                    <option value="Extra Credit">Extra Credit</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    Description
                  </label>
                  <textarea
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                    placeholder="Describe the objectives and requirements..."
                    rows="4"
                    value={taskDescription}
                    onChange={(e) => {
                      setTaskDescription(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  ></textarea>
                </div>
              </div>
            </div>
            <div className="p-6 bg-gray-50 dark:bg-gray-900/50 flex justify-end gap-3">
              <button
                className="px-6 py-2.5 rounded-lg text-sm font-bold text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
                onClick={() => {
                  if (taskCreating) return;
                  setIsCreateTaskOpen(false);
                }}
                type="button"
                disabled={taskCreating}
              >
                Cancel
              </button>
              <button
                className="px-8 py-2.5 rounded-lg bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-60"
                onClick={async () => {
                  setTaskCreating(true);
                  setTaskCreateError('');
                  try {
                    const payload = {
                      subject_id: id,
                      title: taskTitle,
                      description: taskDescription ? taskDescription : null,
                      deadline: taskDeadline ? new Date(taskDeadline).toISOString() : null,
                      points: taskPoints !== '' ? Number(taskPoints) : null,
                      task_type: taskType ? taskType : null,
                    };
                    const response = await api.post('/tasks', payload);
                    setTasks((prev) => [response.data, ...prev]);
                    setTaskTitle('');
                    setTaskDescription('');
                    setTaskDeadline('');
                    setTaskPoints('');
                    setTaskType('');
                    setIsCreateTaskOpen(false);
                  } catch (err) {
                    setTaskCreateError(err?.response?.data?.detail || 'Failed to create task');
                  } finally {
                    setTaskCreating(false);
                  }
                }}
                disabled={!taskTitle.trim() || taskCreating}
                type="button"
              >
                {taskCreating ? 'Publishing...' : 'Publish Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SubjectView;
