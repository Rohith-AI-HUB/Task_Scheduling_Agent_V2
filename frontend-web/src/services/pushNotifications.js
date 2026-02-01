import { getApp } from 'firebase/app';
import { getToken, isSupported, onMessage, getMessaging } from 'firebase/messaging';
import pushService from './pushService';
import { firebaseConfig } from '../config/firebase';

let _foregroundHandlerAttached = false;

const _postFirebaseConfigToServiceWorker = async (registration) => {
  try {
    if (!registration?.active) return;
    registration.active.postMessage({ type: 'INIT_FIREBASE', firebaseConfig });
  } catch {}
};

const _ensureServiceWorkerRegistration = async () => {
  if (!('serviceWorker' in navigator)) return null;
  const existing = await navigator.serviceWorker.getRegistration('/');
  if (existing) return existing;
  return await navigator.serviceWorker.register('/sw.js', { scope: '/' });
};

export const enablePushNotifications = async () => {
  const supported = await isSupported().catch(() => false);
  if (!supported) return { enabled: false, reason: 'unsupported' };

  const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY;
  if (!vapidKey) return { enabled: false, reason: 'missing_vapid_key' };

  if (!('Notification' in window)) return { enabled: false, reason: 'no_notification_api' };

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return { enabled: false, reason: 'permission_denied' };

  const registration = await _ensureServiceWorkerRegistration();
  if (!registration) return { enabled: false, reason: 'no_service_worker' };

  await navigator.serviceWorker.ready.catch(() => {});
  await _postFirebaseConfigToServiceWorker(registration);

  const app = getApp();
  const messaging = getMessaging(app);

  const token = await getToken(messaging, {
    vapidKey,
    serviceWorkerRegistration: registration,
  });

  if (!token) return { enabled: false, reason: 'no_token' };

  await pushService.registerToken(token);

  if (!_foregroundHandlerAttached) {
    _foregroundHandlerAttached = true;
    onMessage(messaging, (payload) => {
      try {
        const title = payload?.notification?.title || 'Notification';
        const body = payload?.notification?.body || '';
        const url = payload?.data?.url || '/';
        const n = new Notification(title, { body, icon: '/icon-192x192.png', data: { url } });
        n.onclick = () => {
          try {
            window.focus();
            window.location.assign(url);
          } catch {}
        };
      } catch {}
    });
  }

  return { enabled: true };
};

