import { useState } from 'react';

const EvaluationResults = ({ evaluation, taskPoints }) => {
  const [expandedSections, setExpandedSections] = useState({
    testCases: false,
    warnings: false,
    document: false,
  });

  if (!evaluation) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400">
        No evaluation results available
      </div>
    );
  }

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
      running: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
      completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
      failed: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
      passed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
      timeout: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
      runtime_error: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
      error: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
    };
    return colors[status] || 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300';
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 75) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-blue-600 dark:text-blue-400';
    if (score >= 40) return 'text-amber-600 dark:text-amber-400';
    return 'text-rose-600 dark:text-rose-400';
  };

  const status = evaluation.status || 'not started';
  const aiScore = evaluation.ai_score;
  const codeResults = evaluation.code_results || {};
  const documentMetrics = evaluation.document_metrics || {};
  const aiFeedback = evaluation.ai_feedback;
  const lastError = evaluation.last_error;

  return (
    <div className="space-y-4">
      {/* Status and Score Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded ${getStatusColor(status)}`}>
            {status.replace('_', ' ').toUpperCase()}
          </span>
          {aiScore !== null && aiScore !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">AI Score:</span>
              <span className={`text-2xl font-bold ${getScoreColor(aiScore)}`}>
                {aiScore}/100
              </span>
              {taskPoints && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  ({Math.round((aiScore / 100) * taskPoints)}/{taskPoints} pts)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {lastError && (
        <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-rose-600 dark:text-rose-400 text-lg">error</span>
            <div>
              <h4 className="font-bold text-rose-800 dark:text-rose-300 text-sm mb-1">Evaluation Error</h4>
              <p className="text-sm text-rose-700 dark:text-rose-400 whitespace-pre-wrap">{lastError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Code Evaluation Results */}
      {(codeResults.passed > 0 || codeResults.failed > 0) && (
        <div className="bg-white dark:bg-[#1c162e] rounded-lg border border-[#eae6f4] dark:border-[#2a2438] overflow-hidden">
          <div className="px-4 py-3 bg-[#faf9fc] dark:bg-[#221b36] border-b border-[#eae6f4] dark:border-[#2a2438]">
            <h4 className="font-bold text-sm text-[#110d1c] dark:text-white flex items-center gap-2">
              <span className="material-symbols-outlined text-lg">code</span>
              Code Evaluation
            </h4>
          </div>
          <div className="p-4 space-y-3">
            {/* Test Results Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-2 bg-emerald-50 dark:bg-emerald-900/10 rounded-lg">
                <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  {codeResults.passed}
                </div>
                <div className="text-xs text-emerald-700 dark:text-emerald-500 font-medium">Passed</div>
              </div>
              <div className="text-center p-2 bg-rose-50 dark:bg-rose-900/10 rounded-lg">
                <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
                  {codeResults.failed}
                </div>
                <div className="text-xs text-rose-700 dark:text-rose-500 font-medium">Failed</div>
              </div>
              {codeResults.total_points > 0 && (
                <>
                  <div className="text-center p-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {codeResults.earned_points}
                    </div>
                    <div className="text-xs text-blue-700 dark:text-blue-500 font-medium">Earned</div>
                  </div>
                  <div className="text-center p-2 bg-gray-50 dark:bg-gray-900/10 rounded-lg">
                    <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                      {codeResults.total_points}
                    </div>
                    <div className="text-xs text-gray-700 dark:text-gray-500 font-medium">Total</div>
                  </div>
                </>
              )}
            </div>

            {/* Code Quality Warnings */}
            {codeResults.warnings && codeResults.warnings.length > 0 && (
              <div className="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('warnings')}
                  className="w-full px-3 py-2 bg-amber-50 dark:bg-amber-900/20 flex items-center justify-between hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
                >
                  <span className="text-sm font-bold text-amber-800 dark:text-amber-300 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">warning</span>
                    Code Quality Warnings ({codeResults.warnings.length})
                  </span>
                  <span className="material-symbols-outlined text-amber-600 dark:text-amber-400">
                    {expandedSections.warnings ? 'expand_less' : 'expand_more'}
                  </span>
                </button>
                {expandedSections.warnings && (
                  <div className="p-3 bg-white dark:bg-[#140f23] space-y-2">
                    {codeResults.warnings.map((warning, idx) => (
                      <div key={idx} className="text-sm text-amber-700 dark:text-amber-400 flex items-start gap-2">
                        <span className="font-bold">{idx + 1}.</span>
                        <span>{warning}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Test Case Details */}
            {codeResults.test_results && codeResults.test_results.length > 0 && (
              <div className="border border-[#eae6f4] dark:border-[#2a2438] rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('testCases')}
                  className="w-full px-3 py-2 bg-[#f9f8fc] dark:bg-[#221b36] flex items-center justify-between hover:bg-[#f0eff5] dark:hover:bg-[#2a2438] transition-colors"
                >
                  <span className="text-sm font-bold text-[#110d1c] dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">list</span>
                    Test Case Details ({codeResults.test_results.length})
                  </span>
                  <span className="material-symbols-outlined text-primary">
                    {expandedSections.testCases ? 'expand_less' : 'expand_more'}
                  </span>
                </button>
                {expandedSections.testCases && (
                  <div className="divide-y divide-[#eae6f4] dark:divide-[#2a2438]">
                    {codeResults.test_results.map((test, idx) => (
                      <div key={idx} className="p-3 bg-white dark:bg-[#140f23]">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-[#110d1c] dark:text-white">
                              #{test.case_number}
                            </span>
                            {test.description && (
                              <span className="text-sm text-gray-600 dark:text-gray-400">
                                {test.description}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {test.points > 1 && (
                              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                                {test.points} pts
                              </span>
                            )}
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${getStatusColor(test.status)}`}>
                              {test.status.replace('_', ' ')}
                            </span>
                          </div>
                        </div>

                        {test.output && test.status === 'passed' && (
                          <div className="mt-2 p-2 bg-emerald-50 dark:bg-emerald-900/10 rounded text-xs font-mono text-emerald-800 dark:text-emerald-300 overflow-x-auto">
                            {test.output}
                          </div>
                        )}

                        {test.error && (
                          <div className="mt-2 p-2 bg-rose-50 dark:bg-rose-900/10 rounded text-xs text-rose-700 dark:text-rose-400">
                            <span className="font-bold">Error: </span>
                            {test.error}
                          </div>
                        )}

                        {test.status === 'failed' && test.expected && test.actual && (
                          <div className="mt-2 grid grid-cols-2 gap-2">
                            <div>
                              <div className="text-xs font-bold text-gray-600 dark:text-gray-400 mb-1">Expected:</div>
                              <div className="p-2 bg-gray-50 dark:bg-gray-900/20 rounded text-xs font-mono overflow-x-auto">
                                {test.expected}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs font-bold text-gray-600 dark:text-gray-400 mb-1">Actual:</div>
                              <div className="p-2 bg-gray-50 dark:bg-gray-900/20 rounded text-xs font-mono overflow-x-auto">
                                {test.actual}
                              </div>
                            </div>
                          </div>
                        )}

                        {test.stderr && (
                          <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-900/10 rounded text-xs font-mono text-amber-800 dark:text-amber-300 overflow-x-auto">
                            <span className="font-bold">stderr: </span>
                            {test.stderr}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Document Analysis Results */}
      {documentMetrics.word_count > 0 && (
        <div className="bg-white dark:bg-[#1c162e] rounded-lg border border-[#eae6f4] dark:border-[#2a2438] overflow-hidden">
          <div className="px-4 py-3 bg-[#faf9fc] dark:bg-[#221b36] border-b border-[#eae6f4] dark:border-[#2a2438]">
            <button
              onClick={() => toggleSection('document')}
              className="w-full flex items-center justify-between hover:opacity-80 transition-opacity"
            >
              <h4 className="font-bold text-sm text-[#110d1c] dark:text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-lg">description</span>
                Document Analysis
              </h4>
              <span className="material-symbols-outlined text-primary">
                {expandedSections.document ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>
          {expandedSections.document && (
            <div className="p-4 space-y-3">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 bg-[#f9f8fc] dark:bg-[#140f23] rounded-lg">
                  <div className="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">Words</div>
                  <div className="text-xl font-bold text-[#110d1c] dark:text-white">
                    {documentMetrics.word_count}
                  </div>
                  {documentMetrics.meets_min_words !== undefined && (
                    <div className={`text-xs font-medium mt-1 ${documentMetrics.meets_min_words ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                      {documentMetrics.meets_min_words ? '✓ Meets requirement' : '✗ Below minimum'}
                    </div>
                  )}
                </div>

                {documentMetrics.keyword_match_ratio !== undefined && (
                  <div className="p-3 bg-[#f9f8fc] dark:bg-[#140f23] rounded-lg">
                    <div className="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">Keyword Match</div>
                    <div className="text-xl font-bold text-[#110d1c] dark:text-white">
                      {documentMetrics.keyword_match_ratio}%
                    </div>
                  </div>
                )}

                {documentMetrics.readability_score !== undefined && documentMetrics.readability_score > 0 && (
                  <div className="p-3 bg-[#f9f8fc] dark:bg-[#140f23] rounded-lg">
                    <div className="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">Readability</div>
                    <div className="text-xl font-bold text-[#110d1c] dark:text-white">
                      {documentMetrics.readability_score.toFixed(1)}
                    </div>
                    {documentMetrics.grade_level && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Grade {documentMetrics.grade_level.toFixed(1)}
                      </div>
                    )}
                  </div>
                )}

                {documentMetrics.structure_quality !== undefined && documentMetrics.structure_quality > 0 && (
                  <div className="p-3 bg-[#f9f8fc] dark:bg-[#140f23] rounded-lg">
                    <div className="text-xs text-gray-600 dark:text-gray-400 font-medium mb-1">Structure</div>
                    <div className="text-xl font-bold text-[#110d1c] dark:text-white">
                      {documentMetrics.structure_quality.toFixed(0)}%
                    </div>
                    {documentMetrics.paragraph_count > 0 && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {documentMetrics.paragraph_count} paragraphs
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Keywords Found */}
              {documentMetrics.keywords_found && documentMetrics.keywords_found.length > 0 && (
                <div>
                  <div className="text-xs font-bold text-gray-600 dark:text-gray-400 mb-2">Keywords Found:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {documentMetrics.keywords_found.map((keyword, idx) => (
                      <span key={idx} className="px-2 py-1 bg-primary/10 text-primary text-xs font-medium rounded">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Plagiarism Warning */}
              {documentMetrics.plagiarism_detected && (
                <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <span className="material-symbols-outlined text-rose-600 dark:text-rose-400">warning</span>
                    <div>
                      <h5 className="font-bold text-rose-800 dark:text-rose-300 text-sm">Plagiarism Warning</h5>
                      <p className="text-sm text-rose-700 dark:text-rose-400 mt-1">
                        Similarity detected: {documentMetrics.max_similarity}% match with other submissions
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AI Feedback */}
      {aiFeedback && (
        <div className="bg-[#f9f8fc] dark:bg-[#140f23] border border-[#eae6f4] dark:border-[#2a2438] rounded-lg p-4">
          <h4 className="text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-2 tracking-widest flex items-center gap-2">
            <span className="material-symbols-outlined text-base">smart_toy</span>
            AI Feedback
          </h4>
          <pre className="text-sm text-[#110d1c] dark:text-white/90 whitespace-pre-wrap font-sans leading-relaxed">
            {aiFeedback}
          </pre>
        </div>
      )}
    </div>
  );
};

export default EvaluationResults;
