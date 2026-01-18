# Task Scheduling Agent V2 - Complete Implementation Plan

> **AI-Enhanced Classroom Management System**
> Production-Ready Architecture & Development Roadmap

---

## Table of Contents
1. [System Flow Architecture](#system-flow-architecture)
2. [Folder Structure](#folder-structure)
3. [Database Schema](#database-schema)
4. [API Design](#api-design)
5. [Implementation Phases](#implementation-phases)
6. [AI Components](#ai-components)
7. [Development Timeline](#development-timeline)

---

## System Flow Architecture

### High-Level System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                            │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │   Web App        │         │   Mobile App     │        │
│  │  (React+Vite)    │         │   (Flutter)      │        │
│  └────────┬─────────┘         └────────┬─────────┘        │
│           │                            │                   │
└───────────┼────────────────────────────┼───────────────────┘
            │                            │
            └────────────┬───────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Firebase Auth         │
            │  (Email + Google)      │
            └────────────┬───────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND LAYER                            │
│                                                             │
│              ┌─────────────────────┐                       │
│              │   FastAPI Server    │                       │
│              │   (Python 3.11+)    │                       │
│              └──────────┬──────────┘                       │
│                         │                                   │
│         ┌───────────────┼───────────────┐                  │
│         ▼               ▼               ▼                  │
│  ┌──────────┐   ┌────────────┐   ┌──────────┐            │
│  │   Auth   │   │  Business  │   │    AI    │            │
│  │  Module  │   │   Logic    │   │  Engine  │            │
│  └──────────┘   └────────────┘   └──────────┘            │
│                                                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │   MongoDB Database     │
                 │  (Atlas / Local)       │
                 └────────────────────────┘
```

### User Journey Flow

#### Teacher Flow
```
Login → Dashboard → Select Subject
  │
  ├─→ Create Task → [Individual/Group] → AI Grouping (optional)
  │     │
  │     └─→ Set Deadline → Publish
  │
  ├─→ View Submissions → AI-Assisted Evaluation → Manual Review → Grade
  │
  ├─→ Extension Requests → AI Workload Analysis → Approve/Reject
  │
  └─→ AI Assistant → Schedule Conflicts → Task Planning
```

#### Student Flow
```
Login → Dashboard → View All Tasks (Multi-Subject)
  │
  ├─→ AI Task Scheduler → Prioritized List → Select Task
  │     │
  │     └─→ Submit Work → Auto-Evaluation → View Results
  │
  ├─→ Request Extension → Provide Reason → Wait Approval
  │
  └─→ AI Assistant → Deadline Reminders → Task Suggestions
```

### AI Processing Flow

```
┌──────────────────────────────────────────────────────────┐
│                   AI ENGINE CORE                         │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  1. Context Manager                            │    │
│  │     - User state tracking                      │    │
│  │     - Session history                          │    │
│  │     - Workload data                            │    │
│  └───────────────────┬────────────────────────────┘    │
│                      ▼                                   │
│  ┌────────────────────────────────────────────────┐    │
│  │  2. Rule Engine                                │    │
│  │     - Intent parser                            │    │
│  │     - Command matcher                          │    │
│  │     - Clarification generator                  │    │
│  └───────────────────┬────────────────────────────┘    │
│                      ▼                                   │
│  ┌────────────────────────────────────────────────┐    │
│  │  3. Task Scheduler                             │    │
│  │     - Priority calculation                     │    │
│  │     - Deadline sorting                         │    │
│  │     - Workload balancing                       │    │
│  └───────────────────┬────────────────────────────┘    │
│                      ▼                                   │
│  ┌────────────────────────────────────────────────┐    │
│  │  4. Evaluator                                  │    │
│  │     - Code runner (sandbox)                    │    │
│  │     - Document analyzer                        │    │
│  │     - Report generator                         │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Folder Structure

### Backend Structure (Simple & Clean)

```
task-scheduling-agent/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry point
│   │   │
│   │   ├── api/                       # API Routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # Authentication endpoints
│   │   │   ├── subjects.py            # Subject management
│   │   │   ├── tasks.py               # Task CRUD
│   │   │   ├── submissions.py         # Submission handling
│   │   │   ├── groups.py              # Group management
│   │   │   ├── extensions.py          # Extension requests
│   │   │   └── ai_assistant.py        # AI chat endpoints
│   │   │
│   │   ├── models/                    # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── subject.py
│   │   │   ├── task.py
│   │   │   ├── submission.py
│   │   │   ├── group.py
│   │   │   └── context.py
│   │   │
│   │   ├── database/                  # DB connection & models
│   │   │   ├── __init__.py
│   │   │   ├── connection.py          # MongoDB connection
│   │   │   └── collections.py         # Collection references
│   │   │
│   │   ├── ai/                        # AI Engine
│   │   │   ├── __init__.py
│   │   │   ├── context_manager.py     # User context tracking
│   │   │   ├── rule_engine.py         # Intent parsing
│   │   │   ├── task_scheduler.py      # Priority algorithm
│   │   │   ├── group_maker.py         # Grouping logic
│   │   │   ├── evaluator/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── code_runner.py     # Code evaluation
│   │   │   │   ├── doc_analyzer.py    # Document analysis
│   │   │   │   └── report_gen.py      # Report generation
│   │   │   └── assistant.py           # Chat interface
│   │   │
│   │   ├── services/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── task_service.py
│   │   │   ├── submission_service.py
│   │   │   ├── group_service.py
│   │   │   └── extension_service.py
│   │   │
│   │   ├── utils/                     # Helpers
│   │   │   ├── __init__.py
│   │   │   ├── firebase_verify.py     # Token verification
│   │   │   ├── validators.py          # Data validators
│   │   │   └── helpers.py             # Common functions
│   │   │
│   │   └── config.py                  # Configuration
│   │
│   ├── tests/                         # Unit tests
│   │   ├── test_api/
│   │   ├── test_ai/
│   │   └── test_services/
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend-web/
│   ├── src/
│   │   ├── components/               # React components
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── tasks/
│   │   │   ├── submissions/
│   │   │   └── ai-assistant/
│   │   │
│   │   ├── pages/                    # Page components
│   │   │   ├── Login.jsx
│   │   │   ├── TeacherDashboard.jsx
│   │   │   ├── StudentDashboard.jsx
│   │   │   ├── SubjectView.jsx
│   │   │   └── TaskView.jsx
│   │   │
│   │   ├── services/                 # API calls
│   │   │   ├── api.js                # Axios config
│   │   │   ├── authService.js
│   │   │   ├── taskService.js
│   │   │   └── aiService.js
│   │   │
│   │   ├── hooks/                    # Custom hooks
│   │   ├── utils/                    # Helpers
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── frontend-mobile/                  # Flutter app (future)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── widgets/
│   │   └── services/
│   │
│   └── pubspec.yaml
│
├── docs/
│   ├── API.md                        # API documentation
│   ├── DATABASE.md                   # Schema docs
│   └── DEPLOYMENT.md                 # Deployment guide
│
└── README.md
```

---

## Database Schema

### Collections Design

#### 1. **users**
```javascript
{
  _id: ObjectId,
  uid: String,              // Firebase UID
  email: String,
  name: String,
  role: String,             // "teacher" | "student"
  created_at: Date,
  updated_at: Date
}
```

#### 2. **subjects**
```javascript
{
  _id: ObjectId,
  name: String,             // "Data Structures"
  code: String,             // "CS201"
  teacher_uid: String,
  created_at: Date
}
```

#### 3. **enrollments**
```javascript
{
  _id: ObjectId,
  subject_id: ObjectId,
  student_uid: String,
  enrolled_at: Date
}
```

#### 4. **tasks**
```javascript
{
  _id: ObjectId,
  subject_id: ObjectId,
  title: String,
  description: String,
  type: String,             // "individual" | "group"
  task_type: String,        // "coding" | "written" | "presentation"
  deadline: Date,
  points: Number,

  // For group tasks
  is_group: Boolean,
  problem_statements: [String],  // Multiple problems for distribution

  // Evaluation config
  evaluation_config: {
    auto_evaluate: Boolean,
    test_cases: [Object],   // For coding tasks
    keywords: [String],     // For written tasks
    min_word_count: Number
  },

  created_at: Date,
  updated_at: Date
}
```

#### 5. **groups**
```javascript
{
  _id: ObjectId,
  task_id: ObjectId,
  name: String,             // "Group A"
  members: [String],        // Array of student UIDs
  assigned_problem: String, // Problem statement assigned
  created_by: String,       // "teacher" | "ai"
  created_at: Date
}
```

#### 6. **submissions**
```javascript
{
  _id: ObjectId,
  task_id: ObjectId,
  student_uid: String,      // Or group_id for group tasks
  group_id: ObjectId,       // null for individual

  // Content
  submission_type: String,  // "file" | "text" | "code"
  file_url: String,
  code_content: String,
  text_content: String,

  // Status
  submitted_at: Date,
  status: String,           // "pending" | "evaluated" | "graded"

  // Evaluation
  ai_evaluation: {
    score: Number,
    passed_tests: Number,
    total_tests: Number,
    report: String
  },

  teacher_grade: Number,
  teacher_feedback: String,

  updated_at: Date
}
```

#### 7. **extensions**
```javascript
{
  _id: ObjectId,
  task_id: ObjectId,
  student_uid: String,      // Or group_id
  group_id: ObjectId,

  reason: String,
  requested_deadline: Date,

  status: String,           // "pending" | "approved" | "rejected"
  teacher_response: String,

  // AI analysis
  ai_analysis: {
    workload_conflict: Boolean,
    previous_extensions: Number,
    recommendation: String
  },

  created_at: Date,
  updated_at: Date
}
```

#### 8. **user_context**
```javascript
{
  _id: ObjectId,
  user_uid: String,

  // Session data
  current_subject: ObjectId,
  recent_commands: [String],

  // Preferences
  workload_preference: String,  // "heavy" | "balanced" | "light"
  reminder_frequency: String,

  // AI learning data
  task_completion_pattern: {
    average_time: Number,
    preferred_hours: [Number],  // 0-23
    peak_productivity: String
  },

  updated_at: Date
}
```

#### 9. **chat_history** (Optional)
```javascript
{
  _id: ObjectId,
  user_uid: String,
  messages: [
    {
      role: String,         // "user" | "assistant"
      content: String,
      timestamp: Date
    }
  ],
  created_at: Date
}
```

---

## API Design

### Authentication Routes

```
POST   /api/auth/register          # Create user account
POST   /api/auth/login             # Firebase token verification
GET    /api/auth/me                # Get current user
```

### Subject Routes

```
POST   /api/subjects               # Create subject (teacher)
GET    /api/subjects               # List user's subjects
GET    /api/subjects/{id}          # Get subject details
POST   /api/subjects/{id}/enroll   # Enroll student
DELETE /api/subjects/{id}/enroll   # Remove student
```

### Task Routes

```
POST   /api/tasks                  # Create task
GET    /api/tasks                  # List tasks (filtered by subject/user)
GET    /api/tasks/{id}             # Get task details
PUT    /api/tasks/{id}             # Update task
DELETE /api/tasks/{id}             # Delete task

POST   /api/tasks/{id}/groups      # AI group creation
GET    /api/tasks/{id}/groups      # List groups for task
```

### Submission Routes

```
POST   /api/submissions            # Submit work
GET    /api/submissions            # List submissions
GET    /api/submissions/{id}       # Get submission details
POST   /api/submissions/{id}/evaluate  # Trigger AI evaluation
PUT    /api/submissions/{id}/grade     # Teacher grading
```

### Extension Routes

```
POST   /api/extensions             # Request extension
GET    /api/extensions             # List extension requests
PUT    /api/extensions/{id}        # Approve/reject (teacher)
GET    /api/extensions/{id}/analysis   # AI workload analysis
```

### AI Assistant Routes

```
POST   /api/ai/chat                # Send message to AI
GET    /api/ai/schedule            # Get AI task schedule
POST   /api/ai/schedule/optimize   # Optimize schedule
GET    /api/ai/context             # Get user context
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Setup & Authentication

**Tasks**:
- [ ] Initialize FastAPI project
- [ ] Setup MongoDB connection
- [ ] Implement Firebase auth verification
- [ ] Create user registration/login endpoints
- [ ] Setup React + Vite project
- [ ] Implement login UI
- [ ] Test auth flow end-to-end

**Deliverable**: Working login system

---

### Phase 2: Core Classroom (Weeks 3-4)
**Goal**: Basic Google Classroom clone

**Tasks**:
- [ ] Subject CRUD APIs
- [ ] Enrollment system
- [ ] Task creation (individual only)
- [ ] Task listing & details
- [ ] Basic submission system
- [ ] Teacher/Student dashboards (UI)

**Deliverable**: Teachers can create tasks, students can submit

---

### Phase 3: AI Task Scheduler (Week 5)
**Goal**: AI-assisted task prioritization

**Tasks**:
- [ ] Implement task priority algorithm
- [ ] Context manager for user workload
- [ ] AI schedule endpoint
- [ ] Schedule UI component
- [ ] Test with multiple subjects/tasks

**Deliverable**: Students see AI-prioritized task list

---

### Phase 4: Group Tasks & AI Grouping (Week 6)
**Goal**: Group task support with AI distribution

**Tasks**:
- [ ] Group creation logic
- [ ] AI-based random distribution
- [ ] Multiple problem assignment
- [ ] Group submission handling
- [ ] UI for group tasks

**Deliverable**: Teachers can create AI-distributed group tasks

---

### Phase 5: AI Evaluation Engine (Week 7)
**Goal**: Automated evaluation

**Tasks**:
- [ ] Code runner (sandboxed)
- [ ] Test case execution
- [ ] Document analyzer (keyword/word count)
- [ ] Report generator
- [ ] Evaluation UI

**Deliverable**: AI can auto-evaluate submissions

---

### Phase 6: Extension System (Week 8)
**Goal**: Deadline extension with AI analysis

**Tasks**:
- [ ] Extension request API
- [ ] AI workload analyzer
- [ ] Teacher approval UI
- [ ] Extension history tracking

**Deliverable**: Extension system with AI insights

---

### Phase 7: AI Assistant (Week 9)
**Goal**: Conversational AI helper

**Tasks**:
- [ ] Rule-based intent parser
- [ ] Command execution engine
- [ ] Clarification handler
- [ ] Chat UI component
- [ ] Context persistence

**Deliverable**: Working AI chat assistant

---

### Phase 8: Polish & Testing (Week 10)
**Goal**: Production readiness

**Tasks**:
- [ ] Error handling
- [ ] Input validation
- [ ] UI/UX improvements
- [ ] Performance optimization
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

**Deliverable**: Production-ready system

---

## AI Components

### 1. Context Manager
```python
# app/ai/context_manager.py

class ContextManager:
    """Tracks user state and preferences"""

    async def get_user_context(self, user_uid: str) -> dict:
        # Fetch from user_context collection
        pass

    async def update_context(self, user_uid: str, data: dict):
        # Update context with new data
        pass

    async def get_workload(self, user_uid: str) -> dict:
        # Calculate current workload from tasks
        pass
```

### 2. Task Scheduler
```python
# app/ai/task_scheduler.py

class TaskScheduler:
    """Priority-based task scheduling"""

    def calculate_priority(self, task: dict, context: dict) -> float:
        # Factors:
        # - Time until deadline
        # - Task weight (points)
        # - Current workload
        # - User patterns
        pass

    async def generate_schedule(self, user_uid: str) -> list:
        # Return sorted task list
        pass
```

### 3. Group Maker
```python
# app/ai/group_maker.py

class GroupMaker:
    """Fair group formation and problem distribution"""

    def create_groups(self,
                     students: list,
                     group_size: int,
                     problems: list) -> list:
        # Random fair grouping
        # Problem assignment
        # Return group structure
        pass
```

### 4. Evaluator
```python
# app/ai/evaluator/code_runner.py

class CodeEvaluator:
    """Safe code execution and testing"""

    async def run_tests(self,
                       code: str,
                       test_cases: list,
                       language: str) -> dict:
        # Run in sandbox
        # Execute test cases
        # Generate report
        pass
```

### 5. Rule Engine
```python
# app/ai/rule_engine.py

class RuleEngine:
    """Intent parsing and command matching"""

    RULES = {
        r"remind.*submit.*": "create_reminder",
        r"schedule.*tasks": "show_schedule",
        r"when.*deadline.*": "query_deadline",
        # ... more rules
    }

    def parse_intent(self, user_input: str) -> dict:
        # Match against rules
        # Extract entities
        # Return intent + params
        pass
```

---

## Development Timeline

### Week-by-Week Plan

| Week | Focus | Status |
|------|-------|--------|
| 1-2  | Foundation & Auth | ⏳ Pending |
| 3-4  | Core Classroom | ⏳ Pending |
| 5    | AI Scheduler | ⏳ Pending |
| 6    | Group Tasks | ⏳ Pending |
| 7    | AI Evaluation | ⏳ Pending |
| 8    | Extensions | ⏳ Pending |
| 9    | AI Assistant | ⏳ Pending |
| 10   | Polish & Test | ⏳ Pending |

---

## Key Technical Decisions

### Why This Stack?

**FastAPI**:
- Fast, async-first
- Built-in validation
- Easy to test
- Python = easy AI logic

**MongoDB**:
- Flexible schema for evolving features
- Easy nested data handling
- Simple migration path

**Firebase Auth**:
- Industry standard
- Secure
- No custom auth vulnerabilities
- Easy role mapping

**React + Vite**:
- Fast development
- Modern tooling
- Large ecosystem

**Flutter** (Mobile):
- Single codebase
- Professional look
- Easy backend integration

---

## Viva Defense Points

### Questions You'll Face

**Q: Why not use ChatGPT API?**
> "Our system is self-contained and explainable. Every decision can be traced through deterministic rules. This ensures transparency, institutional compliance, and no dependency on external paid services."

**Q: Can your AI learn?**
> "The system performs data-driven adaptation, not autonomous learning. It uses historical data to refine heuristics for task scheduling and grouping, but all learning rules are predefined and auditable."

**Q: Why MongoDB over SQL?**
> "Academic workflows involve nested, evolving data structures. MongoDB's schema flexibility allows us to handle tasks, groups, extensions, and context without constant migrations."

**Q: How is evaluation fair?**
> "AI assists but doesn't replace teachers. Code evaluation uses deterministic test cases. Document analysis checks objective metrics. Final grading always requires teacher review."

---

## Success Criteria

### Minimum Viable Product (MVP)
- ✅ Teacher can create tasks
- ✅ Students can submit work
- ✅ AI schedules tasks by priority
- ✅ AI evaluates code with test cases
- ✅ Group tasks with AI distribution
- ✅ Extension system with AI analysis
- ✅ Basic AI assistant

### Stretch Goals (If Time Permits)
- 📊 Analytics dashboard
- 📱 Mobile app
- 🔔 Real-time notifications
- 📈 Performance insights
- 🎨 Advanced UI/UX

---

## Final Notes

This plan is:
- **Realistic**: Achievable in 10 weeks
- **Defensible**: Every choice is justified
- **Deployable**: Works on college servers
- **Scalable**: Can grow after submission
- **Safe**: No LLMs, no external AI APIs

**Next Immediate Step**: Begin Phase 1 - Setup FastAPI and implement authentication.

---

*Document Version: 2.0*
*Last Updated: 2026-01-18*
*Status: Ready for Implementation*

---

## Ideas Pending Implementation

- **Notifications / deadline reminders**: Show upcoming/overdue tasks + send reminders (in-app first, then email).
- **AI scheduling**: Generate a study plan from tasks + deadlines + estimated effort.
- **Attachment improvements**: Teacher can download all as ZIP + attachment preview, and cleanup on task delete.
- **AI schedule preferences UI (context controls)**: Add workload preference selector (heavy/balanced/light) + reminder frequency UI, wired to `PATCH /api/ai/context`.
- **Explainable AI (why this rank?)**: Show a per-task breakdown (Urgency/Importance/Balance) and the final score.
- **Time-to-finish & daily/weekly plan**: Let students set estimated hours per task and generate a realistic plan (today + week).
- **Filters + snooze/ignore**: Hide from AI, snooze for N days, and quick filters (Urgent/High/Normal).
- **Full schedule view**: Separate page to view all prioritized tasks, search/filter, and navigate to task details.
- **Improved urgency rules**: Better handling for no-deadline tasks and overdue tasks (cap overdue dominance).
- **Notifications hook (from AI bands)**: Use urgency/high bands to drive reminders and escalation.
