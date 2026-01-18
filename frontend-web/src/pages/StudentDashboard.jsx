import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { logout } from '../services/authService';
import AISchedule from '../components/AISchedule';
import DueSoon from '../components/DueSoon';
import UpcomingTasks from '../components/UpcomingTasks';

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
  const [loadError, setLoadError] = useState('');

  const [joinCode, setJoinCode] = useState('');
  const [joinError, setJoinError] = useState('');
  const [isJoining, setIsJoining] = useState(false);

  const enrolledCount = useMemo(() => subjects.length, [subjects]);

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

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleJoin = async () => {
    const value = joinCode.trim().toUpperCase();
    if (!value) return;
    setIsJoining(true);
    setJoinError('');
    try {
      const response = await api.post('/subjects/join', { join_code: value });
      setSubjects((prev) => {
        const exists = prev.some((s) => s.id === response.data.id);
        return exists ? prev : [response.data, ...prev];
      });
      setJoinCode('');
    } catch (err) {
      setJoinError(err?.response?.data?.detail || 'Failed to join classroom');
    } finally {
      setIsJoining(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen text-[#110d1c] dark:text-white font-display">
      <header className="sticky top-0 z-50 w-full border-b border-[#d5cee9] bg-background-light/80 backdrop-blur-md dark:border-white/10 dark:bg-background-dark/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <span className="material-symbols-outlined">schedule</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight dark:text-white">Task Scheduling Agent</h1>
          </div>
          <div className="flex items-center gap-4">
            <button className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-white/50 border border-[#d5cee9] text-[#110d1c] hover:bg-white dark:bg-white/5 dark:border-white/10 dark:text-white">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-red-500"></span>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-[#d5cee9] dark:border-white/10">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold dark:text-white">{currentUser?.displayName || currentUser?.email}</p>
                <p className="text-xs text-[#5d479e] dark:text-gray-400">ID: {currentUser?.uid?.slice(0, 6)}</p>
              </div>
              <button
                className="h-10 w-10 rounded-full overflow-hidden bg-gradient-to-br from-primary/30 to-primary/10 border-2 border-primary"
                onClick={() => navigate('/profile')}
                type="button"
              >
                {backendUser?.photo_url ? (
                  <img
                    alt="Profile"
                    className="h-full w-full object-cover"
                    src={resolvePhotoUrl(backendUser.photo_url)}
                  />
                ) : null}
              </button>
              <button
                onClick={handleLogout}
                className="hidden md:inline-flex h-10 items-center rounded-lg bg-primary px-4 font-bold text-white hover:opacity-90 transition-opacity"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <nav className="mb-6 flex items-center gap-2 text-sm font-medium text-[#5d479e] dark:text-gray-400">
          <span className="hover:text-primary cursor-pointer transition-colors" onClick={() => navigate('/student/dashboard')}>
            Home
          </span>
          <span className="material-symbols-outlined text-xs">chevron_right</span>
          <span className="text-[#110d1c] dark:text-white">Student Dashboard</span>
        </nav>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8 flex flex-col gap-8">
            <div className="flex flex-col gap-2">
              <h2 className="text-3xl font-bold tracking-tight dark:text-white">
                Welcome back{currentUser?.displayName ? `, ${currentUser.displayName.split(' ')[0]}!` : '!'}
              </h2>
              <p className="text-[#5d479e] dark:text-gray-400 text-lg leading-relaxed">
                You are enrolled in {enrolledCount} classroom{enrolledCount === 1 ? '' : 's'}.
              </p>
            </div>

            <div className="rounded-xl border border-[#d5cee9] bg-white p-6 shadow-sm dark:bg-white/5 dark:border-white/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-[#110d1c] dark:text-white">Join Classroom</h3>
                  <p className="text-[#5d479e] dark:text-gray-400">
                    Enter your classroom code to enroll in a new subject.
                  </p>
                </div>
                <div className="flex flex-1 items-center gap-3 max-w-md">
                  <div className="relative flex-1">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#5d479e] dark:text-gray-400">
                      key
                    </span>
                    <input
                      className="h-12 w-full rounded-lg border border-[#d5cee9] bg-background-light pl-10 pr-4 text-[#110d1c] focus:border-primary focus:ring-1 focus:ring-primary dark:bg-background-dark dark:border-white/10 dark:text-white placeholder:text-[#5d479e]/50"
                      placeholder="e.g. AB12XY"
                      type="text"
                      value={joinCode}
                      onChange={(e) => {
                        setJoinCode(e.target.value.toUpperCase());
                        setJoinError('');
                      }}
                      disabled={isJoining}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleJoin();
                      }}
                    />
                  </div>
                  <button
                    className="h-12 rounded-lg bg-primary px-8 font-bold text-white transition-all hover:opacity-90 active:scale-95 shadow-lg shadow-primary/20 disabled:opacity-60"
                    onClick={handleJoin}
                    disabled={!joinCode.trim() || isJoining}
                  >
                    {isJoining ? 'Joining' : 'Join'}
                  </button>
                </div>
              </div>
              {(joinError || loadError) && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {joinError || loadError}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-[#110d1c] dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">school</span>
                  Enrolled Classrooms
                </h3>
                <button className="text-sm font-semibold text-primary hover:underline" onClick={loadSubjects} disabled={isLoading}>
                  Refresh
                </button>
              </div>

              {isLoading ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {Array.from({ length: 4 }).map((_, idx) => (
                    <div
                      key={idx}
                      className="flex flex-col rounded-xl border border-[#d5cee9] bg-white p-5 dark:bg-white/5 dark:border-white/10"
                    >
                      <div className="h-12 w-12 rounded-lg bg-primary/10"></div>
                      <div className="mt-4 h-5 w-3/4 rounded bg-[#eae6f4] dark:bg-white/10"></div>
                      <div className="mt-2 h-4 w-1/2 rounded bg-[#eae6f4] dark:bg-white/10"></div>
                      <div className="mt-6 h-9 w-full rounded bg-[#eae6f4] dark:bg-white/10"></div>
                    </div>
                  ))}
                </div>
              ) : subjects.length === 0 ? (
                <div className="rounded-xl border border-[#d5cee9] bg-white p-10 text-center dark:bg-white/5 dark:border-white/10">
                  <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-3xl">school</span>
                  </div>
                  <p className="font-bold text-[#110d1c] dark:text-white">No classrooms yet</p>
                  <p className="text-xs text-[#5d479e] dark:text-gray-400 mt-2">
                    Ask your teacher for the join code, then enter it above.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {subjects.map((subject) => (
                    <div
                      key={subject.id}
                      className="group relative flex flex-col rounded-xl border border-[#d5cee9] bg-white p-5 transition-all hover:shadow-md dark:bg-white/5 dark:border-white/10"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                          <span className="material-symbols-outlined">school</span>
                        </div>
                        <span className="rounded-full bg-green-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-green-700 dark:bg-green-500/20 dark:text-green-400">
                          Active
                        </span>
                      </div>
                      <h4 className="text-lg font-bold dark:text-white">{subject.name}</h4>
                      <p className="text-sm text-[#5d479e] dark:text-gray-400">
                        Code: {subject.code || 'N/A'}
                      </p>
                      <div className="mt-4 flex items-center gap-2 py-3 border-t border-[#d5cee9]/50 dark:border-white/5">
                        <div className="h-6 w-6 rounded-full bg-primary/20"></div>
                        <p className="text-xs font-medium text-[#5d479e] dark:text-gray-400">
                          Teacher: {subject.teacher_uid?.slice(0, 10)}
                        </p>
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-[#5d479e] bg-background-light dark:bg-white/10 px-2 py-1 rounded">
                          JOIN: {subject.join_code}
                        </span>
                        <button
                          className="flex items-center gap-1 text-sm font-bold text-primary group-hover:translate-x-1 transition-transform"
                          onClick={() => navigate(`/subject/${subject.id}`)}
                        >
                          Open <span className="material-symbols-outlined text-sm">arrow_forward</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <aside className="lg:col-span-4 flex flex-col gap-6">
            <AISchedule />
            <DueSoon />
            <UpcomingTasks />
          </aside>
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-6 py-10 border-t border-[#d5cee9] dark:border-white/10 mt-12">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-[#5d479e] dark:text-gray-400">
          <p>© Task Scheduling Agent. Built for Student Success.</p>
        </div>
      </footer>
    </div>
  );
};

export default StudentDashboard;
