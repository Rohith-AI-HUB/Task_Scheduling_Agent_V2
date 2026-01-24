import { useState } from 'react';
import axios from 'axios';

const QuizGenerator = ({ onQuestionsGenerated, onClose }) => {
  const [documentText, setDocumentText] = useState('');
  const [topic, setTopic] = useState('');
  const [numQuestions, setNumQuestions] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check file type
    const allowedTypes = [
      'application/pdf',
      'text/plain',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ];

    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a PDF, TXT, DOCX, or PPTX file');
      return;
    }

    // For now, we'll just read text files directly
    // For PDF/DOCX/PPTX, the teacher would need to copy-paste or we'd need a file upload endpoint
    if (file.type === 'text/plain') {
      const reader = new FileReader();
      reader.onload = (e) => {
        setDocumentText(e.target.result);
      };
      reader.readAsText(file);
    } else {
      setError('For PDF/DOCX/PPTX files, please copy and paste the text content for now');
    }
  };

  const handleGenerate = async () => {
    if (!documentText.trim()) {
      setError('Please provide document content');
      return;
    }

    if (!topic.trim()) {
      setError('Please specify a topic');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('authToken');
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/quizzes/generate`,
        {
          document_content: documentText,
          topic: topic,
          num_questions: numQuestions
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      onQuestionsGenerated(response.data);
      onClose();
    } catch (err) {
      console.error('Error generating questions:', err);
      setError(err.response?.data?.detail || 'Failed to generate questions');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-lg">
          <h2 className="text-2xl font-bold">Generate Quiz Questions with AI</h2>
          <p className="text-sm mt-1 opacity-90">
            Upload a document and specify a topic to auto-generate quiz questions
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Topic Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Topic / Chapter <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Chapter 5: Photosynthesis"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Number of Questions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Questions
            </label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="5"
                max="50"
                value={numQuestions}
                onChange={(e) => setNumQuestions(parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="text-lg font-semibold text-blue-600 w-12 text-center">
                {numQuestions}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Slide to select 5-50 questions</p>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload Document (Optional)
            </label>
            <input
              type="file"
              accept=".txt,.pdf,.docx,.pptx"
              onChange={handleFileUpload}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="text-xs text-gray-500 mt-1">
              Supports: TXT (recommended), PDF, DOCX, PPTX
            </p>
          </div>

          {/* Document Text Area */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Content <span className="text-red-500">*</span>
            </label>
            <textarea
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
              placeholder="Paste textbook chapter content, lecture notes, or study material here..."
              rows={10}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Characters: {documentText.length} / 50,000
            </p>
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
            <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
              <li>AI analyzes your document content</li>
              <li>Generates multiple-choice questions (4 options each)</li>
              <li>Questions test comprehension, not just memorization</li>
              <li>You can review and edit questions before saving</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 rounded-b-lg flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading || !documentText.trim() || !topic.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </>
            ) : (
              'Generate Questions'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default QuizGenerator;
