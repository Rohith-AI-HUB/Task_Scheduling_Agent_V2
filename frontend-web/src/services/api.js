import axios from 'axios';
import { auth } from '../config/firebase';

const coerceErrorMessage = (value) => {
  if (!value) return null;
  if (typeof value === 'string') return value;

  if (Array.isArray(value)) {
    const msgs = value
      .map((item) => (typeof item?.msg === 'string' ? item.msg : null))
      .filter(Boolean);
    if (msgs.length > 0) return msgs.join('; ');
    try {
      return JSON.stringify(value[0] ?? value);
    } catch {
      return 'Unknown error';
    }
  }

  if (typeof value === 'object') {
    if (typeof value.msg === 'string') return value.msg;
    try {
      return JSON.stringify(value);
    } catch {
      return 'Unknown error';
    }
  }

  return null;
};

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const apiRoot = () => String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');

const baseOrigin = () => {
  const root = apiRoot();
  if (root) return root;
  if (typeof window !== 'undefined' && window.location?.origin) return window.location.origin;
  return '';
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let readinessPromise = null;

const ensureBackendReady = async () => {
  if (readinessPromise) return readinessPromise;
  readinessPromise = (async () => {
    const origin = baseOrigin();
    if (!origin) return;
    const url = `${origin.replace(/\/$/, '')}/ready`;
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      try {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 4000);
        const response = await fetch(url, { cache: 'no-store', signal: controller.signal });
        window.clearTimeout(timeoutId);
        if (response.ok) {
          const data = await response.json().catch(() => null);
          if (!data || data.ready !== false) return;
        }
      } catch {
      }
      await wait(1500);
    }
  })();
  return readinessPromise;
};

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    try {
      await ensureBackendReady();
      if (config.data instanceof FormData) {
        if (config.headers && config.headers['Content-Type']) {
          delete config.headers['Content-Type'];
        }
        if (config.headers && config.headers['content-type']) {
          delete config.headers['content-type'];
        }
      }
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      const message =
        coerceErrorMessage(data?.detail) ||
        coerceErrorMessage(data?.message) ||
        coerceErrorMessage(data?.error) ||
        (typeof data === 'string' ? data : null) ||
        'Unknown error';
      error.userMessage = message;

      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          console.error('Unauthorized access:', message);
          // You might want to redirect to login page here
          break;
        case 403:
          console.error('Forbidden access:', message);
          break;
        case 404:
          console.error('Resource not found:', message);
          break;
        case 500:
          console.error('Server error:', message);
          break;
        default:
          console.error('API error:', message);
      }
    } else if (error.request) {
      // Request made but no response
      if (error.code === 'ECONNABORTED' || String(error.message || '').toLowerCase().includes('timeout')) {
        const message = 'Request timed out. Quiz generation can take a bit longer—please try again.';
        error.userMessage = message;
        console.error('Request timeout:', message);
      } else {
        const message = 'Network error - no response from server';
        error.userMessage = message;
        console.error(message);
      }
    } else {
      // Something else happened
      const message = error.message || 'Unknown error';
      error.userMessage = message;
      console.error('Error:', message);
    }
    return Promise.reject(error);
  }
);

export default api;
