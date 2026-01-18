import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const apiRoot = () => String(api?.defaults?.baseURL || '').replace(/\/api\/?$/, '');

const resolvePhotoUrl = (photoUrl) => {
  if (!photoUrl) return '';
  const u = String(photoUrl);
  if (u.startsWith('http://') || u.startsWith('https://')) return u;
  return `${apiRoot()}${u}`;
};

const Profile = () => {
  const navigate = useNavigate();
  const { backendUser, refreshBackendUser, userRole } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [saveLoading, setSaveLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [removeLoading, setRemoveLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  const currentPhoto = useMemo(() => resolvePhotoUrl(backendUser?.photo_url), [backendUser?.photo_url]);
  const previewPhoto = useMemo(() => {
    if (!selectedFile) return '';
    return URL.createObjectURL(selectedFile);
  }, [selectedFile]);

  useEffect(() => {
    refreshBackendUser?.().catch(() => {});
  }, []);

  useEffect(() => {
    setName(backendUser?.name || '');
    setEmail(backendUser?.email || '');
  }, [backendUser?.name, backendUser?.email]);

  useEffect(() => {
    return () => {
      if (previewPhoto) URL.revokeObjectURL(previewPhoto);
    };
  }, [previewPhoto]);

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

  const saveProfile = async () => {
    setSaveLoading(true);
    setError('');
    setSuccess('');
    try {
      const payload = { name: name || null, email: email || null };
      await api.patch('/auth/me', payload);
      await refreshBackendUser?.();
      setSuccess('Profile updated');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to update profile'));
    } finally {
      setSaveLoading(false);
    }
  };

  const uploadPhoto = async () => {
    if (!selectedFile) return;
    setUploadLoading(true);
    setUploadProgress(0);
    setError('');
    setSuccess('');
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      await api.post('/auth/me/photo', form, {
        onUploadProgress: (evt) => {
          const total = Number(evt.total || 0);
          const loaded = Number(evt.loaded || 0);
          if (!total) return;
          const next = Math.max(0, Math.min(100, Math.round((loaded / total) * 100)));
          setUploadProgress(next);
        },
      });
      setSelectedFile(null);
      await refreshBackendUser?.();
      setSuccess('Photo updated');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to upload photo'));
    } finally {
      setUploadLoading(false);
      setUploadProgress(0);
    }
  };

  const removePhoto = async () => {
    setRemoveLoading(true);
    setError('');
    setSuccess('');
    try {
      await api.delete('/auth/me/photo');
      setSelectedFile(null);
      await refreshBackendUser?.();
      setSuccess('Photo removed');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to remove photo'));
    } finally {
      setRemoveLoading(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen text-[#110d1c] dark:text-white font-display">
      <header className="sticky top-0 z-50 w-full border-b border-[#d5cee9] bg-background-light/80 backdrop-blur-md dark:border-white/10 dark:bg-background-dark/80">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <span className="material-symbols-outlined">person</span>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Profile</h1>
              <div className="text-xs text-[#5d479e] dark:text-gray-400">{userRole || backendUser?.role || ''}</div>
            </div>
          </div>
          <button
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
            onClick={() => navigate(-1)}
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
            Back
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {error ? (
          <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="mb-6 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-700 dark:text-emerald-300 text-sm">
            {success}
          </div>
        ) : null}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <div className="rounded-xl border border-[#d5cee9] bg-white p-6 shadow-sm dark:bg-white/5 dark:border-white/10">
              <div className="flex flex-col items-center gap-4">
                <div className="h-24 w-24 rounded-full overflow-hidden border-2 border-primary/30 bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center">
                  {previewPhoto || currentPhoto ? (
                    <img
                      src={previewPhoto || currentPhoto}
                      alt="Profile"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="material-symbols-outlined text-4xl text-primary">person</span>
                  )}
                </div>

                <div className="w-full space-y-3">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="w-full text-sm"
                    onChange={(e) => {
                      const f = e.target.files?.[0] || null;
                      if (!f) {
                        setSelectedFile(null);
                        return;
                      }

                      const allowed = new Set(['image/jpeg', 'image/png', 'image/webp']);
                      if (!allowed.has(f.type)) {
                        setError('Please select a JPG, PNG, or WEBP image.');
                        setSelectedFile(null);
                        e.target.value = '';
                        return;
                      }

                      const maxBytes = 10 * 1024 * 1024;
                      if (f.size > maxBytes) {
                        setError('Image is too large. Max size is 10MB.');
                        setSelectedFile(null);
                        e.target.value = '';
                        return;
                      }

                      setError('');
                      setSuccess('');
                      setSelectedFile(f);
                    }}
                    disabled={uploadLoading || removeLoading}
                  />
                  <button
                    className="w-full h-10 rounded-lg bg-primary text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-60"
                    onClick={uploadPhoto}
                    disabled={!selectedFile || uploadLoading || removeLoading}
                    type="button"
                  >
                    {uploadLoading ? 'Uploading...' : 'Upload Photo'}
                  </button>
                  {uploadLoading ? (
                    <div className="w-full">
                      <div className="h-2 w-full rounded-full bg-[#eae6f4] dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-primary transition-[width]"
                          style={{ width: `${uploadProgress || 0}%` }}
                        ></div>
                      </div>
                      <div className="mt-1 text-xs text-[#5d479e] dark:text-gray-400 font-semibold">
                        {uploadProgress ? `${uploadProgress}%` : 'Starting...'}
                      </div>
                    </div>
                  ) : null}
                  <button
                    className="w-full h-10 rounded-lg border border-[#d5cee9] dark:border-white/10 font-bold hover:border-rose-400 transition-colors disabled:opacity-60"
                    onClick={removePhoto}
                    disabled={(!backendUser?.photo_url && !selectedFile) || uploadLoading || removeLoading}
                    type="button"
                  >
                    {removeLoading ? 'Removing...' : 'Remove Photo'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="md:col-span-2">
            <div className="rounded-xl border border-[#d5cee9] bg-white p-6 shadow-sm dark:bg-white/5 dark:border-white/10 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Name</label>
                <input
                  className="h-12 w-full rounded-lg border border-[#d5cee9] bg-background-light px-4 text-[#110d1c] focus:border-primary focus:ring-1 focus:ring-primary dark:bg-background-dark dark:border-white/10 dark:text-white"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={saveLoading}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Email</label>
                <input
                  className="h-12 w-full rounded-lg border border-[#d5cee9] bg-background-light px-4 text-[#110d1c] focus:border-primary focus:ring-1 focus:ring-primary dark:bg-background-dark dark:border-white/10 dark:text-white"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={saveLoading}
                />
                <div className="mt-2 text-xs text-[#5d479e] dark:text-gray-400">
                  If you use Firebase Auth, changing email here does not change Firebase email.
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  className="h-12 px-6 rounded-lg border border-[#d5cee9] dark:border-white/10 font-bold hover:border-primary/40 transition-colors disabled:opacity-60"
                  onClick={() => {
                    setName(backendUser?.name || '');
                    setEmail(backendUser?.email || '');
                    setError('');
                    setSuccess('');
                  }}
                  disabled={saveLoading}
                  type="button"
                >
                  Reset
                </button>
                <button
                  className="h-12 px-8 rounded-lg bg-primary text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-60"
                  onClick={saveProfile}
                  disabled={!name.trim() || saveLoading}
                  type="button"
                >
                  {saveLoading ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Profile;
