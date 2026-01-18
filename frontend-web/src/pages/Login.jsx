import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginWithEmail, loginWithGoogle, getAuthErrorMessage } from '../services/authService';
import api from '../services/api';

const Login = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const userCredential = await loginWithEmail(formData.email, formData.password);

      const idToken = await userCredential.user.getIdToken();
      const response = await api.post('/auth/login', { idToken });

      // Navigate based on role
      if (response.data.role === 'teacher') {
        navigate('/teacher/dashboard');
      } else {
        navigate('/student/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err?.response?.data?.detail || getAuthErrorMessage(err.code));
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    setError('');

    try {
      const userCredential = await loginWithGoogle();

      const idToken = await userCredential.user.getIdToken();
      const response = await api.post('/auth/login', {
        idToken,
        uid: userCredential.user.uid,
        email: userCredential.user.email,
        name: userCredential.user.displayName
      });

      // Navigate based on role
      if (response.data.role === 'teacher') {
        navigate('/teacher/dashboard');
      } else {
        navigate('/student/dashboard');
      }
    } catch (err) {
      console.error('Google sign-in error:', err);
      const errorDetail = err?.response?.data?.detail || '';

      // If role is required, redirect to register page to select role
      if (err?.response?.status === 400 && errorDetail.includes('Role is required')) {
        navigate('/register', {
          state: { message: 'Please select your role to complete registration.' }
        });
        return;
      }

      setError(errorDetail || getAuthErrorMessage(err.code));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col font-display">
      {/* Top Navigation Bar */}
      <header className="w-full flex items-center justify-between border-b border-solid border-[#eee6f4] dark:border-[#2d1b3d] px-10 py-4 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3 text-primary">
          <div className="size-8">
            <svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <g clipPath="url(#clip0_6_319)">
                <path d="M8.57829 8.57829C5.52816 11.6284 3.451 15.5145 2.60947 19.7452C1.76794 23.9758 2.19984 28.361 3.85056 32.3462C5.50128 36.3314 8.29667 39.7376 11.8832 42.134C15.4698 44.5305 19.6865 45.8096 24 45.8096C28.3135 45.8096 32.5302 44.5305 36.1168 42.134C39.7033 39.7375 42.4987 36.3314 44.1494 32.3462C45.8002 28.361 46.2321 23.9758 45.3905 19.7452C44.549 15.5145 42.4718 11.6284 39.4217 8.57829L24 24L8.57829 8.57829Z" fill="currentColor"></path>
              </g>
              <defs>
                <clipPath id="clip0_6_319"><rect fill="white" height="48" width="48"></rect></clipPath>
              </defs>
            </svg>
          </div>
          <h2 className="text-[#150d1c] dark:text-white text-lg font-bold leading-tight tracking-tight">Task Scheduling Agent</h2>
        </div>
      </header>

      {/* Main Content Area with Geometric Pattern Background */}
      <main className="flex-grow flex items-center justify-center py-12 px-6 bg-pattern">
        <div className="w-full max-w-md">
          {/* Branding Header */}
          <div className="text-center mb-8">
            <h1 className="text-[#150d1c] dark:text-white tracking-tight text-[32px] font-bold leading-tight mb-2">Sign in to your account</h1>
            <p className="text-[#79479e] dark:text-[#a686bd] text-sm font-normal leading-normal">Intelligent planning, simplified.</p>
          </div>

          {/* Login Card */}
          <div className="bg-white dark:bg-[#251833] rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)] border border-[#eee6f4] dark:border-[#3a264a] overflow-hidden">
            <div className="p-8">
              {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form className="space-y-5" onSubmit={handleSubmit}>
                {/* Email Input */}
                <div>
                  <label className="block text-[#150d1c] dark:text-gray-200 text-sm font-medium mb-1.5 ml-1">Email Address</label>
                  <input
                    className="w-full rounded-lg text-[#150d1c] dark:text-white border border-[#ddcee9] dark:border-[#3a264a] bg-white dark:bg-[#1a0f23] focus:ring-2 focus:ring-primary/20 focus:border-primary h-12 px-4 text-base font-normal placeholder:text-[#79479e]/50 outline-none transition-all"
                    placeholder="name@company.com"
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    disabled={isLoading}
                  />
                </div>

                {/* Password Input */}
                <div>
                  <div className="flex items-center justify-between mb-1.5 ml-1">
                    <label className="block text-[#150d1c] dark:text-gray-200 text-sm font-medium">Password</label>
                    <a className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors" href="#">Forgot password?</a>
                  </div>
                  <div className="relative">
                    <input
                      className="w-full rounded-lg text-[#150d1c] dark:text-white border border-[#ddcee9] dark:border-[#3a264a] bg-white dark:bg-[#1a0f23] focus:ring-2 focus:ring-primary/20 focus:border-primary h-12 px-4 pr-12 text-base font-normal placeholder:text-[#79479e]/50 outline-none transition-all"
                      placeholder="••••••••"
                      type={showPassword ? "text" : "password"}
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                      disabled={isLoading}
                    />
                    <button
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#79479e] hover:text-primary p-1 flex items-center justify-center"
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      <span className="material-symbols-outlined text-[22px]">
                        {showPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Sign In Button */}
                <button
                  className="w-full bg-primary hover:bg-primary/90 text-white font-semibold h-12 rounded-lg shadow-lg shadow-primary/20 transition-all flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
                  type="submit"
                  disabled={isLoading}
                >
                  <span>{isLoading ? 'Signing in...' : 'Sign in'}</span>
                  {!isLoading && (
                    <span className="material-symbols-outlined text-sm group-hover:translate-x-0.5 transition-transform">arrow_forward</span>
                  )}
                </button>
              </form>

              {/* Divider */}
              <div className="relative my-8">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-[#eee6f4] dark:border-[#3a264a]"></span>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white dark:bg-[#251833] px-4 text-[#79479e] font-medium tracking-wider">Or continue with</span>
                </div>
              </div>

              {/* Social Login */}
              <button
                className="w-full border border-[#ddcee9] dark:border-[#3a264a] bg-white dark:bg-[#1a0f23] text-[#150d1c] dark:text-white font-medium h-12 rounded-lg hover:bg-gray-50 dark:hover:bg-[#2a1b38] transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleGoogleSignIn}
                disabled={isLoading}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
                </svg>
                Sign in with Google
              </button>
            </div>

            {/* Footer */}
            <div className="bg-gray-50 dark:bg-[#2a1b38] px-8 py-4 border-t border-[#eee6f4] dark:border-[#3a264a] text-center">
              <p className="text-sm text-[#79479e] dark:text-gray-400">
                Don't have an account?
                <button
                  className="text-primary font-bold hover:underline ml-1"
                  onClick={() => navigate('/register')}
                >
                  Register
                </button>
              </p>
            </div>
          </div>

          {/* Additional Footer Links */}
        </div>
      </main>

      {/* Background Pattern Decorative Element */}
      <div className="fixed top-0 right-0 p-12 opacity-10 pointer-events-none">
        <div className="w-64 h-64 border-[40px] border-primary rounded-full"></div>
      </div>
      <div className="fixed bottom-0 left-0 p-12 opacity-10 pointer-events-none">
        <div className="w-48 h-48 bg-primary rounded-xl rotate-12"></div>
      </div>
    </div>
  );
};

export default Login;
