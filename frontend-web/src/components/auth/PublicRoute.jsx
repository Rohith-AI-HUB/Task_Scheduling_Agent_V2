import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { auth } from '../../config/firebase';

const PublicRoute = ({ children }) => {
  const { currentUser, userRole, loading, needsRegistration } = useAuth();
  const signedInUser = currentUser || auth.currentUser;
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="mt-4 text-slate-600 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (signedInUser) {
    // If user needs to complete registration, redirect to register page (but allow if already there)
    if (needsRegistration) {
      if (location.pathname === '/register') {
        return children;
      }
      return <Navigate to="/register" state={{ message: 'Please select your role to complete registration.' }} replace />;
    }

    if (!userRole) {
      // Still loading user role, show spinner
      return (
        <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-slate-600 dark:text-slate-400">Loading...</p>
          </div>
        </div>
      );
    }

    if (userRole === 'teacher') {
      return <Navigate to="/teacher/dashboard" replace />;
    } else if (userRole === 'student') {
      return <Navigate to="/student/dashboard" replace />;
    }
  }

  return children;
};

export default PublicRoute;
