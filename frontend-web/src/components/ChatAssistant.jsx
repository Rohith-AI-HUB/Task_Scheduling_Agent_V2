import { useEffect, useRef, useState } from 'react';
import aiService from '../services/aiService';

const ChatAssistant = ({ height = 600, className = '' } = {}) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [credits, setCredits] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const typingRef = useRef({ timer: null, messageId: null, fullText: '' });

  const createLocalId = () => {
    const id =
      globalThis?.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return id;
  };

  const stopTyping = ({ commit = true } = {}) => {
    const current = typingRef.current;
    if (current.timer) {
      clearInterval(current.timer);
    }
    if (commit && current.messageId) {
      const fullText = current.fullText || '';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === current.messageId
            ? { ...m, content: fullText, isTyping: false }
            : m
        )
      );
    }
    typingRef.current = { timer: null, messageId: null, fullText: '' };
  };

  const startTyping = (messageId, fullText) => {
    stopTyping({ commit: true });
    const text = String(fullText || '');
    typingRef.current = { timer: null, messageId, fullText: text };

    if (!text) {
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, content: '', isTyping: false } : m))
      );
      return;
    }

    let idx = 0;
    const step = () => {
      idx = Math.min(text.length, idx + 2);
      const partial = text.slice(0, idx);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, content: partial, isTyping: idx < text.length } : m
        )
      );
      if (idx >= text.length) stopTyping({ commit: false });
    };

    step();
    typingRef.current.timer = setInterval(step, 18);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getErrorMessage = (err) => {
    const detail = err?.response?.data?.detail;
    if (detail && typeof detail === 'object') {
      if (typeof detail.error === 'string') return detail.error;
      if (typeof detail.message === 'string') return detail.message;
    }
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first?.msg === 'string') return first.msg;
      return JSON.stringify(first);
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return err?.message || 'An error occurred';
  };

  const loadCredits = async () => {
    try {
      const data = await aiService.getCredits();
      setCredits(data);
    } catch (err) {
      console.error('Failed to load credits:', err);
    }
  };

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      const data = await aiService.getChatHistory();
      const history = Array.isArray(data.messages) ? data.messages : [];
      setMessages(
        history.map((m) => ({
          id: createLocalId(),
          ...m,
          isTyping: false,
        }))
      );
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCredits();
    loadHistory();
    return () => stopTyping({ commit: false });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!inputMessage.trim() || isSending) return;

    // Check credits
    if (credits && credits.credits_remaining <= 0) {
      setError('Daily message limit reached. Resets at midnight UTC.');
      return;
    }

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);
    setError('');

    // Add user message to UI immediately
    const userMsg = {
      id: createLocalId(),
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await aiService.sendChatMessage(userMessage);

      // Add assistant response
      const assistantMessageId = createLocalId();
      const assistantMsg = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: response.timestamp,
        intent: response.intent,
        context_used: response.context_used,
        isTyping: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      startTyping(assistantMessageId, response.response);

      // Reload credits after successful message
      await loadCredits();
    } catch (err) {
      const errMsg = getErrorMessage(err);
      const errorCode = err?.response?.data?.detail?.error_code;

      if (errorCode === 'NO_CREDITS') {
        setError(errMsg);
        await loadCredits(); // Refresh credits display
      } else if (errorCode === 'RATE_LIMIT_EXCEEDED' || errorCode === 'RATE_LIMIT') {
        setError('Rate limit exceeded. Please wait a moment.');
      } else if (err?.response?.status === 429) {
        setError(errMsg);
      } else {
        setError(errMsg);
      }

      // Remove the user message if sending failed
      stopTyping({ commit: false });
      setMessages((prev) => prev.filter((msg) => msg !== userMsg));
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear the chat history?')) {
      return;
    }

    try {
      await aiService.clearChatHistory();
      stopTyping({ commit: false });
      setMessages([]);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    let ts = timestamp;
    if (typeof ts === 'string') {
      const hasTimezone = /([zZ]|[+-]\d{2}:\d{2})$/.test(ts);
      if (!hasTimezone) ts = `${ts}Z`;
    }
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const creditsRemaining = credits?.credits_remaining ?? null;
  const creditsLimit = credits?.credits_limit ?? 25;
  const creditsPercentage =
    creditsRemaining === null ? 100 : (creditsRemaining / creditsLimit) * 100;
  const isLowCredits = creditsRemaining !== null && creditsRemaining <= 5 && creditsRemaining > 0;
  const isOutOfCredits = creditsRemaining !== null && creditsRemaining <= 0;
  const creditsDisplay =
    creditsRemaining === null ? `--/${creditsLimit}` : `${creditsRemaining}/${creditsLimit}`;

  return (
    <div
      className={`w-full bg-white rounded-xl shadow-sm border border-[#eae6f4] flex flex-col overflow-hidden transition-all ${className}`}
      style={{ height }}
    >
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-primary/5 to-primary/10 border-b border-[#eae6f4] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="size-10 flex items-center justify-center bg-primary rounded-lg shadow-sm">
            <span className="material-symbols-outlined text-white text-[20px]">smart_toy</span>
          </div>
          <div className="flex flex-col">
            <h2 className="text-[#110d1c] text-base font-bold leading-tight">
              AI Assistant
            </h2>
            <p className="text-[#5d479e] text-xs">
              Task + general help
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="size-8 flex items-center justify-center rounded-lg hover:bg-white/50 text-[#5d479e]"
            onClick={handleClearHistory}
            disabled={messages.length === 0}
            type="button"
            title="Clear history"
          >
            <span className="material-symbols-outlined text-[18px]">delete</span>
          </button>
        </div>
      </div>

      {/* Credits Display */}
      <div className="px-4 py-3 border-b border-[#eae6f4]">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#5d479e]">Messages Today</span>
          <span
            className={`text-xs font-bold ${
              isOutOfCredits
                ? 'text-red-600'
                : isLowCredits
                ? 'text-orange-600'
                : 'text-primary'
            }`}
          >
            {creditsDisplay}
          </span>
        </div>
        <div className="w-full bg-[#eae6f4] h-2 rounded-full overflow-hidden mt-2">
          <div
            className={`h-full transition-all ${
              isOutOfCredits
                ? 'bg-red-500'
                : isLowCredits
                ? 'bg-orange-500'
                : 'bg-primary'
            }`}
            style={{ width: `${creditsPercentage}%` }}
          ></div>
        </div>
        {isLowCredits && (
          <p className="text-xs text-orange-600 mt-2 flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">warning</span>
            Low credits remaining
          </p>
        )}
        {isOutOfCredits && (
          <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">error</span>
            Daily limit reached. Resets at midnight UTC.
          </p>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        <style>{`.custom-scrollbar::-webkit-scrollbar{width:6px}.custom-scrollbar::-webkit-scrollbar-track{background:transparent}.custom-scrollbar::-webkit-scrollbar-thumb{background:#d5cee9;border-radius:10px}.typing-dots{display:inline-flex;gap:4px;align-items:center}.typing-dots span{width:6px;height:6px;border-radius:9999px;background:#5d479e;opacity:.35;animation:typingDot 1.1s infinite}.typing-dots span:nth-child(2){animation-delay:.15s}.typing-dots span:nth-child(3){animation-delay:.3s}@keyframes typingDot{0%,100%{transform:translateY(0);opacity:.35}50%{transform:translateY(-3px);opacity:.9}}`}</style>

        {isLoading ? (
          <div className="flex items-center justify-center h-full text-[#5d479e] text-sm">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined animate-spin">sync</span>
              Loading chat...
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="size-16 flex items-center justify-center bg-primary/10 rounded-full mb-3">
              <span className="material-symbols-outlined text-primary text-[32px]">
                chat_bubble
              </span>
            </div>
            <p className="text-[#110d1c] font-semibold mb-1">
              Start a conversation
            </p>
            <p className="text-[#5d479e] text-sm max-w-xs">
              Ask about tasks, deadlines, submissions, scheduling, or general questions.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="size-8 shrink-0 flex items-center justify-center bg-primary/10 rounded-lg">
                  <span className="material-symbols-outlined text-primary text-[16px]">
                    smart_toy
                  </span>
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  msg.role === 'user'
                    ? 'bg-primary text-white'
                    : 'bg-[#f1eff7] text-[#110d1c]'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap break-words">
                  {msg.role === 'assistant' && msg.isTyping && !msg.content ? (
                    <span className="typing-dots">
                      <span />
                      <span />
                      <span />
                    </span>
                  ) : (
                    msg.content
                  )}
                </p>
                <p
                  className={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/70' : 'text-[#5d479e]'}`}
                >
                  {formatTimestamp(msg.timestamp)}
                  {msg.intent && (
                    <span className="ml-2 opacity-60">• {msg.intent.replace('_', ' ')}</span>
                  )}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="size-8 shrink-0 flex items-center justify-center bg-primary rounded-lg">
                  <span className="material-symbols-outlined text-white text-[16px]">
                    person
                  </span>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="mx-4 mb-3 p-3 bg-red-50 border border-red-100 rounded-lg text-red-600 text-sm flex items-start gap-2">
          <span className="material-symbols-outlined text-[16px] mt-0.5">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Input Area */}
      <form
        onSubmit={handleSendMessage}
        className="p-4 border-t border-[#eae6f4] bg-background-light/50"
      >
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={
              isOutOfCredits
                ? 'Daily limit reached'
                : 'Ask about tasks, deadlines, or anything else...'
            }
            disabled={isSending || isOutOfCredits}
            maxLength={500}
            className="flex-1 px-4 py-2 rounded-lg border border-[#eae6f4] bg-white text-[#110d1c] placeholder-[#5d479e] text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-60 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isSending || !inputMessage.trim() || isOutOfCredits}
            className="px-4 py-2 bg-primary text-white rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSending ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">
                  sync
                </span>
                Sending
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">send</span>
                Send
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-[#5d479e] mt-2">
          {inputMessage.length}/500 characters
        </p>
      </form>
    </div>
  );
};

export default ChatAssistant;
