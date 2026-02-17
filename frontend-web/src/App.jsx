import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import PublicRoute from './components/auth/PublicRoute';
import api from './services/api';
import Login from './pages/Login';
import Register from './pages/Register';
import TeacherDashboard from './pages/TeacherDashboard';
import StudentDashboard from './pages/StudentDashboard';
import TeacherClassrooms from './pages/TeacherClassrooms';
import SubjectView from './pages/SubjectView';
import TaskView from './pages/TaskView';
import QuizAttempt from './pages/QuizAttempt';
import Profile from './pages/Profile';
import Calendar from './pages/Calendar';
import TeacherStudentMarks from './pages/TeacherStudentMarks';

const apiRoot = () => String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');

const baseOrigin = () => {
  const root = apiRoot();
  if (root) return root;
  if (typeof window !== 'undefined' && window.location?.origin) return window.location.origin;
  return '';
};

function App() {
  useEffect(() => {
    const origin = baseOrigin();
    if (!origin) return;
    const url = `${origin.replace(/\/$/, '')}/live`;
    fetch(url).catch(() => {});
  }, []);

  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes - redirect to dashboard if authenticated */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <Register />
              </PublicRoute>
            }
          />

          {/* Protected routes - require authentication */}
          <Route
            path="/teacher/dashboard"
            element={
              <ProtectedRoute requireRole="teacher">
                <TeacherDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/teacher/classrooms"
            element={
              <ProtectedRoute requireRole="teacher">
                <TeacherClassrooms />
              </ProtectedRoute>
            }
          />
          <Route
            path="/teacher/subject/:subjectId/student/:studentUid/marks"
            element={
              <ProtectedRoute requireRole="teacher">
                <TeacherStudentMarks />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/dashboard"
            element={
              <ProtectedRoute requireRole="student">
                <StudentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/subject/:id"
            element={
              <ProtectedRoute>
                <SubjectView />
              </ProtectedRoute>
            }
          />
          <Route
            path="/task/:id"
            element={
              <ProtectedRoute>
                <TaskView />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quiz/:taskId"
            element={
              <ProtectedRoute requireRole="student">
                <QuizAttempt />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/calendar"
            element={
              <ProtectedRoute>
                <Calendar />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
