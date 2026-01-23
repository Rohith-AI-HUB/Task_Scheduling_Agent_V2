# Task Scheduling Agent V2 - API Documentation

## Table of Contents
- [Authentication](#authentication)
- [Extension Requests](#extension-requests)
- [AI Chat Assistant](#ai-chat-assistant)
- [AI Credits](#ai-credits)
- [AI Task Scheduler](#ai-task-scheduler)
- [AI Context Management](#ai-context-management)

---

## Authentication

All API endpoints require authentication via Firebase ID token.

**Headers:**
```
Authorization: Bearer <firebase-id-token>
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Insufficient permissions

---

## Extension Requests

### Create Extension Request

Request a deadline extension for a task (Student only).

**Endpoint:** `POST /api/extensions`

**Request Body:**
```json
{
  "task_id": "507f1f77bcf86cd799439011",
  "requested_deadline": "2024-02-15T23:59:59Z",
  "reason": "I have three exams scheduled in the same week and need additional time to complete this assignment with the quality it deserves."
}
```

**Field Constraints:**
- `task_id` (required): Valid task ID
- `requested_deadline` (required): Datetime (must be after current deadline)
- `reason` (required): String, 10-1000 characters

**Response (201 Created):**
```json
{
  "id": "507f1f77bcf86cd799439012",
  "student_uid": "student123",
  "student_name": "John Doe",
  "task_id": "507f1f77bcf86cd799439011",
  "task_title": "Data Structures Assignment",
  "subject_id": "507f1f77bcf86cd799439010",
  "subject_name": "CS201",
  "current_deadline": "2024-02-10T23:59:59Z",
  "requested_deadline": "2024-02-15T23:59:59Z",
  "extension_days": 5,
  "reason": "I have three exams...",
  "status": "pending",
  "ai_analysis": {
    "workload_score": 0.75,
    "recommendation": "approve",
    "reasoning": "Student has legitimate workload concerns with 3 exams scheduled. Current workload shows 8 pending tasks with 2 overdue. Submission history shows consistent on-time submissions. Recommendation: Approve with suggested 3-day extension.",
    "current_workload": {
      "pending_tasks": 8,
      "overdue_tasks": 2,
      "upcoming_count": 5,
      "recent_submissions": 3,
      "total_points_at_stake": 450
    },
    "risk_factors": ["2 overdue tasks"],
    "suggested_extension_days": 3
  },
  "teacher_response": null,
  "reviewed_by": null,
  "created_at": "2024-01-23T10:30:00Z",
  "updated_at": "2024-01-23T10:30:00Z",
  "reviewed_at": null
}
```

**AI Analysis Fields:**
- `workload_score`: 0-1 score indicating workload intensity (1 = heavy)
- `recommendation`: AI recommendation (approve, deny, partial)
- `reasoning`: Detailed explanation of recommendation
- `risk_factors`: Identified concerns
- `suggested_extension_days`: AI-suggested extension duration

**Error Responses:**
- `400 Bad Request`: Invalid request (deadline before current, duplicate request)
- `403 Forbidden`: Only students can request extensions
- `404 Not Found`: Task not found

---

### List Extension Requests

Get extension requests (filtered by role).

**Endpoint:** `GET /api/extensions`

**Query Parameters:**
- `status` (optional): Filter by status (pending, approved, denied)
- `limit` (optional): Max results (default: 50)

**Behavior:**
- **Students**: See only their own requests
- **Teachers**: See requests for their subjects

**Response (200 OK):**
```json
{
  "items": [...],
  "total": 15,
  "pending_count": 5,
  "approved_count": 8,
  "denied_count": 2
}
```

---

### Get Extension by ID

Get a specific extension request.

**Endpoint:** `GET /api/extensions/{extension_id}`

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439012",
  ...
}
```

**Error Responses:**
- `403 Forbidden`: Not authorized to view this extension
- `404 Not Found`: Extension not found

---

### Approve Extension Request

Approve an extension request (Teacher only).

**Endpoint:** `PATCH /api/extensions/{extension_id}/approve`

**Request Body:**
```json
{
  "response": "Approved due to documented workload concerns",
  "approved_deadline": "2024-02-13T23:59:59Z"
}
```

**Request Fields (all optional):**
- `response`: Teacher's notes (max 500 chars)
- `approved_deadline`: Custom approved deadline (defaults to requested_deadline)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Extension request approved successfully",
  "extension": {
    "id": "507f1f77bcf86cd799439012",
    ...
    "status": "approved",
    "teacher_response": "Approved due to documented workload concerns",
    "reviewed_by": "teacher456",
    "reviewed_at": "2024-01-23T14:00:00Z"
  }
}
```

**Side Effects:**
- Task deadline is updated to approved deadline
- Student is notified (future feature)

**Error Responses:**
- `400 Bad Request`: Extension not pending
- `403 Forbidden`: Only teachers can approve, or not authorized for this subject

---

### Deny Extension Request

Deny an extension request (Teacher only).

**Endpoint:** `PATCH /api/extensions/{extension_id}/deny`

**Request Body:**
```json
{
  "response": "Please manage your time more effectively"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Extension request denied",
  "extension": {
    ...
    "status": "denied"
  }
}
```

**Side Effects:**
- Task deadline remains unchanged
- Student is notified (future feature)

---

### Get Extension Statistics

Get extension statistics for teacher's subjects (Teacher only).

**Endpoint:** `GET /api/extensions/stats`

**Response (200 OK):**
```json
{
  "total_requests": 50,
  "pending_requests": 5,
  "approved_requests": 35,
  "denied_requests": 10,
  "approval_rate": 77.8,
  "average_extension_days": 3.5
}
```

---

## AI Chat Assistant

### Send Chat Message

Send a message to the AI assistant and get a contextual response.

**Endpoint:** `POST /api/ai/chat`

**Request Body:**
```json
{
  "message": "What tasks are due this week?"
}
```

**Field Constraints:**
- `message` (required): String, max 500 characters

**Response (200 OK):**
```json
{
  "response": "You have 3 tasks due this week: Data Structures Assignment (due Jan 25), Essay Draft (due Jan 30), and Lab Report (due Jan 28).",
  "intent": "task_info",
  "context_used": ["tasks", "upcoming_deadlines"],
  "timestamp": "2024-01-23T10:30:00Z"
}
```

**Response Fields:**
- `response`: AI-generated reply to the user's message
- `intent`: Classified intent of the message
  - `task_info`: Questions about tasks and deadlines
  - `submission_status`: Questions about submissions and grades
  - `schedule_help`: Questions about scheduling and prioritization
  - `general_query`: General help questions
  - `greeting`: Greeting messages
  - `out_of_scope`: Non task-management queries
- `context_used`: List of data sources used to generate response
- `timestamp`: Response generation time (ISO 8601)

**Error Responses:**
- `400 Bad Request`: Invalid message format or exceeds length limit
- `429 Too Many Requests`: Rate limit exceeded (max 10 messages/minute)
- `402 Payment Required`: Daily credit limit reached
  ```json
  {
    "detail": "Daily message limit reached. Credits reset at midnight UTC.",
    "credits_remaining": 0,
    "credits_limit": 25,
    "resets_at": "2024-01-24T00:00:00Z"
  }
  ```

---

### Get Chat History

Retrieve conversation history for the current user.

**Endpoint:** `GET /api/ai/chat/history`

**Response (200 OK):**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What tasks are due this week?",
      "timestamp": "2024-01-23T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "You have 3 tasks due this week...",
      "timestamp": "2024-01-23T10:30:05Z",
      "intent": "task_info",
      "context_used": ["tasks"]
    }
  ],
  "total_messages": 2
}
```

**Response Fields:**
- `messages`: Array of conversation messages
  - `role`: "user" or "assistant"
  - `content`: Message text
  - `timestamp`: Message timestamp
  - `intent`: (assistant only) Classified intent
  - `context_used`: (assistant only) Data sources used
- `total_messages`: Total number of messages in history

**Notes:**
- History is stored in-memory per session
- Limited to recent messages (configurable, default: last 50)

---

### Clear Chat History

Delete conversation history for the current user.

**Endpoint:** `DELETE /api/ai/chat/clear`

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Chat history cleared successfully"
}
```

---

## AI Credits

### Get Credit Status

Retrieve current AI credit balance for the user.

**Endpoint:** `GET /api/ai/credits`

**Response (200 OK):**
```json
{
  "credits_remaining": 18,
  "credits_limit": 25,
  "credits_used": 7,
  "resets_at": "2024-01-24T00:00:00Z"
}
```

**Response Fields:**
- `credits_remaining`: Number of messages remaining today
- `credits_limit`: Daily message limit based on role
  - Students: 25 messages/day
  - Teachers: 50 messages/day
- `credits_used`: Messages used today
- `resets_at`: Next reset time (midnight UTC, ISO 8601)

**Credit System:**
- Credits automatically reset at midnight UTC every day
- One message = one credit (regardless of length)
- Credits are checked before processing each chat message
- Failed or error messages don't consume credits

---

## AI Task Scheduler

### Get AI Schedule

Get AI-optimized task schedule with priority rankings.

**Endpoint:** `GET /api/ai/schedule`

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task": {
        "id": "task123",
        "title": "Data Structures Assignment",
        "subject": "CS201",
        "deadline": "2024-01-25T23:59:59Z",
        "points": 100
      },
      "priority": 0.92,
      "band": "urgent",
      "explanation": "This task is urgent due to its approaching deadline in 2 days and high point value of 100 points.",
      "urgency_score": 0.95,
      "importance_score": 0.88,
      "balance_score": 0.93
    },
    {
      "task": {
        "id": "task456",
        "title": "Essay Draft",
        "subject": "ENG101",
        "deadline": "2024-01-30T23:59:59Z",
        "points": 50
      },
      "priority": 0.65,
      "band": "high",
      "explanation": "Moderate priority with 7 days remaining, balancing with your current workload of 5 pending tasks.",
      "urgency_score": 0.60,
      "importance_score": 0.70,
      "balance_score": 0.65
    }
  ],
  "workload_analysis": {
    "total_pending": 5,
    "overdue_count": 1,
    "preference": "balanced"
  },
  "generated_at": "2024-01-23T10:30:00Z"
}
```

**Response Fields:**
- `tasks`: Array of prioritized tasks
  - `task`: Task details (id, title, subject, deadline, points)
  - `priority`: Overall priority score (0-1, higher = more urgent)
  - `band`: Priority band
    - `urgent`: Critical priority (score > 0.8)
    - `high`: High priority (score 0.6-0.8)
    - `normal`: Normal priority (score 0.4-0.6)
    - `low`: Low priority (score < 0.4)
  - `explanation`: AI-generated reasoning for this priority (if Groq enabled)
  - `urgency_score`: Time-based urgency (0-1)
  - `importance_score`: Point value importance (0-1)
  - `balance_score`: Workload balance factor (0-1)
- `workload_analysis`: Student workload context
- `generated_at`: Schedule generation timestamp

**Notes:**
- Schedule is cached for 1 hour for performance
- Cache invalidates when tasks are submitted or created
- Priority calculation uses rule-based algorithm
- Groq explanations are optional enhancements (may fallback to generic messages)

---

### Optimize Schedule

Request optimized schedule based on preferences.

**Endpoint:** `POST /api/ai/schedule/optimize`

**Request Body:**
```json
{
  "preference": "deadline_focused",
  "max_tasks": 10
}
```

**Request Fields:**
- `preference` (optional): Optimization strategy
  - `deadline_focused`: Prioritize nearest deadlines
  - `points_focused`: Prioritize high-point tasks
  - `balanced`: Balance deadlines and points (default)
- `max_tasks` (optional): Maximum tasks to return (default: 20)

**Response (200 OK):**
```json
{
  "tasks": [...],
  "optimization_applied": "deadline_focused",
  "generated_at": "2024-01-23T10:30:00Z"
}
```

---

## AI Context Management

### Get User Context

Retrieve AI context preferences for the current user.

**Endpoint:** `GET /api/ai/context`

**Response (200 OK):**
```json
{
  "user_uid": "abc123",
  "workload_preference": "balanced",
  "study_hours_per_day": 4,
  "difficulty_preference": "medium",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-23T10:30:00Z"
}
```

**Response Fields:**
- `workload_preference`: Scheduling preference (deadline_focused, points_focused, balanced)
- `study_hours_per_day`: Available study hours (1-24)
- `difficulty_preference`: Task difficulty preference (easy, medium, hard)

---

### Update User Context

Update AI context preferences.

**Endpoint:** `PATCH /api/ai/context`

**Request Body:**
```json
{
  "workload_preference": "deadline_focused",
  "study_hours_per_day": 6
}
```

**Request Fields (all optional):**
- `workload_preference`: String (deadline_focused, points_focused, balanced)
- `study_hours_per_day`: Integer (1-24)
- `difficulty_preference`: String (easy, medium, hard)

**Response (200 OK):**
```json
{
  "user_uid": "abc123",
  "workload_preference": "deadline_focused",
  "study_hours_per_day": 6,
  "difficulty_preference": "medium",
  "updated_at": "2024-01-23T10:35:00Z"
}
```

---

## Rate Limits

| Feature | Limit | Window | Error Code |
|---------|-------|--------|------------|
| Chat Messages | 10 messages | 1 minute | 429 |
| Chat Messages (Daily) | 25 (student) / 50 (teacher) | 24 hours | 402 |
| Code Feedback | 20 requests | 1 hour | 429 |
| Doc Analysis | 20 requests | 1 hour | 429 |
| Schedule | 60 requests | 1 hour | 429 |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1706011200
```

---

## Error Response Format

All errors follow this format:

```json
{
  "detail": "Error message description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-23T10:30:00Z"
}
```

**Common Error Codes:**
- `RATE_LIMIT_EXCEEDED`: Rate limit hit
- `CREDIT_LIMIT_REACHED`: Daily credit limit reached
- `INVALID_REQUEST`: Malformed request
- `GROQ_API_ERROR`: AI service error (fallback activated)
- `UNAUTHORIZED`: Authentication failed
- `FORBIDDEN`: Insufficient permissions

---

## Chat Intent Types

The AI assistant classifies messages into these intents:

| Intent | Description | Example Queries |
|--------|-------------|-----------------|
| `task_info` | Questions about tasks and deadlines | "What's due this week?", "When is the CS assignment due?" |
| `submission_status` | Questions about submissions and grades | "What's my grade?", "Did I submit the essay?" |
| `schedule_help` | Questions about scheduling | "What should I work on first?", "Prioritize my tasks" |
| `general_query` | General help questions | "How do I submit?", "Explain evaluation" |
| `greeting` | Greetings | "Hi", "Hello", "Good morning" |
| `out_of_scope` | Non task-management queries | "What's 2+2?", "Tell me a joke" |

**Out of Scope Handling:**
The assistant will politely redirect users to task-management queries when detecting out-of-scope messages.

---

## Groq Integration

Several AI features use Groq API for enhanced responses:

### Code Evaluation Feedback
- **When**: After code submission evaluation
- **Purpose**: Provide constructive feedback on code quality and test failures
- **Fallback**: Generic feedback based on test results

### Document Analysis
- **When**: After document submission
- **Purpose**: Analyze content quality, structure, and provide improvement suggestions
- **Fallback**: Basic metrics (word count, keywords, readability)

### Schedule Explanations
- **When**: Generating AI schedule
- **Purpose**: Explain why tasks are prioritized in specific order
- **Fallback**: Generic priority band labels

### Chat Responses
- **When**: User sends chat message
- **Purpose**: Context-aware responses about tasks and scheduling
- **Fallback**: Rule-based template responses

**All Groq integrations include:**
- Preprocessing to minimize token usage
- Rate limiting to prevent API abuse
- Automatic fallbacks if Groq is unavailable
- Error handling and logging

---

## Testing Endpoints

For development/testing purposes:

**Health Check:**
```
GET /health
Response: {"status": "ok"}
```

**API Root:**
```
GET /api
Response: {"message": "Task Scheduling Agent API"}
```

---

## Changelog

### Version 2.0 (2024-01)
- Added Extension Request System with AI workload analysis
- Added AI Chat Assistant with credit system
- Added AI-generated schedule explanations
- Enhanced code evaluation with Groq feedback
- Enhanced document analysis with Groq insights
- Implemented rate limiting and credit system
- Added user context management

### Version 1.0 (2023-12)
- Initial release with basic task management
- AI task scheduler (rule-based)
- Code evaluation (sandboxed execution)
- Document analysis (basic metrics)
