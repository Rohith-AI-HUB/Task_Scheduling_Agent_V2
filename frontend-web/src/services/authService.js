import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  sendPasswordResetEmail,
  updateProfile
} from 'firebase/auth';
import { auth, googleProvider } from '../config/firebase';
import api from './api';

/**
 * Register a new user with email and password
 * @param {string} email - User's email
 * @param {string} password - User's password
 * @param {string} fullName - User's full name
 * @param {string} role - User's role (student or teacher)
 * @returns {Promise} Firebase user credential
 */
export const registerWithEmail = async (email, password, fullName, role = 'student') => {
  try {
    // Create user in Firebase
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);

    // Update user profile with name
    await updateProfile(userCredential.user, {
      displayName: fullName
    });

    // Get Firebase ID token
    const idToken = await userCredential.user.getIdToken();

    // Register user in backend
    await api.post('/auth/register', {
      uid: userCredential.user.uid,
      email: userCredential.user.email,
      name: fullName,
      role: role,
      idToken
    });

    return userCredential;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
};

/**
 * Sign in with email and password
 * @param {string} email - User's email
 * @param {string} password - User's password
 * @returns {Promise} Firebase user credential
 */
export const loginWithEmail = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);

    // Get Firebase ID token
    const idToken = await userCredential.user.getIdToken();

    // Verify token with backend
    await api.post('/auth/login', { idToken });

    return userCredential;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

/**
 * Sign in with Google
 * @returns {Promise} Firebase user credential
 */
export const loginWithGoogle = async () => {
  try {
    const userCredential = await signInWithPopup(auth, googleProvider);

    // Get Firebase ID token
    const idToken = await userCredential.user.getIdToken();

    // Register/login user in backend
    await api.post('/auth/login', {
      uid: userCredential.user.uid,
      email: userCredential.user.email,
      name: userCredential.user.displayName,
      idToken
    });

    return userCredential;
  } catch (error) {
    console.error('Google sign-in error:', error);
    throw error;
  }
};

/**
 * Sign out current user
 * @returns {Promise}
 */
export const logout = async () => {
  try {
    await signOut(auth);
    // Clear any stored tokens
    localStorage.removeItem('authToken');
  } catch (error) {
    console.error('Logout error:', error);
    throw error;
  }
};

/**
 * Send password reset email
 * @param {string} email - User's email
 * @returns {Promise}
 */
export const resetPassword = async (email) => {
  try {
    await sendPasswordResetEmail(auth, email);
  } catch (error) {
    console.error('Password reset error:', error);
    throw error;
  }
};

/**
 * Get current user's ID token
 * @returns {Promise<string>} ID token
 */
export const getIdToken = async () => {
  const user = auth.currentUser;
  if (user) {
    return await user.getIdToken();
  }
  return null;
};

/**
 * Get error message from Firebase error code
 * @param {string} errorCode - Firebase error code
 * @returns {string} User-friendly error message
 */
export const getAuthErrorMessage = (errorCode) => {
  const errorMessages = {
    'auth/email-already-in-use': 'This email is already registered',
    'auth/invalid-email': 'Invalid email address',
    'auth/operation-not-allowed': 'Operation not allowed',
    'auth/weak-password': 'Password is too weak. Use at least 6 characters',
    'auth/user-disabled': 'This account has been disabled',
    'auth/user-not-found': 'No account found with this email',
    'auth/wrong-password': 'Incorrect password',
    'auth/invalid-credential': 'Invalid email or password',
    'auth/too-many-requests': 'Too many attempts. Please try again later',
    'auth/network-request-failed': 'Network error. Please check your connection',
    'auth/popup-closed-by-user': 'Sign-in popup was closed',
  };

  return errorMessages[errorCode] || 'An error occurred. Please try again';
};
