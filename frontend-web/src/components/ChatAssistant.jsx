import { useEffect, useRef, useState } from 'react';
import aiService from '../services/aiService';

const ChatAssistant = ({ height = 'auto', className = '' } = {}) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [credits, setCredits] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const typingIntervalRef = useRef(null);

  const loadCredits = async () => {
    try {
      const data = await aiService.getCredits();
      setCredits(data);
    } catch (err) {
      console.error('Failed to load credits:', err);
    }
  };

  useEffect(() => {
    loadCredits();
    // Ideally load history too, keeping it simple for now as per mockup focus
  }, []);

  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;
      }
    };
  }, []);

  const typewriter = (text, messageId) => {
    const safeText = `${text ?? ''}`;
    if (!safeText) return Promise.resolve();

    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }

    const chunkSize = safeText.length > 600 ? 4 : safeText.length > 300 ? 2 : 1;
    const delayMs = safeText.length > 600 ? 12 : 18;

    let index = 0;
    setIsTyping(true);

    return new Promise((resolve) => {
      typingIntervalRef.current = setInterval(() => {
        index = Math.min(safeText.length, index + chunkSize);
        const nextText = safeText.slice(0, index);

        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, content: nextText } : m))
        );

        if (index >= safeText.length) {
          clearInterval(typingIntervalRef.current);
          typingIntervalRef.current = null;
          setIsTyping(false);
          resolve();
        }
      }, delayMs);
    });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending || isTyping) return;

    const userMsg = { id: Date.now(), role: 'user', content: inputMessage.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsSending(true);

    try {
      const response = await aiService.sendChatMessage(userMsg.content);
      const aiMsg = { 
          id: Date.now() + 1, 
          role: 'assistant', 
          content: '',
          timestamp: response.timestamp 
      };
      setMessages(prev => [...prev, aiMsg]);
      await typewriter(response.response, aiMsg.id);
      await loadCredits();
    } catch (err) {
      console.error(err);
      // specific error handling if needed
    } finally {
      setIsSending(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const creditsRemaining = credits?.credits_remaining ?? 25;
  const creditsLimit = credits?.credits_limit ?? 25;
  const creditsPercentage = (creditsRemaining / creditsLimit) * 100;
  const isBusy = isSending || isTyping;

  return (
    <div className={`w-full bento-card flex flex-col overflow-hidden bg-white ${className}`} style={{ height }}>
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="size-10 flex items-center justify-center bg-primary rounded-xl shadow-sm">
            <span className="material-symbols-outlined text-white text-[20px]">smart_toy</span>
          </div>
          <div className="min-w-0">
            <div className="font-bold text-slate-800 truncate">AI Assistant</div>
            <div className="text-xs text-slate-500 truncate">Task + general help</div>
          </div>
        </div>
        <button
          className="size-9 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500"
          onClick={() => setMessages([])}
          title="Clear history"
          type="button"
        >
          <span className="material-symbols-outlined text-[18px]">delete</span>
        </button>
      </div>

      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">Messages Today</span>
          <span className="text-xs font-bold text-primary">
            {creditsRemaining}/{creditsLimit}
          </span>
        </div>
        <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden mt-2">
          <div className="h-full bg-primary transition-all" style={{ width: `${Math.min(100, Math.max(0, creditsPercentage))}%` }}></div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4 hide-scrollbar bg-slate-50/50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-10">
            <div className="size-16 flex items-center justify-center bg-primary/10 rounded-full mb-3">
              <span className="material-symbols-outlined text-primary text-[32px]">chat_bubble</span>
            </div>
            <p className="text-slate-800 font-semibold mb-1">Start a conversation</p>
            <p className="text-slate-500 text-sm max-w-xs">
              Ask about tasks, deadlines, submissions, scheduling, or general questions.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role !== 'user' ? (
                <div className="size-8 shrink-0 flex items-center justify-center bg-primary/10 rounded-full">
                  <span className="material-symbols-outlined text-primary text-[16px]">smart_toy</span>
                </div>
              ) : null}
              <div
                className={`max-w-[78%] px-4 py-2 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-2xl rounded-br-md shadow-sm'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-2xl rounded-bl-md shadow-sm'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
              </div>
              {msg.role === 'user' ? (
                <div className="size-8 shrink-0 flex items-center justify-center bg-primary rounded-full shadow-sm">
                  <span className="material-symbols-outlined text-white text-[16px]">person</span>
                </div>
              ) : null}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="flex-1 px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
            placeholder="Ask about tasks, deadlines, or anything else..."
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={isBusy}
            maxLength={500}
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isBusy}
            className="px-4 py-2 bg-primary text-white rounded-lg font-bold text-sm hover:bg-primary/90 transition-colors disabled:opacity-60"
          >
            {isBusy ? '...' : 'Send'}
          </button>
        </div>
        <p className="text-[10px] text-slate-500 mt-2 text-right">{inputMessage.length}/500</p>
      </form>
    </div>
  );
};

export default ChatAssistant;
