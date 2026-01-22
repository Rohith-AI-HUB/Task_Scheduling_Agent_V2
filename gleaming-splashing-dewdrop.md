# Task Scheduling Agent V2 - Complete Plan

## Overview

This document covers:
- **Part A**: Deployment configuration (Render + College Server + Vercel + PWA)
- **Part B**: All implemented features with flows
- **Part C**: Groq AI integration plan with preprocessing strategies

---

# Part A: Deployment Plan

## Deployment Targets

| Target | Platform | Status |
|--------|----------|--------|
| Backend (Primary) | Render.com | To deploy |
| Backend (Secondary) | College Server (no containers) | To deploy |
| Frontend Web | Vercel | To deploy |
| Frontend Mobile | PWA (Progressive Web App) | To implement |
| Database | MongoDB Atlas | Already configured |
| AI | Groq API | To integrate |

## Files to Create

### Backend (Render)
| File | Purpose |
|------|---------|
| `backend/render.yaml` | Render blueprint |
| `backend/Procfile` | Gunicorn startup |
| `backend/runtime.txt` | Python 3.11 |

### Backend (College Server)
| File | Purpose |
|------|---------|
| `deployment/college-server/install.sh` | Setup script |
| `deployment/college-server/taskagent.service` | Systemd service |
| `deployment/college-server/nginx.conf` | Reverse proxy |

### Frontend (Vercel + PWA)
| File | Purpose |
|------|---------|
| `frontend-web/vercel.json` | Vercel config |
| `frontend-web/public/manifest.json` | PWA manifest |
| `frontend-web/public/sw.js` | Service worker |

### Documentation
| File | Purpose |
|------|---------|
| `docs/DEPLOYMENT.md` | Full deployment guide |

---

# Part B: Implemented Features

## Feature Summary

| # | Feature | Status | Groq Integration |
|---|---------|--------|------------------|
| 1 | Authentication | ✅ Done | None |
| 2 | Subject Management | ✅ Done | None |
| 3 | Task Management | ✅ Done | None |
| 4 | Group Creation | ✅ Done | None (keep rule-based) |
| 5 | Submission Handling | ✅ Done | None |
| 6 | Code Evaluation | ✅ Done | **Add Groq feedback** |
| 7 | Document Evaluation | ✅ Done | **Add Groq analysis** |
| 8 | Teacher Grading | ✅ Done | None |
| 9 | AI Task Scheduler | ✅ Done | **Add Groq explanations** |
| 10 | Dashboard | ✅ Done | Via scheduler |
| 11 | Chat Assistant | ❌ Stub | **Full Groq implementation** |

---

# Part C: Groq Integration Plan

## Integration Strategy

**Goal**: Reduce Groq API stress through preprocessing

**Approach**:
1. Run all rule-based logic FIRST (tests, metrics, formulas)
2. Collect structured data from step 1
3. Send minimal, focused prompt to Groq
4. Cache responses where applicable
5. Use fallback messages if Groq fails

---

## FEATURE 6: Code Evaluation + Groq Feedback

### Current Flow
```
Submit → Run tests → Compare outputs → Template feedback
```

### New Flow with Groq
```
Submit → Run tests → Compare outputs → PREPROCESS → Groq → Rich feedback
```

### Preprocessing (Before Groq Call)
```python
preprocessed_data = {
    "code_snippet": submission.content[:2000],  # Truncate long code
    "language": task.evaluation_config.code.language,
    "test_results": [
        {
            "test_number": 1,
            "passed": False,
            "input": "5",
            "expected": "25",
            "actual": "10",
            "error": None
        }
    ],
    "passed_count": 3,
    "total_count": 5,
    "security_issues": ["Uses eval()"],  # If any detected
    "task_description": task.description[:500]
}
```

