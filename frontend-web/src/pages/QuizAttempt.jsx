import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';

const QuizAttempt = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();

  const [quizData, setQuizData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState([]);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [malpracticeEvents, setMalpracticeEvents] = useState([]);
  const [submissionId, setSubmissionId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const startTimeRef = useRef(null);
  const timerRef = useRef(null);
  const malpracticeCountRef = useRef(0);
  const hasStartedRef = useRef(false);

  // Load quiz and start attempt
  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    const startQuiz = async () => {
      try {
        const token = localStorage.getItem('authToken');
        const response = await axios.post(
          `${import.meta.env.VITE_API_URL}/api/quizzes/start?task_id=${taskId}`,
          {},
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );

        const data = response.data;
        setQuizData(data);
        setSubmissionId(data.submission_id);
        setAnswers(new Array(data.questions.length).fill(-1));
        setTimeRemaining(data.time_limit_minutes * 60);
        startTimeRef.current = Date.now();

        // Request fullscreen if enabled
        if (data.enable_fullscreen) {
          requestFullscreen();
        }

        setLoading(false);
      } catch (err) {
        console.error('Error starting quiz:', err);
        setError(err.response?.data?.detail || 'Failed to start quiz');
        setLoading(false);
      }
    };

    startQuiz();

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      exitFullscreen();
    };
  }, [taskId]);

  // Timer countdown
  useEffect(() => {
    if (!quizData || timeRemaining <= 0) return;

    timerRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          handleAutoSubmit('Time expired');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [quizData]);

  // Anti-cheating: Fullscreen monitoring
  useEffect(() => {
    if (!quizData?.enable_anti_cheating) return;

    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement;
      setIsFullscreen(isNowFullscreen);

      if (!isNowFullscreen && quizData.enable_fullscreen) {
        recordMalpractice('exit_fullscreen', 'Student exited fullscreen mode');
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [quizData]);

  // Anti-cheating: Tab visibility
  useEffect(() => {
    if (!quizData?.enable_anti_cheating) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        recordMalpractice('tab_switch', 'Student switched tabs or minimized window');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [quizData]);

  // Anti-cheating: Window blur
  useEffect(() => {
    if (!quizData?.enable_anti_cheating) return;

    const handleBlur = () => {
      recordMalpractice('window_blur', 'Student switched to another application');
    };

    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('blur', handleBlur);
    };
  }, [quizData]);

  // Anti-cheating: Copy/Paste
  useEffect(() => {
    if (!quizData?.enable_anti_cheating) return;

    const handleCopy = (e) => {
      e.preventDefault();
      recordMalpractice('copy_paste', 'Student attempted to copy text');
    };

    const handlePaste = (e) => {
      e.preventDefault();
      recordMalpractice('copy_paste', 'Student attempted to paste text');
    };

    const handleContextMenu = (e) => {
      e.preventDefault();
      recordMalpractice('right_click', 'Student right-clicked (context menu)');
    };

    document.addEventListener('copy', handleCopy);
    document.addEventListener('paste', handlePaste);
    document.addEventListener('contextmenu', handleContextMenu);

    return () => {
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('paste', handlePaste);
      document.removeEventListener('contextmenu', handleContextMenu);
    };
  }, [quizData]);

  const requestFullscreen = () => {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch((err) => {
        console.error('Fullscreen request failed:', err);
      });
    }
  };

  const exitFullscreen = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  };

  const recordMalpractice = (eventType, details) => {
    const event = {
      event_type: eventType,
      timestamp: new Date().toISOString(),
      details: details
    };

    setMalpracticeEvents((prev) => [...prev, event]);
    malpracticeCountRef.current += 1;

    // Auto-submit after 3 violations
    if (malpracticeCountRef.current >= 3) {
      handleAutoSubmit('Multiple malpractice violations detected');
    }
  };

  const handleAnswerChange = (questionIndex, optionIndex) => {
    const newAnswers = [...answers];
    newAnswers[questionIndex] = optionIndex;
    setAnswers(newAnswers);
  };

  const handleAutoSubmit = async (reason) => {
    if (isSubmitting) return;

    recordMalpractice('other', reason);
    await submitQuiz(true);
  };

  const submitQuiz = async (isAutoSubmit = false) => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    try {
      const timeTaken = Math.floor((Date.now() - startTimeRef.current) / 1000);
      const token = localStorage.getItem('authToken');

      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/quizzes/submit`,
        {
          task_id: taskId,
          answers: answers,
          time_taken_seconds: timeTaken,
          malpractice_events: malpracticeEvents
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      exitFullscreen();

      // Navigate to results
      alert(
        isAutoSubmit
          ? 'Quiz auto-submitted due to violations. You have been locked out.'
          : 'Quiz submitted successfully!'
      );
      navigate(`/tasks/${taskId}`);
    } catch (err) {
      console.error('Error submitting quiz:', err);
      alert('Failed to submit quiz: ' + (err.response?.data?.detail || 'Unknown error'));
      setIsSubmitting(false);
    }
  };

  const handleManualSubmit = () => {
    const unanswered = answers.filter((a) => a === -1).length;
    if (unanswered > 0) {
      if (!confirm(`You have ${unanswered} unanswered questions. Submit anyway?`)) {
        return;
      }
    }
    submitQuiz(false);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading quiz...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md">
          <h2 className="text-xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-700 mb-4">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Timer and Header */}
      <div className="max-w-4xl mx-auto bg-gray-800 rounded-lg p-4 mb-4 sticky top-4 z-10 shadow-lg">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">Quiz in Progress</h1>
            <p className="text-sm text-gray-400">
              {answers.filter((a) => a !== -1).length} / {quizData.questions.length} answered
            </p>
          </div>
          <div className="text-right">
            <div
              className={`text-3xl font-bold ${
                timeRemaining < 60 ? 'text-red-500 animate-pulse' : 'text-green-400'
              }`}
            >
              {formatTime(timeRemaining)}
            </div>
            <p className="text-xs text-gray-400">Time Remaining</p>
          </div>
        </div>

        {malpracticeEvents.length > 0 && (
          <div className="mt-3 bg-red-900 border border-red-700 rounded p-2">
            <p className="text-sm font-semibold">
              ⚠️ Warning: {malpracticeEvents.length} violation(s) detected
            </p>
            <p className="text-xs">3 violations will result in automatic submission and lockout</p>
          </div>
        )}
      </div>

      {/* Questions */}
      <div className="max-w-4xl mx-auto space-y-6">
        {quizData.questions.map((question, qIdx) => (
          <div key={qIdx} className="bg-gray-800 rounded-lg p-6 shadow-md">
            <div className="flex items-start mb-4">
              <span className="text-blue-400 font-bold mr-3 text-lg">Q{qIdx + 1}.</span>
              <p className="text-lg flex-1">{question.question}</p>
              <span className="text-gray-400 text-sm ml-2">{question.points} pt(s)</span>
            </div>

            <div className="space-y-3 ml-8">
              {question.options.map((option, oIdx) => (
                <label
                  key={oIdx}
                  className={`flex items-center p-3 rounded border-2 cursor-pointer transition-all ${
                    answers[qIdx] === oIdx
                      ? 'border-blue-500 bg-blue-900 bg-opacity-30'
                      : 'border-gray-700 hover:border-gray-600 hover:bg-gray-750'
                  }`}
                >
                  <input
                    type="radio"
                    name={`question-${qIdx}`}
                    checked={answers[qIdx] === oIdx}
                    onChange={() => handleAnswerChange(qIdx, oIdx)}
                    className="mr-3 h-5 w-5"
                  />
                  <span className="font-medium mr-2">{String.fromCharCode(65 + oIdx)}.</span>
                  <span>{option}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Submit Button */}
      <div className="max-w-4xl mx-auto mt-8 mb-8">
        <button
          onClick={handleManualSubmit}
          disabled={isSubmitting}
          className="w-full py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold text-lg rounded-lg shadow-lg transition-colors"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Quiz'}
        </button>
      </div>

      {/* Anti-exit warning */}
      {!isFullscreen && quizData.enable_fullscreen && (
        <div className="fixed top-0 left-0 right-0 bg-red-600 text-white text-center py-2 z-50">
          ⚠️ Please return to fullscreen mode or your quiz will be auto-submitted
        </div>
      )}
    </div>
  );
};

export default QuizAttempt;
