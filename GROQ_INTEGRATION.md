# Groq API Integration - Core Infrastructure

## Overview

We've successfully implemented the **Phase 1: Core Groq Infrastructure** with full quota-aware routing, guards, and caching as specified in GroqAPI.md.

---

## ✅ Completed Components

### 1. Configuration System
**File:** `backend/app/config.py`

New environment variables:
```bash
GROQ_API_KEY=your_api_key_here
GROQ_ENABLE_ROUTING=true          # Enable intelligent model routing
GROQ_ENABLE_GUARDS=true           # Enable safety guards
GROQ_ENABLE_CACHING=true          # Enable response caching
GROQ_CACHE_TTL_SECONDS=3600       # Cache TTL (1 hour default)
REDIS_URL=redis://localhost:6379  # Redis for quota tracking
REDIS_DB=0
```

### 2. Groq Client (`backend/app/ai/groq_client/client.py`)
- Async wrapper for Groq API
- Exponential backoff retry logic
- Rate limit handling
- Support for all 4 models:
  - `llama-3.1-8b-instant` (workhorse - 30 RPM, 14.4k RPD, 6k TPM)
  - `llama-4-scout-17b-16e-instruct` (complex - 30 RPM, 1k RPD, 30k TPM)
  - `llama-guard-4-12b` (output validation)
  - `llama-prompt-guard-2-86m` (prompt injection detection)

### 3. Intent Classifier (`backend/app/ai/groq_client/intent.py`)
**Rule-based classification** (zero LLM overhead):
- **Simple** → 8B model
- **Medium** → 8B model
- **Complex** → Scout model

Classification criteria:
- Test case generation: ≤3 cases = simple, ≤10 = medium, >10 = complex
- Grade feedback: code length & error complexity
- Deadline suggestions: always complex (needs reasoning)
- Hint generation: based on hint level
- Grade insights: based on submission count

### 4. Quota Tracker (`backend/app/ai/groq_client/quota_tracker.py`)
Tracks **RPM, RPD, TPM, TPD** per model:
- **Redis-first** (fast, distributed)
- **MongoDB fallback** (if Redis unavailable)
- Real-time quota checking before API calls
- Automatic quota enforcement to prevent 429 errors

### 5. Guard System (`backend/app/ai/groq_client/guards.py`)

#### Prompt Guard
- Detects prompt injection patterns
- Blocks empty/oversized prompts
- Rule-based (fast, no API calls)

#### Output Guard
- JSON validation
- Schema validation
- Content safety checks
- Configurable blocking/warning modes

### 6. Caching System (`backend/app/ai/groq_client/cache.py`)
**Hash-based caching** for 30-50% API call reduction:
- SHA256 hashing: `hash(prompt + model + params)`
- Redis-first, MongoDB fallback
- Configurable TTL (default 1 hour)
- Automatic expiration

### 7. Model Router (`backend/app/ai/groq_client/router.py`)
**Full routing pipeline:**
```
Request → Prompt Guard → Cache Check → Intent Classify → Quota Check → API Call → Output Guard → Cache Store
```

Features:
- Automatic Scout → 8B fallback on quota limits
- Force model override option
- Skip cache option
- Comprehensive error handling
- Routing statistics

### 8. API Endpoints (`backend/app/api/groq_stats.py`)

New endpoints for teachers:
```
GET  /api/groq/quota          - View quota usage for all models
GET  /api/groq/health         - Check Groq integration health
GET  /api/groq/cache/stats    - View cache statistics
POST /api/groq/cache/clear    - Clear cache (use with caution)
```

---

## 🏗️ Architecture Diagram

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Prompt Guard    │ ◄─── Blocks injection, validates input
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Cache Lookup    │ ◄─── Check for cached response
└──────┬───────────┘
       │ (cache miss)
       ▼
┌──────────────────┐
│ Intent Classify  │ ◄─── Rule-based, determines complexity
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Model Router    │ ◄─── Routes to 8B (80%) or Scout (≤15%)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Quota Check     │ ◄─── Verify RPM/RPD/TPM/TPD available
└──────┬───────────┘
       │ (quota OK)
       ▼
┌──────────────────┐
│   Groq API Call  │ ◄─── llama-3.1-8b or llama-4-scout
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Output Guard    │ ◄─── Validate JSON, check safety
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Cache Store     │ ◄─── Store for future requests
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│   Response  │
└─────────────┘
```

---

## 🚀 Usage Example

```python
from app.ai.groq_client import get_model_router, IntentType

router = get_model_router()

# Simple usage
result = await router.complete(
    prompt="Generate 3 test cases for a function that adds two numbers",
    intent_type=IntentType.TEST_CASE_GENERATION,
    context={"num_cases": 3},
    json_mode=True,
)

