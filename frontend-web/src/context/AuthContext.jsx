import { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../config/firebase';
import api from '../services/api';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch user data from backend
  const fetchUserData = async (user) => {
    try {
      const token = await user.getIdToken();
      const response = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data) {
        setUserRole(response.data.role);
        return response.data;
      }
    } catch (error) {
      const status = error?.response?.status;

      if (status === 404) {
        const role = sessionStorage.getItem('pendingRole');
        if (!role) {
          setUserRole(null);
          setError('User not found in database. Please register.');
          return;
        }

        try {
          const idToken = await user.getIdToken();
          const name =
            user.displayName ||
            sessionStorage.getItem('pendingName') ||
            (user.email ? user.email.split('@')[0] : 'User');

          await api.post('/auth/login', {
            idToken,
            uid: user.uid,
            email: user.email,
            name,
            role,
          });

          sessionStorage.removeItem('pendingRole');
          sessionStorage.removeItem('pendingName');

          const token = await user.getIdToken();
          const retryResponse = await api.get('/auth/me', {
            headers: { Authorization: `Bearer ${token}` }
          });

          if (retryResponse.data) {
            setUserRole(retryResponse.data.role);
            return retryResponse.data;
          }
        } catch (bootstrapError) {
          console.error('Error bootstrapping user data:', bootstrapError);
        }
      }

      console.error('Error fetching user data:', error);
      setError('Failed to fetch user data');
    }
  };

  useEffect(() => {
    // Listen to auth state changes
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setLoading(true);
      setError(null);
      try {
        if (user) {
          setCurrentUser(user);
          // Fetch additional user data from backend
          await fetchUserData(user);
        } else {
          setCurrentUser(null);
          setUserRole(null);
        }
      } catch (error) {
        console.error('Auth state change error:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    });

    // Cleanup subscription
    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    userRole,
    loading,
    error,
    isAuthenticated: !!currentUser,
    isTeacher: userRole === 'teacher',
    isStudent: userRole === 'student',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
