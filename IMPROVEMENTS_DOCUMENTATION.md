# Task Scheduling Agent V2 — Improvements & Fixes

**Version:** 2.2  
**Updated:** 2026-01-18T22:23:58.6018138+05:30  
**Status:** Phase 5 hardened for non-Docker deployment (Render)

---

## Change Log (Version-Controlled)

### 2026-01-18T22:23:58.6018138+05:30

- **Issue:** Docker-based isolation is not feasible for the intended deployment path (Render backend, Vercel frontend) and some environments (college-managed servers).
  - **Current state (before):** Subprocess execution existed, but lacked explicit per-task config validation and output bounding.
  - **Enhancement:** Strengthen the non-Docker sandbox: best-effort resource limits, strict test-case config, and robust stdout/stderr bounding.
  - **Action taken:** Implemented output-limited runners, safer resource handling on all OS, and a typed `evaluation_config` on tasks.
  - **Rationale:** Reduces risk of runaway output/memory usage and makes evaluation behavior predictable and auditable.

- **Issue:** Python wrapper imported `resource` unconditionally, which breaks on non-POSIX environments.
  - **Current state (before):** Running the Python runner on Windows could fail due to `ImportError: resource`.
  - **Enhancement:** Make resource limits best-effort and OS-safe.
  - **Action taken:** Guarded `resource` import inside the wrapper and kept timeout/output caps platform-independent.
  - **Files:** [code_runner.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/ai/evaluator/code_runner.py)

- **Issue:** Unbounded subprocess output can exhaust server memory on large prints.
  - **Current state (before):** `capture_output=True` buffered all output in memory.
  - **Enhancement:** Enforce a maximum stdout/stderr size per run.
  - **Action taken:** Added an output-capped runner implementation used by Python/JS/Java execution paths.
  - **Files:** [code_runner.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/ai/evaluator/code_runner.py)

- **Issue:** Test cases and evaluation settings were untyped, allowing invalid configs to reach runtime.
  - **Current state (before):** `evaluation_config` was a free-form dict in Mongo.
  - **Enhancement:** Add explicit test-case configuration with schema validation.
  - **Action taken:** Added `TaskEvaluationConfig` + `CodeEvaluationConfig` + `CodeTestCase` models and wired them into task create/update responses.
  - **Files:** [task.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/models/task.py), [tasks.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/api/tasks.py)

- **Issue:** No automated regression tests for sandbox runner behaviors.
  - **Current state (before):** Runner behavior changes were not covered by unit tests.
  - **Enhancement:** Add tests for normalized comparisons, output caps, and security blocking.
  - **Action taken:** Added a focused test suite for the code runner.
  - **Files:** [test_code_runner.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/tests/test_code_runner.py)

- **Verification (post-change):**
  - Backend: `python -m pytest` (16 passed)

### 2026-01-18T22:13:25.5106014+05:30

- **Issue:** This document contained multiple inaccurate claims (file sizes, features, endpoints, and component paths) that did not match the repository state.
  - **Current state (before):** Marked as “Production Ready” with multi-language sandboxing, plagiarism detection, large new components, and endpoints that were not present in code.
  - **Enhancement:** Align documentation with the actual implementation, explicitly track what is implemented vs planned, and add a timestamped log.
  - **Action taken:** Rewrote this document to be accurate, auditable, and maintainable.
  - **Rationale:** Documentation must be trustworthy to support teacher oversight, security reviews, and onboarding.

- **Issue:** Submission response model had a duplicate field definition.
  - **Current state (before):** `attachments` field was duplicated in `SubmissionResponse`, which is error-prone and confusing.
  - **Enhancement:** Remove duplication and add a structured progress response model.
  - **Action taken:** Cleaned up models and added `EvaluationProgressResponse`.
  - **Rationale:** Improves code quality and reduces model ambiguity.
  - **Files:** [submission.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/models/submission.py)

- **Issue:** Evaluation progress endpoint returned an ad-hoc schema and included non-standard status values.
  - **Current state (before):** Returned `status: "not_started"` (outside allowed status values) and was undocumented by schema.
  - **Enhancement:** Enforce a stable response model and normalize status values.
  - **Action taken:** Added `response_model=EvaluationProgressResponse` and normalized status to the allowed set.
  - **Rationale:** Reduces frontend branching and prevents contract drift.
  - **Files:** [submissions.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/api/submissions.py)

- **Issue:** Evaluation summary endpoint loaded all submissions into Python.
  - **Current state (before):** Computed counts and average score in application code.
  - **Enhancement:** Use MongoDB aggregation for better performance and scalability.
  - **Action taken:** Implemented an aggregation pipeline with `$facet` to compute counts + average.
  - **Rationale:** Improves performance for large classes and reduces backend memory usage.
  - **Files:** [tasks.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/api/tasks.py)

- **Issue:** Frontend polling logic could be noisy and included console logging.
  - **Current state (before):** Polled per submission in a loop and logged errors to console.
  - **Enhancement:** Poll concurrently and keep polling silent on transient errors.
  - **Action taken:** Polled progress endpoints concurrently via `Promise.all` and removed console logging.
  - **Rationale:** Better UX, fewer render-time side effects, and lower overhead.
  - **Files:** [TaskView.jsx](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/frontend-web/src/pages/TaskView.jsx)

- **Verification (post-change):**
  - Backend: `python -m pytest` (11 passed)
  - Frontend: `npm run lint` (0 warnings), `npm run build` (success)

---

## Executive Summary

This document tracks improvements across the Task Scheduling Agent V2 codebase with emphasis on correctness, security posture, error handling, performance, and maintainability.