### Groq Prompt Template
```
You are a coding instructor providing feedback on student code.

TASK: {task_description}
LANGUAGE: {language}
CODE:
```{language}
{code_snippet}
```

TEST RESULTS:
- Passed: {passed_count}/{total_count}
{test_results_formatted}

SECURITY ISSUES: {security_issues}

Provide constructive feedback in 2-3 paragraphs:
1. What the student did well
2. Why specific tests failed (be specific about the logic error)
3. One concrete suggestion for improvement

Keep response under 300 words. Be encouraging but specific.
```

### Fallback (If Groq Fails)
```python
fallback_feedback = f"Passed {passed}/{total} test cases. "
if security_issues:
    fallback_feedback += f"Security warning: {issues}. "
fallback_feedback += "Review failed test cases and check your logic."
```

### Files to Modify
| File | Changes |
|------|---------|
| `backend/app/ai/evaluator/report_gen.py` | Add Groq feedback generation |
| `backend/app/services/groq_service.py` | Create/update Groq client wrapper |
| `backend/app/services/submission_service.py` | Call Groq after test execution |

---

## FEATURE 7: Document Evaluation + Groq Analysis

### Current Flow
```
Submit → Count words → Find keywords → Readability score → Basic metrics
```

### New Flow with Groq
```
Submit → Count words → Find keywords → Readability → PREPROCESS → Groq → Deep analysis
```

### Preprocessing (Before Groq Call)
```python
preprocessed_data = {
    "content_preview": submission.content[:3000],  # First 3000 chars
    "word_count": 750,
    "required_keywords": ["algorithm", "complexity", "optimization"],
    "found_keywords": ["algorithm", "complexity"],
    "missing_keywords": ["optimization"],
    "readability": {
        "flesch_score": 65.2,
        "grade_level": 8.5
    },
    "task_requirements": {
        "title": task.title,
        "description": task.description[:500],
        "min_words": 500
    }
}
```

### Groq Prompt Template
```
You are an academic writing evaluator.

ASSIGNMENT: {task_title}
REQUIREMENTS: {task_description}
MINIMUM WORDS: {min_words}

SUBMISSION PREVIEW:
"{content_preview}"

METRICS:
- Word count: {word_count}
- Found keywords: {found_keywords}
- Missing keywords: {missing_keywords}
- Readability: Grade level {grade_level}

Evaluate this submission and provide:
1. Content quality assessment (is it on-topic, well-argued?)
2. Structure feedback (organization, flow)
3. Specific improvements needed
4. Overall quality score suggestion (0-100)

Keep response under 400 words. Be constructive and specific.
```

### Response Parsing
```python
# Extract score from Groq response
groq_response = {
    "quality_assessment": "...",
    "structure_feedback": "...",
    "improvements": ["...", "..."],
    "suggested_score": 75
}
```

### Files to Modify
| File | Changes |
|------|---------|
| `backend/app/ai/evaluator/doc_analyzer.py` | Add Groq analysis call |
| `backend/app/services/groq_service.py` | Add document analysis method |
| `backend/app/models/evaluation.py` | Add Groq feedback fields |

---

## FEATURE 9: AI Task Scheduler + Groq Explanations

### Current Flow
```
Get tasks → Calculate urgency/importance/balance → Sort by priority → Return list
```

### New Flow with Groq
```
Get tasks → Calculate priority (rule-based) → PREPROCESS → Groq → Add explanations
```

### Key Decision
- **Keep rule-based ranking** (fast, consistent, no API cost per request)
- **Add Groq explanations** (why this ranking makes sense)

### Preprocessing (Before Groq Call)
```python
preprocessed_data = {
    "student_context": {
        "workload_preference": "balanced",
        "pending_tasks": 5,
        "overdue_tasks": 1
    },
    "top_tasks": [
        {
            "title": "Data Structures Assignment",
            "subject": "CS201",
            "deadline": "2024-01-25",
            "days_remaining": 2,
            "points": 100,
            "priority_score": 0.92,
            "band": "urgent"
        },
        {
            "title": "Essay Draft",
            "subject": "ENG101",
            "deadline": "2024-01-30",
            "days_remaining": 7,
            "points": 50,
            "priority_score": 0.65,
            "band": "high"
        }
    ]
}
```