if result["success"]:
    print(f"Response: {result['response']}")
    print(f"Model used: {result['model_used']}")
    print(f"Cached: {result['cached']}")
    print(f"Complexity: {result['complexity']}")
else:
    print(f"Error: {result['error']}")
```

---

## 📦 Installation

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set up Redis (optional but recommended)
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis
# Ubuntu: sudo apt install redis-server
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Create MongoDB indexes (if not exists)
The quota tracker will create these automatically:
```javascript
// groq_quota_tracking collection
{ "date": 1, "model": 1 }  // Daily stats
{ "minute": 1, "model": 1 } // Per-minute stats
{ "expires_at": 1 }         // TTL index

// groq_cache collection
{ "_id": 1 }                // Cache key
{ "expires_at": 1 }         // TTL index
```

---

## 🧪 Testing

### Manual Test
```python
# Test basic client
from app.ai.groq_client import get_groq_client

client = get_groq_client()
response = await client.complete(
    prompt="Say hello in JSON format with a 'message' field",
    json_mode=True,
)
print(response)
```

### Test Quota Tracking
```python
from app.ai.groq_client import get_quota_tracker

tracker = get_quota_tracker()
quota = await tracker.get_quota("llama-3.1-8b-instant")
print(f"Current usage: {quota}")
```

### Test Caching
```python
from app.ai.groq_client import get_groq_cache

cache = get_groq_cache()
stats = await cache.get_stats()
print(f"Cache stats: {stats}")
```

### Test via API (requires auth)
```bash
# Get quota status (teacher only)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/groq/quota

# Check health
curl http://localhost:8000/api/groq/health
```

---

## 📊 Monitoring

### Quota Usage
Check `/api/groq/quota` to see:
- RPM/RPD/TPM/TPD usage per model
- Percentage of limits used
- Warnings when approaching limits

### Cache Performance
Check `/api/groq/cache/stats` to see:
- Total cached entries
- Valid vs expired entries
- Cache hit rate (track in logs)

### Logs
Watch for:
- `Cache HIT` / `Cache MISS` - caching effectiveness
- `Routed to: <model>` - routing decisions
- `Quota exceeded` - rate limit warnings
- `Falling back from Scout to 8B` - quota fallback

---

## ⚠️ Important Notes

### Scout Model (llama-4-scout-17b)
- **ONLY 1,000 requests per day** - treat as scarce resource
- Use ONLY for complex tasks requiring deep reasoning
- Routing automatically prefers 8B unless complexity demands Scout
- Monitor `/api/groq/quota` to track Scout usage

### Rate Limits
All models have **30 RPM** limit:
- Burst protection built-in via quota tracker
- Automatic retry with exponential backoff
- Scout → 8B fallback on quota exhaustion

### Caching
- Enabled by default (30-50% API call reduction expected)
- 1-hour TTL (configurable)
- Automatically invalidated on changes
- Clear cache via `/api/groq/cache/clear` if needed

### Redis vs MongoDB
- **Redis**: Faster, recommended for production
- **MongoDB**: Automatic fallback if Redis unavailable
- Both store same data (quota tracking + caching)

---

## 🔜 Next Steps

The core infrastructure is ready! Now we can build features on top:

### Phase 2: Test Case Generation (pending)
- `backend/app/ai/test_case_generator.py`
- `POST /api/tasks/{task_id}/generate-test-cases`

### Phase 3: LLM Grading (pending)
- `backend/app/ai/evaluator/llm_grader.py`
- Hybrid scoring: rule-based + LLM

### Phase 4: Additional Features (pending)
- Smart deadline analyzer
- Problem statement quality checker
- Student hint generator
- Grade distribution insights

See the full plan at: `~/.claude/plans/composed-watching-mountain.md`

---

## 🐛 Troubleshooting

### "Groq API key not configured"
- Set `GROQ_API_KEY` in `.env`
- Restart backend server

### "Redis connection failed"
- Redis not required (MongoDB fallback works)
- To use Redis: ensure Redis is running on `REDIS_URL`

### "Rate limit exceeded"
- Check quota: `GET /api/groq/quota`
- Wait for rate limit reset (RPM resets every minute, RPD at midnight UTC)
- Caching should reduce this significantly

### "Prompt blocked by guard"
- Check for injection patterns in prompt
- Review guard logs for specific reason
- Guards can be disabled via `GROQ_ENABLE_GUARDS=false` (not recommended)

---

## 📝 Summary

**✅ Completed:**
- Full quota-aware routing infrastructure
- Prompt & output guards
- Response caching (30-50% reduction)
- Quota tracking (RPM/RPD/TPM/TPD)
- Intent classification
- API endpoints for monitoring
- Comprehensive error handling
- Redis + MongoDB support

**Ready to build:**
- Test case generation
- LLM grading
- All additional AI features

The foundation is rock-solid! 🎉
