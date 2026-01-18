import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import EvaluationResults from '../components/EvaluationResults';

const TaskView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { userRole } = useAuth();
  const [task, setTask] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [mySubmission, setMySubmission] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [submissionLoading, setSubmissionLoading] = useState(true);
  const [submissionError, setSubmissionError] = useState('');
  const [submissionContent, setSubmissionContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [attachmentsUploading, setAttachmentsUploading] = useState(false);
  const [attachmentsError, setAttachmentsError] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);
  const [myGroup, setMyGroup] = useState(null);
  const [groupList, setGroupList] = useState([]);
  const [groupListMeta, setGroupListMeta] = useState(null);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [groupsError, setGroupsError] = useState('');
  const [groupSearch, setGroupSearch] = useState('');
  const [groupSort, setGroupSort] = useState('name');
  const [collapsedGroups, setCollapsedGroups] = useState({});
  const fileInputRef = useRef(null);

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
  const [gradeFeedback, setGradeFeedback] = useState({});
  const [gradeScore, setGradeScore] = useState({});
  const [gradeLoading, setGradeLoading] = useState({});
  const [evaluationLoading, setEvaluationLoading] = useState({});
  const [batchEvaluationLoading, setBatchEvaluationLoading] = useState(false);
  const [evaluationSummary, setEvaluationSummary] = useState(null);
  const pendingReviewCount = useMemo(
    () => submissions.filter((s) => s?.score === null || s?.score === undefined).length,
    [submissions]
  );
  const groupById = useMemo(() => {
    const map = new Map();
    for (const g of groupList || []) {
      if (g?.id) map.set(g.id, g);
    }
    return map;
  }, [groupList]);
  const visibleGroups = useMemo(() => {
    const list = Array.isArray(groupList) ? [...groupList] : [];
    const q = String(groupSearch || '').trim().toLowerCase();
    const filtered = q
      ? list.filter((g) => {
          const name = String(g?.name || '').toLowerCase();
          const members = (g?.member_uids || []).map((u) => String(u).toLowerCase()).join(' ');
          return name.includes(q) || members.includes(q);
        })
      : list;

    if (groupSort === 'size') {
      filtered.sort((a, b) => (a?.member_uids?.length || 0) - (b?.member_uids?.length || 0));
    } else {
      filtered.sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || '')));
    }
    return filtered;
  }, [groupList, groupSearch, groupSort]);

  const getInitials = (studentUid) => {
    const raw = String(studentUid || '').trim();
    if (!raw) return 'ST';
    const parts = raw.split(/[^a-zA-Z0-9]+/).filter(Boolean);
    if (parts.length === 0) return raw.slice(0, 2).toUpperCase();
    const a = parts[0][0] || '';
    const b = (parts[1] ? parts[1][0] : parts[0][1] || '') || '';
    return `${a}${b}`.toUpperCase();
  };

  const formatDueShort = (deadline) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const formatDueLong = (deadline) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString();
  };

  const submitOrUpdate = async () => {
    setIsSubmitting(true);
    setSubmissionError('');
    try {
      const payload = { task_id: id, content: submissionContent };
      if (task?.type === 'group') {
        if (!myGroup?.id) throw new Error('Group not found');
        payload.group_id = myGroup.id;
      }
      const response = await api.post('/submissions', payload);
      setMySubmission(response.data);
    } catch (err) {
      setSubmissionError(getErrorMessage(err, 'Failed to submit'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const downloadAttachment = async (submissionId, attachment) => {
    try {
      const response = await api.get(`/submissions/${submissionId}/attachments/${attachment.id}`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: attachment.content_type || 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.filename || 'attachment';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setSubmissionError(getErrorMessage(err, 'Failed to download attachment'));
    }
  };

  const ensureSubmissionForAttachments = async () => {
    if (mySubmission) return mySubmission;
    const payload = { task_id: id, content: submissionContent || '' };
    if (task?.type === 'group') {
      if (!myGroup?.id) throw new Error('Group not found');
      payload.group_id = myGroup.id;
    }
    const response = await api.post('/submissions', payload);
    setMySubmission(response.data);
    return response.data;
  };

  const isAllowedFile = (file) => {
    const name = String(file?.name || '').toLowerCase();
    const okExt = ['.pdf', '.jpg', '.jpeg', '.png', '.zip'].some((ext) => name.endsWith(ext));
    return okExt;
  };

  const uploadFiles = async (files) => {
    const list = Array.from(files || []);
    if (list.length === 0) return;

    setAttachmentsError('');
    for (const f of list) {
      if (!isAllowedFile(f)) {
        setAttachmentsError('Only PDF, JPG, PNG or ZIP files are allowed.');
        return;
      }
      if (f.size > 25 * 1024 * 1024) {
        setAttachmentsError('Each file must be 25MB or less.');
        return;
      }
    }

    setAttachmentsUploading(true);
    try {
      const submission = await ensureSubmissionForAttachments();
      const form = new FormData();
      list.forEach((f) => form.append('files', f));
      const response = await api.post(`/submissions/${submission.id}/attachments`, form);
      setMySubmission(response.data);
    } catch (err) {
      setAttachmentsError(getErrorMessage(err, 'Failed to upload attachments'));
    } finally {
      setAttachmentsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const deleteAttachment = async (attachmentId) => {
    if (!mySubmission) return;
    setAttachmentsError('');
    setAttachmentsUploading(true);
    try {
      const response = await api.delete(`/submissions/${mySubmission.id}/attachments/${attachmentId}`);
      setMySubmission(response.data);
    } catch (err) {
      setAttachmentsError(getErrorMessage(err, 'Failed to delete attachment'));
    } finally {
      setAttachmentsUploading(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const response = await api.get(`/tasks/${id}`);
        setTask(response.data);
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to load task'));
      } finally {
        setIsLoading(false);
      }
    };
    if (id) load();
  }, [id]);

  const loadSubmissions = async () => {
    if (!id) return;
    setSubmissionLoading(true);
    setSubmissionError('');
    try {
      if (userRole === 'teacher') {
        const response = await api.get('/submissions', { params: { task_id: id } });
        setSubmissions(response.data || []);
        try {
          const summaryRes = await api.get(`/tasks/${id}/evaluations/summary`);
          setEvaluationSummary(summaryRes.data || null);
        } catch (err) {
          setEvaluationSummary(null);
        }
      } else if (userRole === 'student') {
        setEvaluationSummary(null);
        try {
          const response = await api.get('/submissions/me', { params: { task_id: id } });
          setMySubmission(response.data);
          setSubmissionContent(response.data?.content || '');
        } catch (err) {
          if (err?.response?.status === 404) {
            setMySubmission(null);
            setSubmissionContent('');
          } else {
            throw err;
          }
        }
      }
    } catch (err) {
      setSubmissionError(getErrorMessage(err, 'Failed to load submissions'));
    } finally {
      setSubmissionLoading(false);
    }
  };

  const triggerEvaluation = async (submissionId) => {
    if (!submissionId) return;
    setEvaluationLoading((prev) => ({ ...prev, [submissionId]: true }));
    setSubmissionError('');
    try {
      const response = await api.post(`/submissions/${submissionId}/evaluate`);
      setSubmissions((prev) => prev.map((s) => (s.id === submissionId ? response.data : s)));
    } catch (err) {
      setSubmissionError(getErrorMessage(err, 'Failed to trigger evaluation'));
    } finally {
      setEvaluationLoading((prev) => ({ ...prev, [submissionId]: false }));
    }
  };

  const batchEvaluate = async () => {
    if (!id) return;
    setBatchEvaluationLoading(true);
    setSubmissionError('');
    try {
      await api.post('/submissions/batch/evaluate', { task_id: id });
      await loadSubmissions();
    } catch (err) {
      setSubmissionError(getErrorMessage(err, 'Failed to batch evaluate'));
    } finally {
      setBatchEvaluationLoading(false);
    }
  };

  useEffect(() => {
    if (userRole !== 'teacher') return;

    const runningIds = submissions
      .filter((s) => s?.evaluation?.status === 'pending' || s?.evaluation?.status === 'running')
      .map((s) => s.id)
      .filter(Boolean);

    if (runningIds.length === 0) return;

    const pollInterval = setInterval(async () => {
      const results = await Promise.all(
        runningIds.map((sid) => api.get(`/submissions/${sid}/evaluation/progress`).catch(() => null))
      );
      const updated = results.some((r) => {
        const st = r?.data?.status;
        return st === 'completed' || st === 'failed';
      });
      if (updated) await loadSubmissions();
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [submissions, userRole]);

  useEffect(() => {
    loadSubmissions();
  }, [id, userRole]);

  const loadGroups = async () => {
    if (!id) return;
    if (task?.type !== 'group') {
      setMyGroup(null);
      setGroupList([]);
      setGroupListMeta(null);
      return;
    }

    setGroupsLoading(true);
    setGroupsError('');
    try {
      if (userRole === 'teacher') {
        const response = await api.get('/groups', { params: { task_id: id } });
        setGroupList(response.data?.groups || []);
        setGroupListMeta(response.data || null);
      } else if (userRole === 'student') {
        try {
          const response = await api.get('/groups/me', { params: { task_id: id } });
          setMyGroup(response.data || null);
        } catch (err) {
          if (err?.response?.status === 404) {
            setMyGroup(null);
          } else {
            throw err;
          }
        }
      }
    } catch (err) {
      setGroupsError(getErrorMessage(err, 'Failed to load groups'));
    } finally {
      setGroupsLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, [id, userRole, task?.type]);

  return (
    <div className="bg-background-light dark:bg-background-dark text-[#110d1c] dark:text-white h-screen overflow-y-auto overflow-x-hidden font-display">
      {userRole === 'teacher' ? (
        <>
          <header className="sticky top-0 z-50 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-md border-b border-[#eae6f4] dark:border-[#2a2438]">
            <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-3">
                  <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white">
                    <span className="material-symbols-outlined text-xl">assignment</span>
                  </div>
                  <h1 className="text-lg font-bold tracking-tight">Task Scheduling Agent</h1>
                </div>
                <nav className="hidden md:flex items-center gap-4 ml-8">
                  <button
                    className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
                    onClick={() => navigate(-1)}
                  >
                    <span className="material-symbols-outlined text-lg">arrow_back</span>
                    Back
                  </button>
                  <button
                    className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
                    onClick={() =>
                      task?.subject_id ? navigate(`/subject/${task.subject_id}`) : navigate('/teacher/dashboard')
                    }
                  >
                    <span className="material-symbols-outlined text-lg">school</span>
                    Go to Subject
                  </button>
                </nav>
              </div>
              <div className="flex items-center gap-4">
                <button className="bg-primary text-white text-sm font-bold px-4 py-2 rounded-lg hover:bg-primary/90 transition-all flex items-center gap-2">
                  <span className="material-symbols-outlined text-lg">person</span>
                  Teacher Profile
                </button>
                <div className="size-10 rounded-full bg-cover bg-center border-2 border-primary/20 bg-gradient-to-br from-primary/20 to-primary/5"></div>
              </div>
            </div>
          </header>

          <main className="max-w-[960px] mx-auto px-6 py-8">
            {(error || submissionError) && (
              <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error || submissionError}
              </div>
            )}

            {isLoading ? (
              <div className="text-gray-600 dark:text-gray-300">Loading...</div>
            ) : !task ? (
              <div className="text-gray-600 dark:text-gray-300">Task not found.</div>
            ) : (
              <>
                <div className="bg-white dark:bg-[#1c162e] rounded-xl shadow-sm border border-[#eae6f4] dark:border-[#2a2438] overflow-hidden mb-8">
                  <div className="flex flex-col md:flex-row">
                    <div className="w-full md:w-1/3 bg-gradient-to-br from-primary/20 to-primary/5 min-h-[160px]"></div>
                    <div className="p-6 flex-1 flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-start mb-2 gap-4">
                          <h2 className="text-2xl font-bold text-[#110d1c] dark:text-white">{task.title}</h2>
                          <span className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
                            Active
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-4 text-sm text-[#5d479e] dark:text-[#a094c7]">
                          <div className="flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-lg">calendar_today</span>
                            {formatDueShort(task.deadline) ? `Due ${formatDueShort(task.deadline)}` : 'No deadline'}
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-lg">grade</span>
                            {typeof task.points === 'number' ? `${task.points} pts` : 'No points'}
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-lg">group</span>
                            {task.type === 'individual' ? 'Individual Task' : task.type || 'Task'}
                          </div>
                        </div>
                      </div>
                      <div className="mt-6 flex justify-end">
                        <button className="bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all text-sm font-bold px-5 py-2 rounded-lg flex items-center gap-2">
                          <span className="material-symbols-outlined text-lg">edit</span>
                          Edit Task
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <section className="mb-10">
                  <div className="flex items-center gap-2 mb-4 px-1">
                    <span className="material-symbols-outlined text-primary">description</span>
                    <h3 className="text-xl font-bold text-[#110d1c] dark:text-white">Task Description</h3>
                  </div>
                  <div className="bg-white dark:bg-[#1c162e] p-6 rounded-xl border border-[#eae6f4] dark:border-[#2a2438]">
                    <p className="text-[#4b3d75] dark:text-[#c0bad3] leading-relaxed whitespace-pre-wrap">
                      {task.description || 'No description.'}
                    </p>
                  </div>
                </section>

                {task.type === 'group' ? (
                  <section className="mb-10">
                    <div className="flex items-center justify-between mb-6 px-1 gap-4 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">groups</span>
                        <h3 className="text-xl font-bold text-[#110d1c] dark:text-white">Groups</h3>
                      </div>
                      <div className="flex items-center gap-3 flex-wrap">
                        <input
                          className="px-3 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-sm"
                          placeholder="Search UID or group..."
                          value={groupSearch}
                          onChange={(e) => setGroupSearch(e.target.value)}
                        />
                        <select
                          className="px-3 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-sm"
                          value={groupSort}
                          onChange={(e) => setGroupSort(e.target.value)}
                        >
                          <option value="name">Sort: Name</option>
                          <option value="size">Sort: Size</option>
                        </select>
                        <button
                          onClick={loadGroups}
                          className="px-4 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-sm font-bold hover:border-primary/40 transition-colors disabled:opacity-60"
                          disabled={groupsLoading}
                          type="button"
                        >
                          Refresh
                        </button>
                        {!groupListMeta?.group_set_id ? (
                          <button
                            onClick={async () => {
                              setGroupsLoading(true);
                              setGroupsError('');
                              try {
                                const response = await api.post('/groups', { task_id: id, regenerate: false });
                                setGroupList(response.data?.groups || []);
                                setGroupListMeta(response.data || null);
                              } catch (err) {
                                setGroupsError(getErrorMessage(err, 'Failed to generate groups'));
                              } finally {
                                setGroupsLoading(false);
                              }
                            }}
                            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-bold hover:bg-primary/90 transition-colors disabled:opacity-60"
                            disabled={groupsLoading}
                            type="button"
                          >
                            Generate Groups
                          </button>
                        ) : (
                          <button
                            onClick={async () => {
                              if (groupListMeta?.has_submissions) return;
                              const ok = window.confirm('Regenerate groups? This cannot be undone.');
                              if (!ok) return;
                              setGroupsLoading(true);
                              setGroupsError('');
                              try {
                                const response = await api.post('/groups', { task_id: id, regenerate: true });
                                setGroupList(response.data?.groups || []);
                                setGroupListMeta(response.data || null);
                              } catch (err) {
                                setGroupsError(getErrorMessage(err, 'Failed to regenerate groups'));
                              } finally {
                                setGroupsLoading(false);
                              }
                            }}
                            className="px-4 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-sm font-bold hover:border-primary/40 transition-colors disabled:opacity-60"
                            disabled={groupsLoading || !!groupListMeta?.has_submissions}
                            type="button"
                            title={groupListMeta?.has_submissions ? 'Disabled because submissions exist' : 'Regenerate groups'}
                          >
                            Regenerate Groups
                          </button>
                        )}
                      </div>
                    </div>

                    {groupsError ? (
                      <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                        {groupsError}
                      </div>
                    ) : null}

                    {groupsLoading ? (
                      <div className="text-[#5d479e] dark:text-[#a094c7]">Loading groups...</div>
                    ) : !groupListMeta?.group_set_id ? (
                      <div className="text-[#5d479e] dark:text-[#a094c7]">Groups not generated yet.</div>
                    ) : visibleGroups.length === 0 ? (
                      <div className="text-[#5d479e] dark:text-[#a094c7]">No groups found.</div>
                    ) : (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {visibleGroups.map((g) => {
                          const isCollapsed = !!collapsedGroups[g.id];
                          const hasSubmission = !!g.submission_id;
                          return (
                            <div
                              key={g.id}
                              className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] overflow-hidden shadow-sm"
                            >
                              <div className="p-4 border-b border-[#eae6f4] dark:border-[#2a2438] bg-[#faf9fc] dark:bg-[#221b36] flex items-start justify-between gap-3">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-bold text-[#110d1c] dark:text-white">{g.name}</h4>
                                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary">
                                      {g.member_uids?.length || 0} members
                                    </span>
                                    {hasSubmission ? (
                                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                                        Submitted
                                      </span>
                                    ) : (
                                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                                        Not submitted
                                      </span>
                                    )}
                                  </div>
                                  {g.assigned_problem_statement ? (
                                    <div className="mt-1 text-sm text-[#5d479e] dark:text-[#a094c7]">
                                      Problem: {g.assigned_problem_statement}
                                    </div>
                                  ) : null}
                                </div>
                                <div className="flex items-center gap-2">
                                  {g.submission_id ? (
                                    <button
                                      className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] hover:border-primary/40 transition-colors"
                                      type="button"
                                      onClick={() => {
                                        const el = document.getElementById(`submission-${g.submission_id}`);
                                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                      }}
                                    >
                                      View Submission
                                    </button>
                                  ) : null}
                                  <button
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] hover:border-primary/40 transition-colors"
                                    type="button"
                                    onClick={() => setCollapsedGroups((p) => ({ ...p, [g.id]: !p[g.id] }))}
                                  >
                                    {isCollapsed ? 'Expand' : 'Collapse'}
                                  </button>
                                </div>
                              </div>
                              {!isCollapsed ? (
                                <div className="p-4">
                                  <div className="flex flex-wrap gap-2">
                                    {(g.member_uids || []).map((uid) => (
                                      <button
                                        key={uid}
                                        type="button"
                                        className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#f0eff5] dark:bg-[#251e3b] text-[#3d2a78] dark:text-[#c0bad3] hover:opacity-80 transition-opacity"
                                        onClick={async () => {
                                          try {
                                            await navigator.clipboard.writeText(String(uid));
                                          } catch (_e) {
                                            setGroupsError('Copy failed');
                                          }
                                        }}
                                        title="Copy UID"
                                      >
                                        {uid}
                                      </button>
                                    ))}
                                  </div>
                                  {g.submission_id ? (
                                    <div className="mt-3 text-xs text-[#5d479e] dark:text-[#a094c7]">
                                      Last update:{' '}
                                      {g.submission_updated_at ? new Date(g.submission_updated_at).toLocaleString() : '—'} by{' '}
                                      {g.submitted_by_uid || '—'}
                                    </div>
                                  ) : null}
                                </div>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </section>
                ) : null}

                <section>
                  <div className="flex items-center justify-between mb-6 px-1 gap-4">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary">analytics</span>
                      <h3 className="text-xl font-bold text-[#110d1c] dark:text-white">Submissions</h3>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-sm font-medium text-[#5d479e] dark:text-[#a094c7] bg-[#f0eff5] dark:bg-[#251e3b] px-3 py-1 rounded-full">
                        {pendingReviewCount} Pending Review
                      </div>
                      {evaluationSummary?.average_ai_score !== null && evaluationSummary?.average_ai_score !== undefined ? (
                        <div className="text-sm font-medium text-[#5d479e] dark:text-[#a094c7] bg-[#f0eff5] dark:bg-[#251e3b] px-3 py-1 rounded-full">
                          AI Avg {Number(evaluationSummary.average_ai_score).toFixed(1)}
                        </div>
                      ) : null}
                      <button
                        onClick={batchEvaluate}
                        className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-bold hover:bg-primary/90 transition-colors disabled:opacity-60"
                        disabled={submissionLoading || batchEvaluationLoading}
                        type="button"
                      >
                        {batchEvaluationLoading ? 'Evaluating...' : 'Evaluate All'}
                      </button>
                      <button
                        onClick={loadSubmissions}
                        className="px-4 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-sm font-bold hover:border-primary/40 transition-colors disabled:opacity-60"
                        disabled={submissionLoading}
                        type="button"
                      >
                        Refresh
                      </button>
                    </div>
                  </div>

                  {/* Evaluation Analytics Dashboard */}
                  {evaluationSummary && submissions.length > 0 && (
                    <div className="mb-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {/* Total Submissions */}
                      <div className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] p-4">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-2">
                          <span className="material-symbols-outlined text-lg">assignment</span>
                          <p className="text-xs font-bold uppercase tracking-wider">Total Submissions</p>
                        </div>
                        <p className="text-3xl font-bold text-[#110d1c] dark:text-white">
                          {evaluationSummary.total_submissions || 0}
                        </p>
                      </div>

                      {/* Average AI Score */}
                      {evaluationSummary.average_ai_score !== null && evaluationSummary.average_ai_score !== undefined && (
                        <div className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] p-4">
                          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-2">
                            <span className="material-symbols-outlined text-lg">smart_toy</span>
                            <p className="text-xs font-bold uppercase tracking-wider">Avg AI Score</p>
                          </div>
                          <div className="flex items-baseline gap-2">
                            <p className="text-3xl font-bold text-primary">
                              {Number(evaluationSummary.average_ai_score).toFixed(1)}
                            </p>
                            <span className="text-sm text-gray-500 dark:text-gray-400">/100</span>
                          </div>
                        </div>
                      )}

                      {/* Evaluation Status Breakdown */}
                      {evaluationSummary.status_counts && Object.keys(evaluationSummary.status_counts).length > 0 && (
                        <div className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] p-4">
                          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-2">
                            <span className="material-symbols-outlined text-lg">assessment</span>
                            <p className="text-xs font-bold uppercase tracking-wider">Evaluation Status</p>
                          </div>
                          <div className="space-y-1">
                            {Object.entries(evaluationSummary.status_counts).map(([status, count]) => (
                              <div key={status} className="flex items-center justify-between text-sm">
                                <span className="capitalize text-gray-600 dark:text-gray-400">{status}:</span>
                                <span className="font-bold text-[#110d1c] dark:text-white">{count}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Quick Stats */}
                      <div className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] p-4">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-2">
                          <span className="material-symbols-outlined text-lg">trending_up</span>
                          <p className="text-xs font-bold uppercase tracking-wider">Quick Stats</p>
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600 dark:text-gray-400">Graded:</span>
                            <span className="font-bold text-emerald-600 dark:text-emerald-400">
                              {submissions.filter((s) => s.score !== null && s.score !== undefined).length}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600 dark:text-gray-400">Ungraded:</span>
                            <span className="font-bold text-amber-600 dark:text-amber-400">
                              {submissions.filter((s) => s.score === null || s.score === undefined).length}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600 dark:text-gray-400">With Feedback:</span>
                            <span className="font-bold text-blue-600 dark:text-blue-400">
                              {submissions.filter((s) => s.feedback && s.feedback.trim()).length}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {submissionLoading ? (
                    <div className="text-[#5d479e] dark:text-[#a094c7]">Loading submissions...</div>
                  ) : submissions.length === 0 ? (
                    <div className="text-[#5d479e] dark:text-[#a094c7]">No submissions yet.</div>
                  ) : (
                    <div className="space-y-6">
                      {submissions.map((s) => {
                        const isUngraded = s?.score === null || s?.score === undefined;
                        const group = s?.group_id ? groupById.get(s.group_id) : null;
                        const evalStatusRaw = String(s?.evaluation?.status || '').toLowerCase();
                        const evalStatus =
                          evalStatusRaw === 'pending' ||
                          evalStatusRaw === 'running' ||
                          evalStatusRaw === 'completed' ||
                          evalStatusRaw === 'failed'
                            ? evalStatusRaw
                            : null;
                        return (
                          <div
                            key={s.id}
                            id={`submission-${s.id}`}
                            className="bg-white dark:bg-[#1c162e] rounded-xl border border-[#eae6f4] dark:border-[#2a2438] overflow-hidden shadow-sm"
                          >
                            <div className="p-5 border-b border-[#eae6f4] dark:border-[#2a2438] flex justify-between items-center bg-[#faf9fc] dark:bg-[#221b36] gap-4">
                              <div className="flex items-center gap-3">
                                <div className="size-9 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-sm">
                                  {getInitials(s.student_uid)}
                                </div>
                                <div>
                                  <h4 className="font-bold text-sm text-[#110d1c] dark:text-white uppercase tracking-tight">
                                    Student UID: {s.student_uid}
                                  </h4>
                                  {group ? (
                                    <p className="text-xs text-[#5d479e] dark:text-[#a094c7]">Group: {group.name}</p>
                                  ) : null}
                                  <p className="text-xs text-[#5d479e] dark:text-[#a094c7]">
                                    Submitted {s.submitted_at ? new Date(s.submitted_at).toLocaleString() : '—'}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                {evalStatus ? (
                                  <span
                                    className={`text-xs font-semibold px-2 py-1 rounded ${
                                      evalStatus === 'completed'
                                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                        : evalStatus === 'failed'
                                          ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'
                                          : evalStatus === 'running'
                                            ? 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300'
                                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                                    }`}
                                  >
                                    AI {evalStatus}
                                  </span>
                                ) : null}
                                <span
                                  className={`text-xs font-semibold px-2 py-1 rounded ${
                                    isUngraded
                                      ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                                      : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                  }`}
                                >
                                  {isUngraded ? 'Ungraded' : 'Graded'}
                                </span>
                              </div>
                            </div>
                            <div className="p-6">
                              <div className="mb-6">
                                <h5 className="text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-2 tracking-widest">
                                  Submitted Text
                                </h5>
                                <div className="bg-[#f9f8fc] dark:bg-[#140f23] p-4 rounded-lg text-sm leading-relaxed border border-[#eae6f4] dark:border-[#2a2438] whitespace-pre-wrap">
                                  {s.content || '—'}
                                </div>
                              </div>

                              {Array.isArray(s.attachments) && s.attachments.length > 0 ? (
                                <div className="mb-6">
                                  <h5 className="text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-2 tracking-widest">
                                    Attachments
                                  </h5>
                                  <div className="flex flex-wrap gap-2">
                                    {s.attachments.map((a) => (
                                      <button
                                        key={a.id}
                                        className="px-3 py-2 rounded-lg border border-[#eae6f4] dark:border-[#2a2438] bg-white/60 dark:bg-white/5 text-xs font-bold hover:border-primary/40 transition-colors flex items-center gap-2"
                                        onClick={() => downloadAttachment(s.id, a)}
                                        type="button"
                                      >
                                        <span className="material-symbols-outlined text-base">attach_file</span>
                                        <span className="max-w-[220px] truncate">{a.filename}</span>
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              ) : null}

                              <div className="mb-6">
                                <div className="flex items-center justify-between mb-3">
                                  <h5 className="text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase tracking-widest">
                                    Evaluation
                                  </h5>
                                  <button
                                    className="px-3 py-2 rounded-lg bg-white dark:bg-[#1c162e] border border-[#eae6f4] dark:border-[#2a2438] text-xs font-bold hover:border-primary/40 transition-colors disabled:opacity-60"
                                    disabled={!!evaluationLoading[s.id]}
                                    onClick={() => triggerEvaluation(s.id)}
                                    type="button"
                                  >
                                    {evaluationLoading[s.id] ? 'Starting...' : 'Evaluate'}
                                  </button>
                                </div>
                                <EvaluationResults evaluation={s?.evaluation} taskPoints={task?.points} />
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
                                <div className="md:col-span-1">
                                  <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-2 tracking-widest">
                                    Score{typeof task.points === 'number' ? ` / ${task.points}` : ''}
                                  </label>
                                  <input
                                    className="w-full bg-[#f9f8fc] dark:bg-[#140f23] border-[#eae6f4] dark:border-[#2a2438] rounded-lg focus:ring-primary focus:border-primary text-sm font-bold h-11"
                                    placeholder="--"
                                    type="number"
                                    value={gradeScore[s.id] ?? (s.score ?? '')}
                                    onChange={(e) => setGradeScore((prev) => ({ ...prev, [s.id]: e.target.value }))}
                                    disabled={!!gradeLoading[s.id]}
                                  />
                                </div>
                                <div className="md:col-span-2">
                                  <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-2 tracking-widest">
                                    Feedback
                                  </label>
                                  <textarea
                                    className="w-full bg-[#f9f8fc] dark:bg-[#140f23] border-[#eae6f4] dark:border-[#2a2438] rounded-lg focus:ring-primary focus:border-primary text-sm h-11 py-2.5"
                                    placeholder="Add a comment..."
                                    rows="1"
                                    value={gradeFeedback[s.id] ?? (s.feedback ?? '')}
                                    onChange={(e) =>
                                      setGradeFeedback((prev) => ({ ...prev, [s.id]: e.target.value }))
                                    }
                                    disabled={!!gradeLoading[s.id]}
                                  ></textarea>
                                </div>
                                <div className="md:col-span-1">
                                  <button
                                    className="w-full bg-primary text-white font-bold py-2.5 rounded-lg hover:bg-primary/90 transition-all text-sm flex items-center justify-center gap-2 disabled:opacity-60"
                                    disabled={!!gradeLoading[s.id]}
                                    onClick={async () => {
                                      setGradeLoading((prev) => ({ ...prev, [s.id]: true }));
                                      setSubmissionError('');
                                      try {
                                        const scoreValue = gradeScore[s.id];
                                        const feedbackValue = gradeFeedback[s.id];
                                        const payload = {};
                                        if (scoreValue !== undefined) {
                                          payload.score = scoreValue === '' ? null : Number(scoreValue);
                                        }
                                        if (feedbackValue !== undefined) payload.feedback = feedbackValue;
                                        const response = await api.patch(`/submissions/${s.id}/grade`, payload);
                                        setSubmissions((prev) => prev.map((x) => (x.id === s.id ? response.data : x)));
                                      } catch (err) {
                                        setSubmissionError(err?.response?.data?.detail || 'Failed to save grade');
                                      } finally {
                                        setGradeLoading((prev) => ({ ...prev, [s.id]: false }));
                                      }
                                    }}
                                    type="button"
                                  >
                                    <span className="material-symbols-outlined text-lg">save</span>
                                    {gradeLoading[s.id] ? 'Saving...' : 'Save Grade'}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>

                <footer className="mt-12 pt-8 border-t border-[#eae6f4] dark:border-[#2a2438] flex flex-col md:flex-row items-center justify-between text-[#5d479e] dark:text-[#a094c7] text-xs uppercase tracking-widest font-bold">
                  <p>© TASK SCHEDULING AGENT</p>
                  <div className="flex gap-6 mt-4 md:mt-0">
                    <button className="hover:text-primary transition-colors">Privacy Policy</button>
                    <button className="hover:text-primary transition-colors">Terms of Service</button>
                    <button className="hover:text-primary transition-colors">Support</button>
                  </div>
                </footer>
              </>
            )}
          </main>
        </>
      ) : (
        <div className="relative flex h-screen w-full flex-col overflow-y-auto overflow-x-hidden">
          <div className="layout-container flex h-full grow flex-col">
            <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-[#eae6f4] dark:border-white/10 bg-white dark:bg-background-dark px-6 md:px-10 py-3 sticky top-0 z-50">
              <div className="flex items-center gap-4 text-primary">
                <div className="size-6">
                  <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M8.57829 8.57829C5.52816 11.6284 3.451 15.5145 2.60947 19.7452C1.76794 23.9758 2.19984 28.361 3.85056 32.3462C5.50128 36.3314 8.29667 39.7376 11.8832 42.134C15.4698 44.5305 19.6865 45.8096 24 45.8096C28.3135 45.8096 32.5302 44.5305 36.1168 42.134C39.7033 39.7375 42.4987 36.3314 44.1494 32.3462C45.8002 28.361 46.2321 23.9758 45.3905 19.7452C44.549 15.5145 42.4718 11.6284 39.4217 8.57829L24 24L8.57829 8.57829Z"
                      fill="currentColor"
                    ></path>
                  </svg>
                </div>
                <h2 className="text-[#110d1c] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
                  Task Scheduling Agent
                </h2>
              </div>
              <div className="flex flex-1 justify-end gap-8">
                <nav className="hidden md:flex items-center gap-9">
                  <button
                    className="text-[#110d1c] dark:text-gray-300 text-sm font-medium leading-normal hover:text-primary transition-colors"
                    onClick={() => navigate('/student/dashboard')}
                  >
                    Dashboard
                  </button>
                  <button className="text-primary text-sm font-semibold leading-normal underline underline-offset-4">
                    Courses
                  </button>
                  <button className="text-[#110d1c] dark:text-gray-300 text-sm font-medium leading-normal hover:text-primary transition-colors">
                    Calendar
                  </button>
                </nav>
                <div className="size-10 rounded-full bg-cover bg-center border border-gray-200 dark:border-white/10 bg-gradient-to-br from-primary/20 to-primary/5"></div>
              </div>
            </header>

            <main className="flex flex-1 justify-center py-8">
              <div className="layout-content-container flex flex-col w-full max-w-[960px] px-6">
                <nav className="flex flex-wrap gap-2 py-2 mb-2">
                  <button
                    className="text-primary text-base font-medium leading-normal hover:underline"
                    onClick={() =>
                      task?.subject_id ? navigate(`/subject/${task.subject_id}`) : navigate('/student/dashboard')
                    }
                  >
                    Courses
                  </button>
                  <span className="text-gray-400 text-base font-medium leading-normal">/</span>
                  <span className="text-[#110d1c] dark:text-gray-300 text-base font-medium leading-normal">
                    {task?.subject_id ? 'Subject' : 'Course'}
                  </span>
                </nav>

                {(error || submissionError) && (
                  <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                    {error || submissionError}
                  </div>
                )}

                {isLoading ? (
                  <div className="text-slate-600 dark:text-slate-400">Loading...</div>
                ) : !task ? (
                  <div className="text-slate-600 dark:text-slate-400">Task not found.</div>
                ) : (
                  <>
                    <div className="flex flex-wrap justify-between items-end gap-3 py-4">
                      <div className="flex flex-col gap-2">
                        <h1 className="text-[#110d1c] dark:text-white text-4xl font-black leading-tight tracking-[-0.033em]">
                          {task.title}
                        </h1>
                        <div className="flex items-center gap-2 text-[#5d479e] dark:text-primary/70">
                          <span className="material-symbols-outlined text-sm">event</span>
                          <p className="text-base font-normal leading-normal">
                            {formatDueLong(task.deadline) ? `Due ${formatDueLong(task.deadline)}` : 'No deadline'}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 py-6">
                      <div className="flex flex-col gap-2 rounded-xl p-6 border border-[#d5cee9] dark:border-white/10 bg-white dark:bg-background-dark shadow-sm">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <span className="material-symbols-outlined text-lg">info</span>
                          <p className="text-sm font-medium uppercase tracking-wider">Status</p>
                        </div>
                        <p className="text-[#110d1c] dark:text-white tracking-light text-2xl font-bold leading-tight">
                          {submissionLoading
                            ? 'Loading'
                            : mySubmission
                            ? mySubmission.score !== null && mySubmission.score !== undefined
                              ? 'Graded'
                              : 'Submitted'
                            : task.deadline && new Date(task.deadline).getTime() < Date.now()
                            ? 'Missing'
                            : 'Not submitted'}
                        </p>
                      </div>
                      <div className="flex flex-col gap-2 rounded-xl p-6 border border-[#d5cee9] dark:border-white/10 bg-white dark:bg-background-dark shadow-sm">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <span className="material-symbols-outlined text-lg">grade</span>
                          <p className="text-sm font-medium uppercase tracking-wider">Score</p>
                        </div>
                        <p className="text-[#110d1c] dark:text-white tracking-light text-2xl font-bold leading-tight">
                          {mySubmission?.score ?? '—'}
                        </p>
                      </div>
                      <div className="flex flex-col gap-2 rounded-xl p-6 border border-[#d5cee9] dark:border-white/10 bg-white dark:bg-background-dark shadow-sm">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <span className="material-symbols-outlined text-lg">chat_bubble</span>
                          <p className="text-sm font-medium uppercase tracking-wider">Feedback</p>
                        </div>
                        <p className="text-[#110d1c] dark:text-white tracking-light text-2xl font-bold leading-tight">
                          {mySubmission?.feedback ?? '—'}
                        </p>
                      </div>
                    </div>

                    {task.type === 'group' ? (
                      <div className="bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 rounded-xl overflow-hidden mb-8 shadow-sm">
                        <div className="px-6 py-5 border-b border-[#d5cee9] dark:border-white/10 bg-gray-50/50 dark:bg-white/5 flex items-center justify-between gap-4">
                          <h2 className="text-[#110d1c] dark:text-white text-xl font-bold leading-tight tracking-tight">
                            Your Group
                          </h2>
                          <button
                            className="px-4 py-2 rounded-lg border border-[#d5cee9] dark:border-white/10 hover:border-primary/40 transition-colors text-sm font-bold"
                            onClick={loadGroups}
                            disabled={groupsLoading}
                            type="button"
                          >
                            Refresh
                          </button>
                        </div>
                        <div className="p-6">
                          {groupsError ? (
                            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                              {groupsError}
                            </div>
                          ) : null}
                          {groupsLoading ? (
                            <div className="text-gray-600 dark:text-gray-300">Loading group...</div>
                          ) : myGroup ? (
                            <div className="flex flex-col gap-3">
                              {myGroup.assigned_problem_statement ? (
                                <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                  <span className="font-semibold">Assigned Problem:</span> {myGroup.assigned_problem_statement}
                                </div>
                              ) : null}
                              <div className="flex flex-wrap gap-2">
                                {(myGroup.member_uids || []).map((uid) => (
                                  <span
                                    key={uid}
                                    className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#f0eff5] dark:bg-[#251e3b] text-[#3d2a78] dark:text-[#c0bad3]"
                                  >
                                    {uid}
                                  </span>
                                ))}
                              </div>
                              {mySubmission?.group_id ? (
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  Last updated {mySubmission.updated_at ? new Date(mySubmission.updated_at).toLocaleString() : '—'} by{' '}
                                  {mySubmission.student_uid || '—'}
                                </div>
                              ) : null}
                            </div>
                          ) : (
                            <div className="text-gray-600 dark:text-gray-300">Groups not available yet.</div>
                          )}
                        </div>
                      </div>
                    ) : null}

                    <div className="bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 rounded-xl overflow-hidden mb-8 shadow-sm">
                      <div className="px-6 py-5 border-b border-[#d5cee9] dark:border-white/10 bg-gray-50/50 dark:bg-white/5">
                        <h2 className="text-[#110d1c] dark:text-white text-xl font-bold leading-tight tracking-tight">
                          Task Description
                        </h2>
                      </div>
                      <div className="p-6">
                        <div className="max-w-none text-gray-700 dark:text-gray-300 space-y-4 whitespace-pre-wrap">
                          {task.description || 'No description.'}
                        </div>
                      </div>
                    </div>

                    <div className="bg-white dark:bg-background-dark border border-[#d5cee9] dark:border-white/10 rounded-xl overflow-hidden mb-8 shadow-sm">
                      <div className="px-6 py-5 border-b border-[#d5cee9] dark:border-white/10 bg-gray-50/50 dark:bg-white/5 flex items-center justify-between gap-4">
                        <h2 className="text-[#110d1c] dark:text-white text-xl font-bold leading-tight tracking-tight">
                          Your Submission
                        </h2>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-semibold px-2 py-1 bg-primary/10 text-primary rounded">
                            {mySubmission ? 'Submitted' : 'Draft'}
                          </span>
                          <button
                            className="px-4 py-2 rounded-lg border border-[#d5cee9] dark:border-white/10 hover:border-primary/40 transition-colors text-sm font-bold"
                            onClick={loadSubmissions}
                            disabled={submissionLoading}
                            type="button"
                          >
                            Refresh
                          </button>
                        </div>
                      </div>
                      <div className="p-6">
                        <div className="flex flex-col gap-4">
                          <textarea
                            className="w-full min-h-[300px] p-4 text-base bg-white dark:bg-white/5 border border-[#d5cee9] dark:border-white/10 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all placeholder:text-gray-400"
                            placeholder="Type your answer here or paste your solutions..."
                            value={submissionContent}
                            onChange={(e) => setSubmissionContent(e.target.value)}
                            disabled={isSubmitting}
                          ></textarea>
                          {attachmentsError ? (
                            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                              {attachmentsError}
                            </div>
                          ) : null}

                          <div
                            className={`border-2 border-dashed rounded-xl p-5 transition-colors ${
                              isDragActive
                                ? 'border-primary bg-primary/[0.04]'
                                : 'border-[#d5cee9] dark:border-white/10 bg-white/50 dark:bg-white/5'
                            }`}
                            onDragEnter={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setIsDragActive(true);
                            }}
                            onDragOver={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setIsDragActive(true);
                            }}
                            onDragLeave={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setIsDragActive(false);
                            }}
                            onDrop={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setIsDragActive(false);
                              uploadFiles(e.dataTransfer.files);
                            }}
                          >
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                              <div>
                                <div className="flex items-center gap-2 text-primary font-bold">
                                  <span className="material-symbols-outlined">attach_file</span>
                                  Attachments
                                </div>
                                <div className="text-xs text-gray-500 mt-1">Drag & drop or browse. PDF, JPG, PNG, ZIP (Max 25MB)</div>
                              </div>
                              <div className="flex items-center gap-3">
                                <input
                                  ref={fileInputRef}
                                  type="file"
                                  multiple
                                  className="hidden"
                                  accept=".pdf,.jpg,.jpeg,.png,.zip,application/pdf,image/jpeg,image/png,application/zip"
                                  onChange={(e) => uploadFiles(e.target.files)}
                                  disabled={attachmentsUploading}
                                />
                                <button
                                  className="px-5 py-2 rounded-lg bg-primary text-white text-sm font-bold hover:bg-primary/90 transition-all disabled:opacity-60"
                                  onClick={() => fileInputRef.current?.click()}
                                  disabled={attachmentsUploading}
                                  type="button"
                                >
                                  {attachmentsUploading ? 'Uploading...' : 'Browse Files'}
                                </button>
                              </div>
                            </div>

                            {Array.isArray(mySubmission?.attachments) && mySubmission.attachments.length > 0 ? (
                              <div className="mt-4 flex flex-wrap gap-2">
                                {mySubmission.attachments.map((a) => (
                                  <div
                                    key={a.id}
                                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#d5cee9] dark:border-white/10 bg-white dark:bg-white/5 text-xs font-bold"
                                  >
                                    <button
                                      className="flex items-center gap-2 hover:text-primary transition-colors"
                                      onClick={() => downloadAttachment(mySubmission.id, a)}
                                      type="button"
                                    >
                                      <span className="material-symbols-outlined text-base">description</span>
                                      <span className="max-w-[220px] truncate">{a.filename}</span>
                                    </button>
                                    <button
                                      className="text-gray-400 hover:text-red-500 transition-colors"
                                      onClick={() => deleteAttachment(a.id)}
                                      type="button"
                                      disabled={attachmentsUploading}
                                    >
                                      <span className="material-symbols-outlined text-base">close</span>
                                    </button>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="mt-4 text-xs text-gray-500">No attachments yet.</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-4 mb-12">
                      <button
                        className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-primary/20 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                        onClick={submitOrUpdate}
                        disabled={
                          !submissionContent.trim() ||
                          isSubmitting ||
                          submissionLoading ||
                          (task?.type === 'group' && !myGroup?.id)
                        }
                        type="button"
                      >
                        <span className="material-symbols-outlined">send</span>
                        {isSubmitting ? 'Submitting...' : mySubmission ? 'Resubmit Assignment' : 'Submit Assignment'}
                      </button>
                      <p className="text-center text-sm text-gray-500">
                        By clicking submit, you agree to the academic integrity policy. You can resubmit until the deadline.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </main>

            <footer className="border-t border-[#eae6f4] dark:border-white/10 py-8 text-center text-gray-400 text-sm">
              <p>© Task Scheduling Agent Academic Portal</p>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskView;