Phase 5 (AI Evaluation Engine) is implemented as a baseline that supports:
- Persisted evaluation status and results on submissions
- Teacher-triggered single and batch evaluation
- Teacher dashboard indicators and result viewer
- Lightweight progress polling endpoint

The baseline intentionally prioritizes safe defaults and clear API contracts for Render-style deployments where Docker may not be available.

---

## Audit Findings (Issues → Enhancements → Implementation)

### 1) Documentation correctness and completeness

- **Current state:** Prior versions overstated features and referenced incorrect file names/paths (case mismatches like `taskview.jsx` vs `TaskView.jsx`) and endpoints that did not exist.
- **Enhancement:** Keep this document as an auditable record of what exists now, what was verified by tests, and what is planned.
- **Implementation:** This document was rewritten and a timestamped change log was added (see above).

### 2) Code quality and API contract consistency

- **Current state:** Duplicate Pydantic field definitions and ad-hoc API payloads increase the chance of contract drift.
- **Enhancement:** Enforce stable response models and keep statuses in a fixed set.
- **Implementation:** `EvaluationProgressResponse` added; evaluation progress endpoint now uses a response model and normalized status values.

### 3) Performance optimization

- **Current state:** Class evaluation summary previously required loading all submissions into application memory.
- **Enhancement:** Use DB-level aggregation for counts and averages.
- **Implementation:** Summary endpoint now uses an aggregation pipeline.

### 4) Error handling and robustness

- **Current state:** Polling and evaluation status reporting can fail silently or return inconsistent shapes.
- **Enhancement:** Make progress polling resilient, keep server response shape stable, and keep polling only when necessary.
- **Implementation:** Frontend polls only while evaluations are pending/running; backend returns a stable progress schema.

### 5) Maintainability

- **Current state:** Mixed “implemented” and “planned” claims without explicit separation.
- **Enhancement:** Separate “Implemented” vs “Planned” clearly and log changes with rationale.
- **Implementation:** Added “Current Implementation Snapshot” and “Planned Improvements” sections.

---

## Current Implementation Snapshot (Truth Source)

### Backend

- **Submission evaluation storage**
  - Location: `submissions.evaluation`
  - Model: [SubmissionEvaluation](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/models/submission.py)
  - Status values: `pending | running | completed | failed`

- **Evaluation execution**
  - Trigger: teacher endpoint calls a queue function which schedules evaluation work on the server event loop
  - Service: [submission_service.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/services/submission_service.py)
  - Code runner: Subprocess runner (isolated mode `-I`) with output caps and best-effort resource limits
    - File: [code_runner.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/ai/evaluator/code_runner.py)
  - Task-level configuration: typed `evaluation_config` stored on tasks
    - Model: [TaskEvaluationConfig](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/models/task.py)
  - Document analyzer: word count + keyword match; optional PDF extraction if `pypdf` or `PyPDF2` installed
    - File: [doc_analyzer.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/ai/evaluator/doc_analyzer.py)
  - Feedback generator: formats a basic AI feedback string
    - File: [report_gen.py](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/backend/app/ai/evaluator/report_gen.py)

- **API endpoints (Phase 5)**
  - `POST /api/submissions/{id}/evaluate` (teacher) — triggers evaluation
  - `GET /api/submissions/{id}/evaluation` (teacher or owning student) — returns evaluation object
  - `GET /api/submissions/{id}/evaluation/progress` — lightweight polling response
  - `POST /api/submissions/batch/evaluate` (teacher) — batch trigger
  - `GET /api/tasks/{id}/evaluations/summary` (teacher) — counts + average score

### Frontend (Teacher)

- **Task view integration**
  - File: [TaskView.jsx](file:///C:/Users/rohit/Documents/PYTHON/Task_Scheduling_Agent_V2/frontend-web/src/pages/TaskView.jsx)
  - Features:
    - Per-submission status badge (AI pending/running/completed/failed)
    - “Evaluate” per submission
    - “Evaluate All” for the task
    - Results panel (score, tests, word count, feedback, error)
    - Automatic polling while any evaluation is pending/running

---

## Security Enhancements (Implemented vs Planned)

### Implemented

- Python subprocess execution uses isolated mode (`python -I`) and runs in a temporary directory.
- Output caps (stdout/stderr) for all subprocess runners to prevent memory exhaustion.
- Best-effort OS-aware resource limiting: enforced on POSIX when available; timeouts/output caps always apply.
- Optional security blocking mode based on simple static checks (`security_mode: block`).

### Planned (Recommended)

- Strong sandboxing (network namespace, read-only FS, seccomp/AppArmor) requires containers/OS controls and may not be feasible on all hosts.
- If Docker becomes available in a controlled environment, use containerized runners with: no network, read-only FS, and CPU/memory limits.

---

## Performance Optimizations (Implemented vs Planned)

### Implemented

- DB-level aggregation for evaluation summaries via Mongo pipeline.
- Frontend polling only activates when there are pending/running evaluations.

### Planned

- Server-side evaluation worker queue to control concurrency under load
- Batch evaluation throttling and progress tracking per task

---

## Testing & Verification

### Verified commands

- Backend: `python -m pytest`
- Frontend: `npm run lint`, `npm run build`

Latest verification is recorded in the Change Log entry above.

---

## Planned Improvements (Backlog)

### Code evaluation

- Strengthen isolation for non-Docker hosts (separate user, tighter filesystem permissions, restricted syscalls where possible).
- Add Docker-based runners if deployment policy permits (optional).

### Document analysis

- Add readability metrics
- Add a basic plagiarism detection framework for within-task similarity checks
- Improve PDF extraction reliability and error reporting

### Workflow and maintainability

- Add a teacher-configurable evaluation configuration to task create/update UI
- Add optional “re-evaluate” semantics (force flag) for batch evaluation
- Add structured logging for evaluation lifecycle events

