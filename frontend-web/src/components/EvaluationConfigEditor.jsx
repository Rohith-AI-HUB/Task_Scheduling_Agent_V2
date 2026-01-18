import { useMemo } from 'react';

const DEFAULT_CODE = {
  language: 'python',
  timeout_ms: 2000,
  memory_limit_mb: 256,
  max_output_kb: 64,
  enable_quality_checks: true,
  security_mode: 'warn',
  weight: 0.7,
  test_cases: [],
};

const DEFAULT_DOC = {
  keywords: [],
  min_words: null,
  enable_readability: true,
  enable_plagiarism: false,
  enable_structure: true,
  weight: 0.3,
};

const clampInt = (value, fallback) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.trunc(n);
};

const clampFloat = (value, fallback) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return n;
};

const normalizeKeywords = (raw) => {
  return String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 200);
};

const EvaluationConfigEditor = ({ value, onChange, disabled = false }) => {
  const cfg = value || null;
  const code = cfg?.code || null;
  const doc = cfg?.document || null;

  const keywordText = useMemo(() => (doc?.keywords || []).join(', '), [doc?.keywords]);

  const setCfg = (next) => {
    const hasCode = !!next?.code;
    const hasDoc = !!next?.document;
    onChange(hasCode || hasDoc ? next : null);
  };

  return (
    <div className="p-4 rounded-xl border border-[#eae6f4] dark:border-[#2a2438] bg-[#faf9fc] dark:bg-[#221b36] space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-sm font-bold text-[#110d1c] dark:text-white">Evaluation (optional)</div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">
            <input
              type="checkbox"
              checked={!!code}
              disabled={disabled}
              onChange={(e) => {
                const checked = e.target.checked;
                setCfg({ code: checked ? { ...DEFAULT_CODE } : null, document: doc ? { ...doc } : null });
              }}
            />
            Code
          </label>
          <label className="flex items-center gap-2 text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">
            <input
              type="checkbox"
              checked={!!doc}
              disabled={disabled}
              onChange={(e) => {
                const checked = e.target.checked;
                setCfg({ code: code ? { ...code } : null, document: checked ? { ...DEFAULT_DOC } : null });
              }}
            />
            Document
          </label>
        </div>
      </div>

      {code ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Language
              </label>
              <select
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                value={code.language || 'python'}
                disabled={disabled}
                onChange={(e) => setCfg({ code: { ...code, language: e.target.value }, document: doc ? { ...doc } : null })}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
              </select>
              {code.language && code.language !== 'python' ? (
                <div className="mt-1 text-xs text-[#5d479e] dark:text-[#a094c7]">
                  Requires runtime installed on the backend host.
                </div>
              ) : null}
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Security Mode
              </label>
              <select
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                value={code.security_mode || 'warn'}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({ code: { ...code, security_mode: e.target.value }, document: doc ? { ...doc } : null })
                }
              >
                <option value="warn">Warn</option>
                <option value="block">Block</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Timeout (ms)
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                value={code.timeout_ms ?? 2000}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({ code: { ...code, timeout_ms: clampInt(e.target.value, 2000) }, document: doc ? { ...doc } : null })
                }
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Memory (MB)
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                value={code.memory_limit_mb ?? 256}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({
                    code: { ...code, memory_limit_mb: clampInt(e.target.value, 256) },
                    document: doc ? { ...doc } : null,
                  })
                }
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Max Output (KB)
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                value={code.max_output_kb ?? 64}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({
                    code: { ...code, max_output_kb: clampInt(e.target.value, 64) },
                    document: doc ? { ...doc } : null,
                  })
                }
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Code Weight
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                step="0.1"
                value={code.weight ?? 0.7}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({ code: { ...code, weight: clampFloat(e.target.value, 0.7) }, document: doc ? { ...doc } : null })
                }
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!code.enable_quality_checks}
              disabled={disabled}
              onChange={(e) =>
                setCfg({ code: { ...code, enable_quality_checks: e.target.checked }, document: doc ? { ...doc } : null })
              }
            />
            <div className="text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">Enable quality checks</div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="text-sm font-bold text-[#110d1c] dark:text-white">Test Cases</div>
              <button
                type="button"
                className="px-4 py-2 rounded-lg text-sm font-bold border border-gray-300 dark:border-gray-600 hover:border-primary/40 transition-colors disabled:opacity-60"
                disabled={disabled}
                onClick={() => {
                  const nextCases = [...(code.test_cases || [])];
                  nextCases.push({
                    input: '',
                    expected_output: '',
                    timeout_ms: null,
                    comparison_mode: 'exact',
                    points: 1,
                    description: '',
                  });
                  setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                }}
              >
                Add Test
              </button>
            </div>

            {(code.test_cases || []).length === 0 ? (
              <div className="text-sm text-[#5d479e] dark:text-[#a094c7]">No test cases configured.</div>
            ) : (
              <div className="space-y-3">
                {(code.test_cases || []).map((tc, idx) => (
                  <div key={idx} className="p-3 rounded-xl border border-[#eae6f4] dark:border-[#2a2438] bg-white dark:bg-[#1c162e]">
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <div className="text-sm font-bold text-[#110d1c] dark:text-white">Case {idx + 1}</div>
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-lg text-xs font-bold border border-gray-300 dark:border-gray-600 hover:border-rose-400 transition-colors disabled:opacity-60"
                        disabled={disabled}
                        onClick={() => {
                          const nextCases = [...(code.test_cases || [])];
                          nextCases.splice(idx, 1);
                          setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                        }}
                      >
                        Remove
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="md:col-span-2">
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Description
                        </label>
                        <input
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          value={tc.description || ''}
                          disabled={disabled}
                          onChange={(e) => {
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, description: e.target.value };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Comparison
                        </label>
                        <select
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          value={tc.comparison_mode || 'exact'}
                          disabled={disabled}
                          onChange={(e) => {
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, comparison_mode: e.target.value };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        >
                          <option value="exact">Exact</option>
                          <option value="normalized">Normalized</option>
                          <option value="contains">Contains</option>
                          <option value="regex">Regex</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Points
                        </label>
                        <input
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          type="number"
                          value={tc.points ?? 1}
                          disabled={disabled}
                          onChange={(e) => {
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, points: clampInt(e.target.value, 1) };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Timeout (ms)
                        </label>
                        <input
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          type="number"
                          value={tc.timeout_ms ?? ''}
                          disabled={disabled}
                          onChange={(e) => {
                            const raw = e.target.value;
                            const val = raw === '' ? null : clampInt(raw, null);
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, timeout_ms: val };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Input
                        </label>
                        <textarea
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          rows="3"
                          value={tc.input || ''}
                          disabled={disabled}
                          onChange={(e) => {
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, input: e.target.value };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                          Expected Output
                        </label>
                        <textarea
                          className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                          rows="2"
                          value={tc.expected_output || ''}
                          disabled={disabled}
                          onChange={(e) => {
                            const nextCases = [...(code.test_cases || [])];
                            nextCases[idx] = { ...tc, expected_output: e.target.value };
                            setCfg({ code: { ...code, test_cases: nextCases }, document: doc ? { ...doc } : null });
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {doc ? (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Keywords (comma-separated)
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                value={keywordText}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({ code: code ? { ...code } : null, document: { ...doc, keywords: normalizeKeywords(e.target.value) } })
                }
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Min Words
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                value={doc.min_words ?? ''}
                disabled={disabled}
                onChange={(e) => {
                  const raw = e.target.value;
                  const val = raw === '' ? null : clampInt(raw, null);
                  setCfg({ code: code ? { ...code } : null, document: { ...doc, min_words: val } });
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#5d479e] dark:text-[#a094c7] uppercase mb-1 tracking-widest">
                Doc Weight
              </label>
              <input
                className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 focus:border-primary focus:ring-primary text-sm"
                type="number"
                step="0.1"
                value={doc.weight ?? 0.3}
                disabled={disabled}
                onChange={(e) =>
                  setCfg({ code: code ? { ...code } : null, document: { ...doc, weight: clampFloat(e.target.value, 0.3) } })
                }
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">
              <input
                type="checkbox"
                checked={!!doc.enable_readability}
                disabled={disabled}
                onChange={(e) => setCfg({ code: code ? { ...code } : null, document: { ...doc, enable_readability: e.target.checked } })}
              />
              Readability
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">
              <input
                type="checkbox"
                checked={!!doc.enable_structure}
                disabled={disabled}
                onChange={(e) => setCfg({ code: code ? { ...code } : null, document: { ...doc, enable_structure: e.target.checked } })}
              />
              Structure
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#4b3d75] dark:text-[#c0bad3]">
              <input
                type="checkbox"
                checked={!!doc.enable_plagiarism}
                disabled={disabled}
                onChange={(e) => setCfg({ code: code ? { ...code } : null, document: { ...doc, enable_plagiarism: e.target.checked } })}
              />
              Plagiarism
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default EvaluationConfigEditor;