### Groq Prompt Template
```
You are a study advisor helping a student prioritize tasks.

STUDENT WORKLOAD: {workload_preference} preference, {pending_tasks} pending, {overdue_tasks} overdue

PRIORITIZED TASKS (already ranked by urgency and importance):
{tasks_formatted}

For each task, provide a brief 1-sentence explanation of why it's ranked at this priority level. Consider:
- Deadline proximity
- Point value
- Student's current workload

Format as:
1. {task_title}: {explanation}
2. {task_title}: {explanation}
...

Keep explanations concise and actionable.
```

### Caching Strategy
- Cache explanations for 1 hour (tasks don't change that often)
- Invalidate cache when:
  - Student submits a task
  - New task is created
  - Deadline passes

### Files to Modify
| File | Changes |
|------|---------|
| `backend/app/ai/task_scheduler.py` | Add Groq explanation generation |
| `backend/app/models/ai.py` | Add explanation field to ScheduledTask |
| `backend/app/services/groq_service.py` | Add scheduler explanation method |
| `backend/app/api/ai.py` | Return explanations in response |

---

## FEATURE 11: Chat Assistant (New Implementation)

### Scope
**Task-focused assistant** that can:
- Answer questions about tasks, deadlines, submissions
- Explain evaluation results
- Help with scheduling queries
- NOT: General tutoring, content explanation, homework help

### Architecture
```
User message → Intent Classification (rule-based) → Context Gathering → Groq → Response
```

### Intent Categories (Rule-Based Classification)
```python
INTENTS = {
    "task_info": ["what", "when", "due", "deadline", "assignment"],
    "submission_status": ["submitted", "grade", "score", "feedback", "evaluation"],
    "schedule_help": ["priority", "first", "start", "order", "plan"],
    "general_query": ["help", "how", "explain"]
}
```

### Preprocessing Pipeline
```python
def preprocess_chat(user_message, user_uid):
    # 1. Classify intent
    intent = classify_intent(user_message)

    # 2. Gather relevant context based on intent
    context = {}

    if intent == "task_info":
        context["tasks"] = get_user_tasks(user_uid, limit=10)
        context["upcoming_deadlines"] = get_due_soon(user_uid, days=7)

    elif intent == "submission_status":
        context["recent_submissions"] = get_recent_submissions(user_uid, limit=5)
        context["pending_evaluations"] = get_pending_evaluations(user_uid)

    elif intent == "schedule_help":
        context["schedule"] = get_ai_schedule(user_uid, limit=5)
        context["workload"] = get_workload(user_uid)

    # 3. Build minimal context for Groq
    return {
        "intent": intent,
        "user_message": user_message,
        "context": context
    }
```

### Groq Prompt Template
```
You are a task management assistant for students. You help with:
- Task information and deadlines
- Submission status and grades
- Scheduling and prioritization

You do NOT help with:
- Course content or homework answers
- General tutoring
- Topics unrelated to task management

STUDENT CONTEXT:
{context_formatted}

STUDENT QUESTION: {user_message}

Provide a helpful, concise response. If the question is outside your scope, politely redirect to task-related queries.

Keep response under 200 words.
```

### API Endpoints (New)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ai/chat` | POST | Send message, get response |
| `/api/ai/chat/history` | GET | Get conversation history |
| `/api/ai/chat/clear` | DELETE | Clear conversation |

### Request/Response Models
```python
# Request
class ChatRequest(BaseModel):
    message: str  # Max 500 chars

# Response
class ChatResponse(BaseModel):
    response: str
    intent: str
    context_used: List[str]  # ["tasks", "submissions", etc.]
    timestamp: datetime
```

### Credit System (Chat Only)

**Daily Credits:**
| Role | Credits/Day | Reset Time |
|------|-------------|------------|
| Student | 25 messages | Midnight UTC |
| Teacher | 50 messages | Midnight UTC |

**Database Schema:**
```python
# Collection: ai_credits
{
    "user_uid": str,
    "role": "student" | "teacher",
    "credits_used": int,
    "credits_limit": int,  # 25 or 50
    "last_reset": datetime,
    "created_at": datetime,
    "updated_at": datetime
}
```

**Credit Check Flow:**
```
User sends message → Check credits remaining
  → If credits > 0: Process message, decrement credits
  → If credits = 0: Return "Daily limit reached" message
```

**API Endpoints for Credits:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ai/credits` | GET | Get remaining credits |
| `/api/ai/credits/reset` | POST | Admin: Manual reset (admin only) |

**Frontend Display:**
- Show "X/25 messages remaining today" in chat UI
- Warning at 5 credits remaining
- Disable input when 0 credits

**Credit Response Model:**
```python
class CreditStatus(BaseModel):
    credits_remaining: int
    credits_limit: int
    resets_at: datetime  # Next midnight UTC
```

### Rate Limiting (Per-Minute)
- Max 10 messages per minute per user (burst protection)
- Cooldown message if exceeded

### Files to Create/Modify
| File | Changes |
|------|---------|
| `backend/app/api/ai.py` | Add chat + credits endpoints |
| `backend/app/services/chat_service.py` | New: Chat logic |
| `backend/app/services/credit_service.py` | New: Credit management |
| `backend/app/ai/intent_classifier.py` | New: Intent detection |
| `backend/app/models/chat.py` | New: Chat + Credit models |
| `frontend-web/src/components/ChatAssistant.jsx` | New: Chat UI with credit display |
| `frontend-web/src/services/aiService.js` | Add chat + credits API calls |

---

## Groq Service Architecture

### Centralized Groq Client
```python
# backend/app/services/groq_service.py

class GroqService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.1-70b-versatile"  # or mixtral-8x7b

    async def generate_code_feedback(self, preprocessed_data: dict) -> str:
        """Generate feedback for code evaluation"""

    async def analyze_document(self, preprocessed_data: dict) -> dict:
        """Analyze document submission"""

    async def explain_schedule(self, preprocessed_data: dict) -> List[str]:
        """Generate task priority explanations"""

    async def chat_response(self, preprocessed_data: dict) -> str:
        """Generate chat response"""
```

### Error Handling
```python
async def safe_groq_call(self, prompt: str, fallback: str) -> str:
    try:
        response = await self.client.chat.completions.create(...)
        return response.choices[0].message.content
    except GroqAPIError as e:
        logger.error(f"Groq API error: {e}")
        return fallback
    except asyncio.TimeoutError:
        logger.error("Groq timeout")
        return fallback
```

### Rate Limiting (Application Level)
```python
# Per-user rate limiting
GROQ_LIMITS = {
    "code_feedback": {"max": 20, "window": 3600},  # 20/hour
    "doc_analysis": {"max": 20, "window": 3600},   # 20/hour
    "schedule": {"max": 60, "window": 3600},       # 60/hour (cached)
    "chat": {"max": 100, "window": 3600}           # 100/hour
}
```

---

## Implementation Checklist

### Phase 1: Deployment Setup
- [ ] Create `backend/render.yaml`
- [ ] Create `backend/Procfile`
- [ ] Create `backend/runtime.txt`
- [ ] Create `deployment/college-server/install.sh`
- [ ] Create `deployment/college-server/taskagent.service`
- [ ] Create `deployment/college-server/nginx.conf`
- [ ] Create `frontend-web/vercel.json`
- [ ] Create `frontend-web/public/manifest.json`
- [ ] Create `frontend-web/public/sw.js`
- [ ] Update `docs/DEPLOYMENT.md`

### Phase 2: Groq Service Foundation
- [ ] Create/update `backend/app/services/groq_service.py`
- [ ] Add rate limiting utilities
- [ ] Add caching layer (Redis or in-memory)
- [ ] Add error handling and fallbacks
- [ ] Add Groq configuration to settings

### Phase 3: Code Evaluation + Groq
- [ ] Update `backend/app/ai/evaluator/report_gen.py`
- [ ] Add preprocessing function
- [ ] Integrate Groq feedback generation
- [ ] Add fallback messages
- [ ] Test with various code submissions

### Phase 4: Document Analysis + Groq
- [ ] Update `backend/app/ai/evaluator/doc_analyzer.py`
- [ ] Add content analysis preprocessing
- [ ] Integrate Groq analysis
- [ ] Parse and store Groq suggestions
- [ ] Test with various document types

### Phase 5: Task Scheduler + Groq Explanations
- [ ] Update `backend/app/ai/task_scheduler.py`
- [ ] Add explanation generation
- [ ] Implement caching for explanations
- [ ] Update API response model
- [ ] Update frontend to display explanations

### Phase 6: Chat Assistant + Credit System (New)
- [ ] Create `backend/app/services/chat_service.py`
- [ ] Create `backend/app/services/credit_service.py`
- [ ] Create `backend/app/ai/intent_classifier.py`
- [ ] Create `backend/app/models/chat.py` (includes CreditStatus model)
- [ ] Add chat + credits endpoints to `backend/app/api/ai.py`
- [ ] Create `frontend-web/src/components/ChatAssistant.jsx` (with credit display)
- [ ] Update `frontend-web/src/services/aiService.js`
- [ ] Add chat UI to dashboard
- [ ] Create `ai_credits` collection index in MongoDB

### Phase 7: Testing & Documentation
- [ ] Test all Groq integrations
- [ ] Test rate limiting
- [ ] Test fallback behavior
- [ ] Update API documentation
- [ ] Update README

---

## API Cost Estimation

### Per-Feature Groq Calls
| Feature | Calls/Action | Tokens (est.) | When Called |
|---------|--------------|---------------|-------------|
| Code Feedback | 1 | ~500 | After evaluation |
| Doc Analysis | 1 | ~800 | After evaluation |
| Schedule Explain | 1 | ~400 | Dashboard load (cached 1hr) |
| Chat | 1 | ~300 | Each message |

### Daily Estimate (100 active students)
- Evaluations: ~50/day × 2 features = 100 calls
- Schedule: ~100 loads / 10 cache hits = 10 calls
- Chat: ~200 messages/day = 200 calls
- **Total: ~310 calls/day**

---

## Summary

### What Changes

1. **Code Evaluation**: Add Groq feedback after test execution
2. **Document Analysis**: Add Groq content analysis after metrics
3. **Task Scheduler**: Add Groq explanations (keep rule-based ranking)
4. **Chat Assistant**: Build new feature with task-focused scope

### Preprocessing Strategy

All Groq calls follow this pattern:
```
Rule-based processing → Structured data extraction → Minimal Groq prompt → Response parsing → Fallback if needed
```

### Files Summary

**New Files:**
- `backend/app/services/groq_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/credit_service.py`
- `backend/app/ai/intent_classifier.py`
- `backend/app/models/chat.py`
- `frontend-web/src/components/ChatAssistant.jsx`
- Deployment configs (render.yaml, Procfile, etc.)

**New Database Collection:**
- `ai_credits` - Track daily message credits per user

**Modified Files:**
- `backend/app/ai/evaluator/report_gen.py`
- `backend/app/ai/evaluator/doc_analyzer.py`
- `backend/app/ai/task_scheduler.py`
- `backend/app/api/ai.py`
- `backend/app/models/ai.py`
- `frontend-web/src/services/aiService.js`
