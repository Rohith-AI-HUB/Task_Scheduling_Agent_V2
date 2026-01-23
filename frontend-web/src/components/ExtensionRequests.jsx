import { useEffect, useState } from 'react';
import aiService from '../services/aiService';

const ExtensionRequests = () => {
  const [extensions, setExtensions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [processing, setProcessing] = useState({});
  const [status, setStatus] = useState('pending');

  const loadExtensions = async () => {
    setIsLoading(true);
    try {
      const data = await aiService.getExtensionRequests(status || undefined);
      setExtensions(data.items || []);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load extension requests');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadExtensions();
  }, [status]);

  const handleApprove = async (ext) => {
    setProcessing({ [ext.id]: true });
    try {
      await aiService.approveExtension(ext.id, {});
      await loadExtensions();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to approve');
    } finally {
      setProcessing({});
    }
  };

  const handleDeny = async (ext) => {
    setProcessing({ [ext.id]: true });
    try {
      await aiService.denyExtension(ext.id, {});
      await loadExtensions();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to deny');
    } finally {
      setProcessing({});
    }
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString();
  };

  const getRecommendationColor = (rec) => {
    if (rec === 'approve') return 'text-green-600 dark:text-green-400';
    if (rec === 'deny') return 'text-red-600 dark:text-red-400';
    return 'text-orange-600 dark:text-orange-400';
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-[#eae6f4] dark:border-slate-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-[#eae6f4] dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="size-10 flex items-center justify-center bg-primary/10 dark:bg-primary/20 rounded-lg">
            <span className="material-symbols-outlined text-primary text-[20px]">schedule</span>
          </div>
          <div>
            <h2 className="text-[#110d1c] dark:text-white text-base font-bold">Extension Requests</h2>
            <p className="text-[#5d479e] dark:text-slate-400 text-xs capitalize">{status} requests</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-[#eae6f4] dark:border-slate-800 overflow-hidden">
            {['pending', 'approved', 'denied'].map((s) => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`px-3 py-1.5 text-xs font-bold capitalize ${status === s ? 'bg-primary text-white' : 'bg-white dark:bg-slate-900 text-[#110d1c] dark:text-white'} transition-colors`}
                disabled={isLoading}
              >
                {s}
              </button>
            ))}
          </div>
          <button onClick={loadExtensions} disabled={isLoading} className="size-8 flex items-center justify-center rounded-lg hover:bg-background-light dark:hover:bg-slate-800">
            <span className="material-symbols-outlined text-[18px]">refresh</span>
          </button>
        </div>
      </div>

      <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
        <style>{`.custom-scrollbar::-webkit-scrollbar{width:6px}.custom-scrollbar::-webkit-scrollbar-track{background:transparent}.custom-scrollbar::-webkit-scrollbar-thumb{background:#d5cee9;border-radius:10px}`}</style>

        {error && (
          <div className="mx-4 my-3 p-3 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50 rounded-lg text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="p-4 text-center text-[#5d479e] dark:text-slate-400 text-sm">Loading...</div>
        ) : extensions.length === 0 ? (
          <div className="p-6 text-center">
            <span className="material-symbols-outlined text-[#5d479e] dark:text-slate-500 text-[40px] mb-2">done_all</span>
            <p className="text-[#110d1c] dark:text-white font-semibold">No {status} requests</p>
            <p className="text-[#5d479e] dark:text-slate-400 text-sm mt-1">Try a different filter</p>
          </div>
        ) : (
          extensions.map((ext) => (
            <div key={ext.id} className="border-b border-[#eae6f4] dark:border-slate-800 last:border-0 p-4 hover:bg-background-light/50 dark:hover:bg-slate-800/50 transition-colors">
              <div className="flex justify-between items-start gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-[#110d1c] dark:text-white font-semibold text-sm truncate">{ext.task_title}</h3>
                  <p className="text-[#5d479e] dark:text-slate-400 text-xs">{ext.student_name || ext.student_uid}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300">
                    {ext.extension_days}d
                  </span>
                  <span
                    className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      ext.status === 'approved'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                        : ext.status === 'denied'
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                        : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                    }`}
                  >
                    {ext.status}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#5d479e] dark:text-slate-400 mb-2">
                <span>{formatDate(ext.current_deadline)} → {formatDate(ext.requested_deadline)}</span>
              </div>

              <p className="text-xs text-[#110d1c] dark:text-slate-300 mb-3 line-clamp-2">{ext.reason}</p>

              {ext.ai_analysis && (
                <div className="mb-3 p-2 bg-primary/5 dark:bg-primary/10 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="material-symbols-outlined text-[14px] text-primary">psychology</span>
                    <span className={`text-xs font-bold uppercase ${getRecommendationColor(ext.ai_analysis.recommendation)}`}>
                      AI: {ext.ai_analysis.recommendation}
                    </span>
                    <span className="text-xs text-[#5d479e] dark:text-slate-400">
                      Workload: {Math.round(ext.ai_analysis.workload_score * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-[#5d479e] dark:text-slate-400 line-clamp-2">{ext.ai_analysis.reasoning}</p>
                </div>
              )}

              {ext.status === 'pending' ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(ext)}
                    disabled={processing[ext.id]}
                    className="flex-1 px-3 py-2 bg-green-600 text-white rounded-lg text-xs font-bold hover:bg-green-700 transition-colors disabled:opacity-60 flex items-center justify-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    Approve
                  </button>
                  <button
                    onClick={() => handleDeny(ext)}
                    disabled={processing[ext.id]}
                    className="flex-1 px-3 py-2 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 transition-colors disabled:opacity-60 flex items-center justify-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">cancel</span>
                    Deny
                  </button>
                </div>
              ) : (
                <div className="text-xs text-[#5d479e] dark:text-slate-400">
                  {ext.teacher_response ? <span>Teacher: {ext.teacher_response}</span> : <span>No teacher note</span>}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ExtensionRequests;
