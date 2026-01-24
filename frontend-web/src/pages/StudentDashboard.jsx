import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import aiService from '../services/aiService';
import { logout } from '../services/authService';
import AISchedule from '../components/AISchedule';
import DueSoon from '../components/DueSoon';
import ChatAssistant from '../components/ChatAssistant';

const StudentDashboard = () => {
  const { currentUser, backendUser } = useAuth();
  const navigate = useNavigate();

  const resolvePhotoUrl = (photoUrl) => {
    if (!photoUrl) return '';
    const u = String(photoUrl);
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    const root = String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');
    return `${root}${u}`;
  };

  const [subjects, setSubjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [joinCode, setJoinCode] = useState('');
  const [isJoining, setIsJoining] = useState(false);

  const [extensions, setExtensions] = useState([]);
  const [extLoading, setExtLoading] = useState(true);

  const enrolledCount = useMemo(() => subjects.length, [subjects]);

  const loadSubjects = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/subjects');
      setSubjects(response.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExtensions = async () => {
    setExtLoading(true);
    try {
      const data = await aiService.getExtensionRequests();
      setExtensions(data?.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setExtLoading(false);
    }
  };

  useEffect(() => {
    loadSubjects();
    loadExtensions();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleJoin = async () => {
    const value = joinCode.trim().toUpperCase();
    if (!value) return;
    setIsJoining(true);
    try {
      const response = await api.post('/subjects/join', { join_code: value });
      setSubjects((prev) => {
        const exists = prev.some((s) => s.id === response.data.id);
        return exists ? prev : [response.data, ...prev];
      });
      setJoinCode('');
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to join classroom');
    } finally {
      setIsJoining(false);
    }
  };

  const formatDateTime = (value) => {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString();
  };

  return (
    <div className="min-h-screen bg-surface text-slate-900 font-sans antialiased">
      <nav className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <div className="bg-primary p-1.5 rounded-lg text-white">
              <span className="material-symbols-outlined block">bolt</span>
            </div>
            <span className="font-bold text-lg tracking-tight">Task Scheduling Agent</span>
          </div>
          <div className="hidden lg:flex items-center gap-4 text-sm font-medium text-slate-600">
            <button className="text-primary" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} type="button">
              Dashboard
            </button>
            <button className="hover:text-primary" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} type="button">
              Classrooms
            </button>
            <button className="hover:text-primary" onClick={() => navigate('/calendar')} type="button">
              Schedule
            </button>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
            onClick={() => navigate('/calendar')}
            title="Calendar"
            type="button"
          >
            <span className="material-symbols-outlined">calendar_month</span>
          </button>
          <button className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100" title="Notifications" type="button">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button
            className="w-9 h-9 rounded-full bg-slate-200 overflow-hidden border-2 border-white shadow-sm"
            onClick={() => navigate('/profile')}
            title="Profile settings"
            type="button"
          >
            {backendUser?.photo_url ? (
              <img alt="User avatar" className="w-full h-full object-cover" src={resolvePhotoUrl(backendUser.photo_url)} />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-700 font-bold">
                {(currentUser?.displayName || 'S').slice(0, 1).toUpperCase()}
              </div>
            )}
          </button>
          <button
            onClick={handleLogout}
            className="w-10 h-10 flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
            title="Logout"
            type="button"
          >
            <span className="material-symbols-outlined">logout</span>
          </button>
        </div>
      </nav>

      <main className="max-w-[1440px] mx-auto p-6">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 bento-card p-8 bg-gradient-to-br from-white to-soft-purple/30 flex flex-col justify-between relative overflow-hidden">
            <div className="relative z-10">
              <span className="text-primary font-semibold text-sm bg-primary/10 px-3 py-1 rounded-full uppercase tracking-wider">
                Student Portal
              </span>
              <h1 className="text-4xl font-bold text-slate-900 mt-4">
                Welcome back,
                <br />
                {currentUser?.displayName?.split(' ')?.[0] || 'Student'}
              </h1>
              <p className="text-slate-500 mt-2 max-w-md">
                You are enrolled in {enrolledCount} classroom{enrolledCount === 1 ? '' : 's'}.
              </p>
            </div>
            <div className="flex flex-wrap gap-4 mt-6 relative z-10">
              <button
                onClick={() => navigate('/calendar')}
                className="bg-primary text-white px-6 py-3 rounded-xl font-semibold flex items-center gap-2 hover:bg-accent-purple transition-all shadow-lg shadow-primary/20"
                type="button"
              >
                <span className="material-symbols-outlined">calendar_month</span>
                View Schedule
              </button>
              <button
                onClick={loadSubjects}
                className="bg-white text-slate-700 border border-slate-200 px-6 py-3 rounded-xl font-semibold hover:bg-slate-50 transition-all flex items-center gap-2"
                type="button"
              >
                <span className="material-symbols-outlined">sync</span>
                Refresh Classes
              </button>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-8 bento-card p-6 flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">school</span>
                Your Classrooms
              </h3>
              <button className="text-primary text-sm font-bold hover:underline" onClick={loadSubjects} type="button">
                Refresh
              </button>
            </div>

            {isLoading ? (
              <div className="text-sm text-slate-500">Loading classrooms...</div>
            ) : subjects.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                No classrooms yet. Join one below.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {subjects.map((sub) => (
                  <button
                    key={sub.id}
                    className="border border-slate-100 bg-slate-50 rounded-xl p-5 text-left hover:border-primary/30 hover:bg-white transition-colors"
                    onClick={() => navigate(`/subject/${sub.id}`)}
                    type="button"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                        {sub.code || 'CLASS'}
                      </span>
                      <span className="text-[10px] font-bold bg-green-100 text-green-700 px-2 py-1 rounded-full uppercase tracking-wider">
                        Active
                      </span>
                    </div>
                    <div className="font-bold text-slate-800 line-clamp-1">{sub.name}</div>
                    <div className="text-xs text-slate-500 mt-1">Join code: <span className="font-mono">{sub.join_code}</span></div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="col-span-12 lg:col-span-4">
            <AISchedule />
          </div>

          <div className="col-span-12 lg:col-span-8 bento-card p-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">vpn_key</span>
                  Join Classroom
                </h3>
                <p className="text-xs text-slate-500 mt-1">Enter your classroom code to enroll.</p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                className="flex-1 px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="e.g. AB12XY"
                type="text"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
              />
              <button
                className="px-5 py-2 rounded-lg bg-primary text-white font-bold text-sm hover:bg-primary/90 transition-colors disabled:opacity-60"
                onClick={handleJoin}
                disabled={!joinCode || isJoining}
                type="button"
              >
                {isJoining ? '...' : 'Join'}
              </button>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4">
            <DueSoon />
          </div>

          <div className="col-span-12 lg:col-span-8 bento-card flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-500">history_edu</span>
                Extensions
              </h3>
              <button className="text-primary text-sm font-bold hover:underline" onClick={loadExtensions} type="button">
                Refresh
              </button>
            </div>
            <div className="p-4 space-y-3">
              {extLoading ? (
                <div className="text-sm text-slate-500">Loading...</div>
              ) : extensions.length === 0 ? (
                <div className="text-center text-slate-500 text-sm py-6">No extension requests.</div>
              ) : (
                extensions.slice(0, 6).map((ext) => (
                  <div key={ext.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="font-bold text-sm text-slate-800 truncate">{ext.task_title || 'Task'}</div>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          ext.status === 'approved'
                            ? 'bg-green-100 text-green-700'
                            : ext.status === 'denied'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-orange-100 text-orange-700'
                        }`}>
                          {String(ext.status || 'pending').toUpperCase()}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        Requested: {formatDateTime(ext.requested_deadline)}
                      </div>
                      <div className="text-xs text-slate-500">
                        Current: {formatDateTime(ext.current_deadline)}
                      </div>
                    </div>
                    <span className="material-symbols-outlined text-slate-300">chevron_right</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4">
            <ChatAssistant height="100%" className="h-full" />
          </div>
        </div>
      </main>
    </div>
  );
};

export default StudentDashboard;
