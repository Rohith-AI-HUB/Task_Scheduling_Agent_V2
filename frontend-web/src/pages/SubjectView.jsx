import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const SubjectView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userRole, backendUser } = useAuth();
  const tasksSectionRef = useRef(null);
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
  const [taskKind, setTaskKind] = useState('individual');
  const [groupSize, setGroupSize] = useState('3');
  const [problemStatements, setProblemStatements] = useState(['']);
  const [bulkProblems, setBulkProblems] = useState('');
  const [previewNonce, setPreviewNonce] = useState(0);
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
  const [isHeaderMenuOpen, setIsHeaderMenuOpen] = useState(false);
  const [isExtensionOpen, setIsExtensionOpen] = useState(false);
  const [extensionTask, setExtensionTask] = useState(null);
  const [extensionDeadline, setExtensionDeadline] = useState('');
  const [extensionReason, setExtensionReason] = useState('');
  const [extensionError, setExtensionError] = useState('');
  const [extensionSubmitting, setExtensionSubmitting] = useState(false);
  const [extensionSuccess, setExtensionSuccess] = useState('');

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

  const resolvePhotoUrl = (photoUrl) => {
    if (!photoUrl) return '';
    const u = String(photoUrl);
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    const root = String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');
    return `${root}${u}`;
  };

  const groupPreview = useMemo(() => {
    if (taskKind !== 'group') return null;
    const size = Number(groupSize);
    if (!Number.isFinite(size) || size < 2) return null;
    const students = (roster || []).map((s) => s?.uid).filter(Boolean);
    if (students.length === 0) return { groupCount: 0, groups: [] };

    const shuffled = [...students];
    for (let i = shuffled.length - 1; i > 0; i -= 1) {
      const r = (Math.random() + previewNonce * 0.000001) % 1;
      const j = Math.floor(r * (i + 1));
      const tmp = shuffled[i];
      shuffled[i] = shuffled[j];
      shuffled[j] = tmp;
    }

    const fullCount = Math.floor(shuffled.length / size);
    const remainder = shuffled.length % size;
    const groups = [];
    let idx = 0;
    for (let k = 0; k < fullCount; k += 1) {
      groups.push(shuffled.slice(idx, idx + size));
      idx += size;
    }
    if (remainder) {
      const leftover = shuffled.slice(idx);
      if (groups.length === 0) {
        groups.push(leftover);
      } else {
        leftover.forEach((uid, i) => {
          groups[i % groups.length].push(uid);
        });
      }
    }

    const normalizedProblems = (problemStatements || []).map((p) => String(p || '').trim()).filter(Boolean);
    const preview = groups.slice(0, 3).map((members, i) => ({
      members,
      problem: normalizedProblems.length ? normalizedProblems[i % normalizedProblems.length] : null,
    }));
    return { groupCount: groups.length, groups: preview };
  }, [taskKind, groupSize, problemStatements, roster, previewNonce]);

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
      if (status === 'submitted') counts.completed += 1;
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
            if (studentTab === 'completed') return status === 'submitted';
            if (studentTab === 'pending') return status !== 'submitted';
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

  const formatDateInputValue = (value) => {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    const offset = d.getTimezoneOffset();
    const local = new Date(d.getTime() - offset * 60000);
    return local.toISOString().slice(0, 16);
  };

  const openExtensionRequest = (task) => {
    if (!task?.deadline) return;
    setExtensionTask(task);
    setExtensionReason('');
    setExtensionError('');
    setExtensionSuccess('');
    const base = new Date(task.deadline);
    if (!Number.isNaN(base.getTime())) {
      base.setDate(base.getDate() + 1);
      setExtensionDeadline(formatDateInputValue(base));
    } else {
      setExtensionDeadline('');
    }
    setIsExtensionOpen(true);
  };

  const handleSubmitExtension = async () => {
    if (!extensionTask) return;
    const reason = extensionReason.trim();
    if (!extensionDeadline) {
      setExtensionError('Select a requested deadline');
      return;
    }
    if (reason.length < 10) {
      setExtensionError('Reason must be at least 10 characters');
      return;
    }

    const currentDeadline = new Date(extensionTask.deadline);
    const requested = new Date(extensionDeadline);
    if (Number.isNaN(requested.getTime())) {
      setExtensionError('Requested deadline is invalid');
      return;
    }
    if (currentDeadline instanceof Date && !Number.isNaN(currentDeadline.getTime())) {
      if (requested.getTime() <= currentDeadline.getTime()) {
        setExtensionError('Requested deadline must be after current deadline');
        return;
      }
    }

    setExtensionSubmitting(true);
    setExtensionError('');
    setExtensionSuccess('');
    try {
      await api.post('/extensions', {
        task_id: extensionTask.id,
        requested_deadline: requested.toISOString(),
        reason,
      });
      setExtensionSuccess('Extension request submitted');
    } catch (err) {
      setExtensionError(getErrorMessage(err, 'Failed to submit extension request'));
    } finally {
      setExtensionSubmitting(false);
    }
  };

  const scrollToTasks = () => {
    const el = tasksSectionRef.current || document.getElementById('subject-tasks');
    if (!el || typeof el.scrollIntoView !== 'function') return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
                  type="button"
                >
                  Dashboard
                </button>
                <button className="text-primary text-sm font-bold leading-normal">Subjects</button>
                <button
                  className="text-[#110d1c] dark:text-gray-300 text-sm font-medium leading-normal hover:text-primary transition-colors"
                  onClick={scrollToTasks}
                  type="button"
                >
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

                <div ref={tasksSectionRef} id="subject-tasks" className="flex items-center justify-between mb-6 gap-4">
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
          <header className="border-b border-solid border-slate-200 dark:border-slate-800 bg-white dark:bg-background-dark sticky top-0 z-50">
            <div className="px-4 sm:px-6 md:px-10 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white shrink-0">
                    <span className="material-symbols-outlined">event_upcoming</span>
                  </div>
                  <h2 className="text-slate-900 dark:text-white text-base sm:text-lg font-bold leading-tight tracking-[-0.015em] truncate">
                    Task Scheduling Agent
                  </h2>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    className="md:hidden flex items-center justify-center rounded-lg size-10 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    onClick={() => setIsHeaderMenuOpen((v) => !v)}
                    type="button"
                  >
                    <span className="material-symbols-outlined">{isHeaderMenuOpen ? 'close' : 'menu'}</span>
                  </button>
                  <button className="flex items-center justify-center rounded-lg size-10 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                    <span className="material-symbols-outlined">notifications</span>
                  </button>
                  <button
                    className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 ring-2 ring-slate-100 dark:ring-slate-800 bg-gradient-to-br from-primary/20 to-primary/5 overflow-hidden"
                    onClick={() => navigate('/profile')}
                    type="button"
                  >
                    {backendUser?.photo_url ? (
                      <img
                        alt="Profile"
                        className="h-full w-full object-cover"
                        referrerPolicy="no-referrer"
                        src={resolvePhotoUrl(backendUser.photo_url)}
                      />
                    ) : (
                      <span className="material-symbols-outlined text-slate-500 dark:text-slate-300">person</span>
                    )}
                  </button>
                </div>
              </div>

              <div className={`${isHeaderMenuOpen ? 'flex' : 'hidden'} md:flex flex-col md:flex-row md:items-center gap-3 md:gap-6`}>
                <nav className="flex flex-col md:flex-row items-start md:items-center gap-2 md:gap-9">
                  <button
                    className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors"
                    onClick={() => {
                      setIsHeaderMenuOpen(false);
                      navigate('/student/dashboard');
                    }}
                    type="button"
                  >
                    Dashboard
                  </button>
                  <button className="text-primary text-sm font-bold leading-normal" type="button">
                    My Subjects
                  </button>
                  <button
                    className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors"
                    onClick={() => {
                      setIsHeaderMenuOpen(false);
                      navigate('/calendar');
                    }}
                    type="button"
                  >
                    Calendar
                  </button>
                  <button className="text-slate-600 dark:text-slate-400 hover:text-primary text-sm font-medium leading-normal transition-colors" type="button">
                    Reports
                  </button>
                </nav>

                <label className="flex flex-col w-full md:min-w-40 md:max-w-64">
                  <div className="flex w-full items-stretch rounded-lg h-10 overflow-hidden border border-slate-200 dark:border-slate-700">
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
              </div>
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
                  <button
                    className="flex items-center gap-2 text-slate-500 text-sm font-medium hover:text-primary transition-colors"
                    onClick={() => navigate('/calendar')}
                    type="button"
                  >
                    <span>View Full Calendar</span>
                    <span className="material-symbols-outlined text-lg">calendar_month</span>
                  </button>
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
                        : status === 'submitted'
                        ? {
                            className:
                              'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
                            icon: 'check_circle',
                            label: 'Completed',
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
                              className={`${badge.className} inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider leading-none whitespace-nowrap shrink-0 min-w-0 max-w-[70%]`}
                            >
                              <span className="material-symbols-outlined text-[14px] shrink-0">{badge.icon}</span>
                              <span className="truncate">{badge.label}</span>
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
                              <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                                {status === 'missing' ? 'Overdue' : ' '}
                              </span>
                              <div className="flex items-center gap-2">
                                {userRole === 'student' && task.deadline && status !== 'submitted' ? (
                                  <div
                                    className="border border-primary text-primary px-3 py-2 rounded-lg text-xs font-bold hover:bg-primary/10 transition-all cursor-pointer select-none"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      openExtensionRequest(task);
                                    }}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        openExtensionRequest(task);
                                      }
                                    }}
                                  >
                                    Request Extension
                                  </div>
                                ) : null}
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
                                    View Details
                                  </div>
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

      {userRole === 'student' && isExtensionOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/60 backdrop-blur-sm">
          <div
            className="absolute inset-0"
            onClick={() => {
              if (extensionSubmitting) return;
              setIsExtensionOpen(false);
            }}
          ></div>
          <div className="relative bg-white dark:bg-[#1c1633] w-full max-w-[520px] max-h-[90vh] flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
              <h2 className="text-xl font-bold text-[#110d1c] dark:text-white">Request Extension</h2>
              <button
                className="text-gray-400 hover:text-gray-600 transition-colors"
                onClick={() => {
                  if (extensionSubmitting) return;
                  setIsExtensionOpen(false);
                }}
                type="button"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="p-6 space-y-5 flex-1 min-h-0 overflow-y-auto">
              {extensionError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {extensionError}
                </div>
              )}
              {extensionSuccess && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-600 dark:text-emerald-400 text-sm">
                  {extensionSuccess}
                </div>
              )}
              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#110d1c] dark:text-white">
                  {extensionTask?.title || 'Selected Task'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Current deadline: {formatDeadline(extensionTask?.deadline) || 'No deadline'}
                </p>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">Requested deadline</label>
                <input
                  className="h-11 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-[#221a3b] px-3 text-sm text-[#110d1c] dark:text-white focus:border-primary focus:ring-1 focus:ring-primary"
                  type="datetime-local"
                  value={extensionDeadline}
                  onChange={(e) => {
                    setExtensionDeadline(e.target.value);
                    setExtensionError('');
                    setExtensionSuccess('');
                  }}
                  disabled={extensionSubmitting}
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">Reason</label>
                <textarea
                  className="min-h-[120px] w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-[#221a3b] px-3 py-2 text-sm text-[#110d1c] dark:text-white focus:border-primary focus:ring-1 focus:ring-primary"
                  value={extensionReason}
                  onChange={(e) => {
                    setExtensionReason(e.target.value);
                    setExtensionError('');
                    setExtensionSuccess('');
                  }}
                  disabled={extensionSubmitting}
                />
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 dark:border-gray-800 flex justify-end gap-3">
              <button
                className="px-5 py-2.5 rounded-lg text-sm font-bold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                onClick={() => {
                  if (extensionSubmitting) return;
                  setIsExtensionOpen(false);
                }}
                type="button"
                disabled={extensionSubmitting}
              >
                Close
              </button>
              <button
                className="px-6 py-2.5 rounded-lg bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-60"
                onClick={handleSubmitExtension}
                type="button"
                disabled={extensionSubmitting || !extensionDeadline || extensionReason.trim().length < 10}
              >
                {extensionSubmitting ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </div>
        </div>
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
          <div className="relative bg-white dark:bg-[#1c1633] w-full max-w-[600px] max-h-[90vh] flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
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
            <div className="p-6 space-y-6 flex-1 min-h-0 overflow-y-auto">
              {taskCreateError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {taskCreateError}
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                    Task Title
                  </label>
                  <input
                    className="w-full h-11 px-3 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
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
                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                    Individual vs Group
                  </label>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className={`h-11 px-4 rounded-lg text-base font-bold border transition-colors ${
                        taskKind === 'individual'
                          ? 'bg-primary text-white border-primary'
                          : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:border-primary/40'
                      }`}
                      onClick={() => {
                        if (taskCreating) return;
                        setTaskKind('individual');
                        setTaskCreateError('');
                      }}
                      disabled={taskCreating}
                    >
                      Individual
                    </button>
                    <button
                      type="button"
                      className={`h-11 px-4 rounded-lg text-base font-bold border transition-colors ${
                        taskKind === 'group'
                          ? 'bg-primary text-white border-primary'
                          : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:border-primary/40'
                      }`}
                      onClick={() => {
                        if (taskCreating) return;
                        setTaskKind('group');
                        setTaskCreateError('');
                      }}
                      disabled={taskCreating}
                    >
                      Group
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Deadline</label>
                  <input
                    className="w-full h-11 px-3 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
                    type="datetime-local"
                    value={taskDeadline}
                    onChange={(e) => {
                      setTaskDeadline(e.target.value);
                      setTaskCreateError('');
                    }}
                    disabled={taskCreating}
                  />
                </div>
                {taskKind === 'group' ? (
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                      Group Size
                    </label>
                    <input
                      className="w-full h-11 px-3 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
                      type="number"
                      min={2}
                      value={groupSize}
                      onChange={(e) => {
                        setGroupSize(e.target.value);
                        setTaskCreateError('');
                      }}
                      disabled={taskCreating}
                    />
                  </div>
                ) : null}
                <div>
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                    {taskKind === 'group' ? 'Points (optional)' : 'Points'}
                  </label>
                  <input
                    className="w-full h-11 px-3 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
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
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Task Type</label>
                  <select
                    className="w-full h-11 px-3 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
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
                  <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    className="w-full px-3 py-2.5 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-base"
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

                {taskKind === 'group' ? (
                  <div className="md:col-span-2 space-y-3">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Problem Statements</label>
                      <button
                        type="button"
                        className="px-4 py-2 rounded-lg text-sm font-bold border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors"
                        onClick={() => {
                          setProblemStatements((prev) => [...(prev || []), '']);
                        }}
                        disabled={taskCreating}
                      >
                        Add
                      </button>
                    </div>

                    <div className="space-y-2">
                      {(problemStatements || []).map((p, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            className="flex-1 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                            type="text"
                            placeholder={`Problem ${idx + 1}`}
                            value={p}
                            onChange={(e) => {
                              const v = e.target.value;
                              setProblemStatements((prev) =>
                                (prev || []).map((x, i) => (i === idx ? v : x))
                              );
                              setTaskCreateError('');
                            }}
                            disabled={taskCreating}
                          />
                          <button
                            type="button"
                            className="px-2 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors disabled:opacity-50"
                            onClick={() => {
                              if (idx === 0) return;
                              setProblemStatements((prev) => {
                                const next = [...(prev || [])];
                                const tmp = next[idx - 1];
                                next[idx - 1] = next[idx];
                                next[idx] = tmp;
                                return next;
                              });
                            }}
                            disabled={taskCreating || idx === 0}
                            title="Move up"
                          >
                            <span className="material-symbols-outlined text-base">arrow_upward</span>
                          </button>
                          <button
                            type="button"
                            className="px-2 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors disabled:opacity-50"
                            onClick={() => {
                              setProblemStatements((prev) => {
                                const next = [...(prev || [])];
                                if (idx >= next.length - 1) return next;
                                const tmp = next[idx + 1];
                                next[idx + 1] = next[idx];
                                next[idx] = tmp;
                                return next;
                              });
                            }}
                            disabled={taskCreating || idx === (problemStatements || []).length - 1}
                            title="Move down"
                          >
                            <span className="material-symbols-outlined text-base">arrow_downward</span>
                          </button>
                          <button
                            type="button"
                            className="px-2 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:border-red-400 transition-colors"
                            onClick={() => {
                              setProblemStatements((prev) => (prev || []).filter((_, i) => i !== idx));
                            }}
                            disabled={taskCreating}
                            title="Remove"
                          >
                            <span className="material-symbols-outlined text-base">delete</span>
                          </button>
                        </div>
                      ))}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 tracking-widest">
                        Bulk paste (one per line)
                      </label>
                      <textarea
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                        rows="3"
                        value={bulkProblems}
                        onChange={(e) => setBulkProblems(e.target.value)}
                        disabled={taskCreating}
                      ></textarea>
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          type="button"
                          className="px-4 py-2 rounded-lg text-sm font-bold border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors disabled:opacity-60"
                          onClick={() => {
                            const lines = String(bulkProblems || '')
                              .split('\n')
                              .map((x) => x.trim())
                              .filter(Boolean);
                            if (lines.length === 0) return;
                            setProblemStatements((prev) => {
                              const existing = (prev || []).map((x) => String(x || '').trim()).filter(Boolean);
                              return [...existing, ...lines];
                            });
                            setBulkProblems('');
                          }}
                          disabled={taskCreating}
                        >
                          Add Lines
                        </button>
                        <button
                          type="button"
                          className="px-4 py-2 rounded-lg text-sm font-bold border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors disabled:opacity-60"
                          onClick={() => setPreviewNonce((n) => n + 1)}
                          disabled={taskCreating}
                        >
                          Shuffle Preview
                        </button>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl border border-[#eae6f4] dark:border-[#2a2438] bg-[#faf9fc] dark:bg-[#221b36]">
                      <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="text-sm font-bold text-[#110d1c] dark:text-white">Group Preview</div>
                        <div className="text-xs text-[#5d479e] dark:text-[#a094c7]">
                          {groupPreview ? `Estimated groups: ${groupPreview.groupCount}` : 'Set group size to preview'}
                        </div>
                      </div>
                      {groupPreview && groupPreview.groups.length > 0 ? (
                        <div className="mt-3 space-y-2">
                          {groupPreview.groups.map((g, i) => (
                            <div key={i} className="text-sm text-[#4b3d75] dark:text-[#c0bad3]">
                              <span className="font-semibold">Group {i + 1}:</span> {g.members.join(', ')}
                              {g.problem ? <span className="ml-2 text-xs text-primary">({g.problem})</span> : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}
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
                      type: taskKind,
                    };
                    if (taskKind === 'group') {
                      const size = Number(groupSize);
                      if (!Number.isFinite(size) || size < 2) throw new Error('Group size must be at least 2');
                      const problems = (problemStatements || []).map((p) => String(p || '').trim()).filter(Boolean);
                      payload.problem_statements = problems;
                      payload.group_settings = { group_size: size, shuffle: true };
                    }
                    const response = await api.post('/tasks', payload);
                    setTasks((prev) => [response.data, ...prev]);
                    setTaskTitle('');
                    setTaskDescription('');
                    setTaskDeadline('');
                    setTaskPoints('');
                    setTaskType('');
                    setTaskKind('individual');
                    setGroupSize('3');
                    setProblemStatements(['']);
                    setBulkProblems('');
                    setPreviewNonce(0);
                    setIsCreateTaskOpen(false);
                  } catch (err) {
                    setTaskCreateError(getErrorMessage(err, 'Failed to create task'));
                  } finally {
                    setTaskCreating(false);
                  }
                }}
                disabled={
                  !taskTitle.trim() ||
                  taskCreating ||
                  (taskKind === 'group' && (!Number.isFinite(Number(groupSize)) || Number(groupSize) < 2))
                }
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
