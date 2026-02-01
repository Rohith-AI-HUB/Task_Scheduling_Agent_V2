"""
Groq AI Service
Centralized service for all Groq API interactions with rate limiting and caching.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from functools import wraps

from groq import Groq, APIError, RateLimitError, APIConnectionError
from app.config import settings

logger = logging.getLogger(__name__)


class GroqServiceError(Exception):
    """Custom exception for Groq service errors"""
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class InMemoryCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[str]:
        """Get value from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() < entry["expires_at"]:
                return entry["value"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: str, ttl_seconds: int = 3600):
        """Set value in cache with TTL"""
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds)
        }

    def delete(self, key: str):
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear_expired(self):
        """Remove all expired entries"""
        now = datetime.utcnow()
        expired_keys = [k for k, v in self._cache.items() if now >= v["expires_at"]]
        for key in expired_keys:
            del self._cache[key]


class RateLimiter:
    """Token bucket rate limiter for Groq API calls"""

    def __init__(self):
        # Rate limits per feature per user (max calls per window)
        self.limits = {
            "code_feedback": {"max": 20, "window": 3600},    # 20/hour
            "code_grade": {"max": 30, "window": 3600},      # 30/hour
            "doc_analysis": {"max": 20, "window": 3600},     # 20/hour
            "doc_summary": {"max": 20, "window": 3600},      # 20/hour
            "doc_analysis_part": {"max": 60, "window": 3600},  # 60/hour
            "doc_summary_part": {"max": 60, "window": 3600},   # 60/hour
            "schedule": {"max": 60, "window": 3600},         # 60/hour (cached)
            "chat": {"max": 100, "window": 3600},            # 100/hour
            "extension_analysis": {"max": 30, "window": 3600},  # 30/hour
            "test_generation": {"max": 50, "window": 3600},   # 50/hour
            "task_extraction": {"max": 50, "window": 3600}    # 50/hour
        }
        # Track usage: {user_uid: {feature: [(timestamp, ...)]}}
        self._usage: Dict[str, Dict[str, List[datetime]]] = {}

    def check_limit(self, user_uid: str, feature: str) -> bool:
        """Check if user is within rate limit for feature"""
        if feature not in self.limits:
            return True

        limit_config = self.limits[feature]
        window_start = datetime.utcnow() - timedelta(seconds=limit_config["window"])

        # Initialize user tracking
        if user_uid not in self._usage:
            self._usage[user_uid] = {}
        if feature not in self._usage[user_uid]:
            self._usage[user_uid][feature] = []

        # Clean old entries
        self._usage[user_uid][feature] = [
            ts for ts in self._usage[user_uid][feature]
            if ts > window_start
        ]

        # Check limit
        return len(self._usage[user_uid][feature]) < limit_config["max"]

    def record_usage(self, user_uid: str, feature: str):
        """Record a usage event"""
        if user_uid not in self._usage:
            self._usage[user_uid] = {}
        if feature not in self._usage[user_uid]:
            self._usage[user_uid][feature] = []

        self._usage[user_uid][feature].append(datetime.utcnow())

    def get_remaining(self, user_uid: str, feature: str) -> int:
        """Get remaining calls for user/feature"""
        if feature not in self.limits:
            return -1  # Unlimited

        limit_config = self.limits[feature]
        window_start = datetime.utcnow() - timedelta(seconds=limit_config["window"])

        if user_uid not in self._usage or feature not in self._usage[user_uid]:
            return limit_config["max"]

        # Count recent calls
        recent_calls = len([
            ts for ts in self._usage[user_uid][feature]
            if ts > window_start
        ])

        return max(0, limit_config["max"] - recent_calls)


class RoleQuotaLimiter:
    def __init__(
        self,
        global_rpm: int,
        global_rpd: int,
        teacher_weight: int,
        student_weight: int,
        teacher_count: int,
        student_count: int,
    ):
        self._global_rpm = max(0, int(global_rpm))
        self._global_rpd = max(0, int(global_rpd))

        self._teacher_weight = max(0, int(teacher_weight))
        self._student_weight = max(0, int(student_weight))
        self._teacher_count = max(0, int(teacher_count))
        self._student_count = max(0, int(student_count))

        teacher_share = self._teacher_weight * self._teacher_count
        student_share = self._student_weight * self._student_count
        total_share = teacher_share + student_share
        if total_share <= 0:
            teacher_share = 1
            student_share = 1
            total_share = 2

        self._share = {
            "teacher": teacher_share,
            "student": student_share,
            "total": total_share,
        }

        self._limits = {
            "teacher": {
                "rpm": (self._global_rpm * teacher_share) / total_share,
                "rpd": (self._global_rpd * teacher_share) / total_share,
            },
            "student": {
                "rpm": (self._global_rpm * student_share) / total_share,
                "rpd": (self._global_rpd * student_share) / total_share,
            },
        }

        now = datetime.utcnow()
        self._buckets: Dict[str, Dict[str, float | datetime]] = {
            "teacher": {
                "minute_tokens": float(self._limits["teacher"]["rpm"]),
                "minute_last": now,
                "day_tokens": float(self._limits["teacher"]["rpd"]),
                "day_last": now,
            },
            "student": {
                "minute_tokens": float(self._limits["student"]["rpm"]),
                "minute_last": now,
                "day_tokens": float(self._limits["student"]["rpd"]),
                "day_last": now,
            },
        }

    def get_limits(self) -> Dict[str, Any]:
        teacher_per_user = (
            (self._limits["teacher"]["rpd"] / self._teacher_count) if self._teacher_count > 0 else None
        )
        student_per_user = (
            (self._limits["student"]["rpd"] / self._student_count) if self._student_count > 0 else None
        )
        return {
            "global": {"rpm": self._global_rpm, "rpd": self._global_rpd},
            "weights": {"teacher": self._teacher_weight, "student": self._student_weight},
            "counts": {"teacher": self._teacher_count, "student": self._student_count},
            "share": dict(self._share),
            "teacher": {"rpm": self._limits["teacher"]["rpm"], "rpd": self._limits["teacher"]["rpd"]},
            "student": {"rpm": self._limits["student"]["rpm"], "rpd": self._limits["student"]["rpd"]},
            "per_user_rpd": {"teacher": teacher_per_user, "student": student_per_user},
        }

    def _normalize_role(self, role: str) -> str:
        r = str(role or "").lower()
        return "teacher" if r == "teacher" else "student"

    def _refill_minute(self, role: str):
        r = self._normalize_role(role)
        capacity = float(self._limits[r]["rpm"])
        if capacity <= 0:
            return
        bucket = self._buckets[r]
        now = datetime.utcnow()
        last = bucket["minute_last"]
        elapsed = max(0.0, (now - last).total_seconds())
        refill_rate = capacity / 60.0
        bucket["minute_tokens"] = min(capacity, float(bucket["minute_tokens"]) + elapsed * refill_rate)
        bucket["minute_last"] = now

    def _refill_day(self, role: str):
        r = self._normalize_role(role)
        capacity = float(self._limits[r]["rpd"])
        if capacity <= 0:
            return
        bucket = self._buckets[r]
        now = datetime.utcnow()
        last = bucket["day_last"]
        elapsed = max(0.0, (now - last).total_seconds())
        refill_rate = capacity / 86400.0
        bucket["day_tokens"] = min(capacity, float(bucket["day_tokens"]) + elapsed * refill_rate)
        bucket["day_last"] = now

    def check_limit(self, role: str) -> bool:
        r = self._normalize_role(role)
        self._refill_minute(r)
        self._refill_day(r)
        bucket = self._buckets[r]
        return float(bucket["minute_tokens"]) >= 1.0 and float(bucket["day_tokens"]) >= 1.0

    def record_usage(self, role: str):
        r = self._normalize_role(role)
        self._refill_minute(r)
        self._refill_day(r)
        bucket = self._buckets[r]
        bucket["minute_tokens"] = max(0.0, float(bucket["minute_tokens"]) - 1.0)
        bucket["day_tokens"] = max(0.0, float(bucket["day_tokens"]) - 1.0)


class GroqService:
    """
    Centralized Groq AI service with:
    - Rate limiting per user/feature
    - Response caching
    - Error handling with fallbacks
    - Structured prompts for each feature
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.client = None
        self.grading_client = None
        self.model = settings.groq_model
        self.cache = InMemoryCache()
        self.rate_limiter = RateLimiter()
        self.role_quota_limiter = RoleQuotaLimiter(
            global_rpm=settings.groq_global_rpm,
            global_rpd=settings.groq_global_rpd,
            teacher_weight=settings.groq_teacher_weight,
            student_weight=settings.groq_student_weight,
            teacher_count=settings.groq_teacher_count,
            student_count=settings.groq_student_count,
        )
        self._initialized = True

        # Initialize Groq client if API key is available
        if settings.groq_api_key:
            try:
                self.client = Groq(api_key=settings.groq_api_key)
                logger.info("[OK] Groq client initialized successfully")
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize Groq client: {e}")
        else:
            logger.warning("[WARNING] Groq API key not configured - AI features will use fallbacks")

        # Initialize Groq grading client if API key is available
        if settings.groq_grading_api_key:
            try:
                self.grading_client = Groq(api_key=settings.groq_grading_api_key)
                logger.info("[OK] Groq grading client initialized successfully")
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize Groq grading client: {e}")

    def is_available(self) -> bool:
        """Check if Groq service is available"""
        return self.client is not None or self.grading_client is not None

    def _generate_cache_key(self, feature: str, data: dict) -> str:
        """Generate a cache key from feature and data"""
        data_str = json.dumps(data, sort_keys=True)
        hash_str = hashlib.md5(data_str.encode()).hexdigest()
        return f"groq:{feature}:{hash_str}"

    async def _call_groq(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        client: Optional[Groq] = None
    ) -> str:
        """
        Make an async call to Groq API

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity parameter (0-1)
            client: Optional Groq client instance (defaults to self.client)

        Returns:
            Response text from Groq
        """
        active_client = client or self.client
        if not active_client:
            raise GroqServiceError("Groq client not initialized")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            # Run sync client in executor for async compatibility
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: active_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            logger.warning(f"Groq rate limit hit: {e}")
            raise GroqServiceError("AI service rate limit exceeded. Please try again later.")

        except APIConnectionError as e:
            logger.error(f"Groq connection error: {e}")
            raise GroqServiceError("Unable to connect to AI service.")

        except APIError as e:
            logger.error(f"Groq API error: {e}")
            raise GroqServiceError(f"AI service error: {str(e)}")

    async def safe_call(
        self,
        feature: str,
        user_uid: str,
        prompt: str,
        role: str = "student",
        system_prompt: str = "",
        fallback: str = "Unable to generate AI response.",
        use_cache: bool = True,
        cache_ttl: int = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_grading_key: bool = False
    ) -> str:
        """
        Safe Groq call with rate limiting, caching, and fallback

        Args:
            feature: Feature name for rate limiting (code_feedback, doc_analysis, schedule, chat)
            user_uid: User ID for rate limiting
            prompt: The prompt to send
            system_prompt: System prompt
            fallback: Fallback response if Groq fails
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds (default from settings)
            max_tokens: Max response tokens
            temperature: Response creativity
            use_grading_key: Whether to use the grading API key

        Returns:
            Groq response or fallback
        """
        # Determine client to use
        client = self.grading_client if use_grading_key and self.grading_client else self.client

        # Check if Groq is available
        if not client:
            logger.debug(f"Groq client not available, using fallback for {feature}")
            return fallback

        # Check rate limit
        if not self.rate_limiter.check_limit(user_uid, feature):
            # remaining = self.rate_limiter.get_remaining(user_uid, feature)
            logger.warning(f"Rate limit exceeded for user {user_uid} on {feature}")
            raise RateLimitExceeded(
                f"Rate limit exceeded for {feature}. Please wait before trying again."
            )

        # Check cache
        if use_cache and settings.groq_enable_caching:
            cache_key = self._generate_cache_key(feature, {"prompt": prompt})
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {feature}")
                return cached_response

        try:
            if not self.role_quota_limiter.check_limit(role):
                raise RateLimitExceeded("Global Groq quota exceeded for your role. Please try again later.")

            # Make the API call
            response = await self._call_groq(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                client=client
            )

            # Record usage
            self.rate_limiter.record_usage(user_uid, feature)
            self.role_quota_limiter.record_usage(role)

            # Cache response
            if use_cache and settings.groq_enable_caching:
                ttl = cache_ttl or settings.groq_cache_ttl_seconds
                self.cache.set(cache_key, response, ttl)

            return response

        except (GroqServiceError, RateLimitExceeded):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Groq call: {e}")
            return fallback

    async def chat_response(
        self,
        user_uid: str,
        message: str,
        intent: str,
        context: Dict[str, Any],
        role: str = "student",
        history: List[Dict] = None
    ) -> str:
        """
        Generate a chat response using Groq AI.

        Args:
            user_uid: User's unique identifier
            message: User's message
            intent: Classified intent (task_info, submission_status, etc.)
            context: Relevant context data (tasks, submissions, schedule, workload)
            role: User's role (student/teacher)
            history: Recent conversation history

        Returns:
            AI-generated response string
        """
        history = history or []

        # Build system prompt based on role
        if role == "teacher":
            system_prompt = """You are a helpful AI assistant for teachers using a task scheduling and classroom management system.

Your role:
- Help teachers manage their classrooms, assignments, and student submissions
- Provide insights about pending work, upcoming deadlines, and student progress
- Answer questions about tasks, submissions, and scheduling
- Be concise, professional, and actionable

When answering:
- Reference specific tasks, subjects, and deadlines from the context provided
- Suggest next actions when appropriate
- Keep responses brief (2-3 sentences typically)
- If you don't have enough context, ask clarifying questions"""
        else:
            system_prompt = """You are a helpful AI assistant for students using a task scheduling system.

Your role:
- Help students manage their assignments and deadlines
- Provide study scheduling advice and prioritization guidance
- Answer questions about tasks, submissions, and grades
- Be encouraging, clear, and concise

When answering:
- Reference specific tasks and deadlines from the context provided
- Suggest actionable next steps when relevant
- Keep responses brief (2-3 sentences typically)
- If you don't have enough context, ask clarifying questions"""

        # Build context summary
        context_summary = self._build_context_summary(context, role)

        # Build conversation history
        history_text = ""
        if history:
            history_text = "\n\nRecent conversation:\n"
            for msg in history[-5:]:  # Last 5 messages
                history_text += f"{msg['role']}: {msg['content']}\n"

        # Build the prompt
        prompt = f"""Context about the user:
{context_summary}
{history_text}

User's question: {message}

Provide a helpful, concise response based on the context above."""

        # Call Groq API
        return await self.safe_call(
            feature="chat",
            user_uid=user_uid,
            role=role,
            prompt=prompt,
            system_prompt=system_prompt,
            fallback="I'm having trouble processing your request right now. Please try again.",
            use_cache=False,  # Don't cache chat responses
            max_tokens=500,
            temperature=0.7
        )

    def _build_context_summary(self, context: Dict[str, Any], role: str) -> str:
        """Build a text summary of the context for the LLM"""
        summary_parts = []

        # Tasks
        if "tasks" in context and context["tasks"]:
            tasks = context["tasks"][:10]  # Limit to 10 tasks
            if role == "teacher":
                summary_parts.append(f"Teacher's classroom tasks ({len(tasks)}):")
            else:
                summary_parts.append(f"Student's upcoming tasks ({len(tasks)}):")
            for task in tasks:
                summary_parts.append(f"  - {task.get('title', 'Untitled')} ({task.get('subject', 'Subject')}): due {task.get('deadline', 'No deadline')}, {task.get('points', 0)} points")

        # Submissions
        if "submissions" in context and context["submissions"]:
            submissions = context["submissions"][:5]  # Limit to 5
            if role == "teacher":
                summary_parts.append(f"\nRecent submissions ({len(submissions)}):")
                for sub in submissions:
                    status = sub.get('status', 'pending')
                    summary_parts.append(f"  - {sub.get('task_title', 'Task')}: {status}")
            else:
                summary_parts.append(f"\nRecent submissions ({len(submissions)}):")
                for sub in submissions:
                    score = sub.get('score')
                    summary_parts.append(f"  - {sub.get('task_title', 'Task')}: {'graded' if score is not None else 'pending'}" + (f" (score: {score})" if score is not None else ""))

        # Workload
        if "workload" in context:
            workload = context["workload"]
            if role == "teacher":
                ungraded = workload.get('ungraded_submissions', 0)
                classrooms = workload.get('active_classrooms', 0)
                summary_parts.append(f"\nWorkload: {ungraded} ungraded submissions across {classrooms} classrooms")
            else:
                pending = workload.get('pending', 0)
                overdue = workload.get('overdue', 0)
                due_soon = workload.get('due_soon', 0)
                summary_parts.append(f"\nWorkload: {pending} pending tasks, {overdue} overdue, {due_soon} due soon")

        # Schedule
        if "schedule" in context and context["schedule"]:
            schedule = context["schedule"][:3]  # Top 3 priorities
            summary_parts.append(f"\nPriority tasks:")
            for item in schedule:
                band = item.get('band', 'normal')
                summary_parts.append(f"  - {item.get('title', 'Task')}: {band} priority")

        if not summary_parts:
            return "No specific context available."

        return "\n".join(summary_parts)

    # ========================================
    # Feature-Specific Methods
    # ========================================

    async def generate_code_feedback(
        self,
        user_uid: str,
        code: str,
        language: str,
        test_results: List[dict],
        task_description: str,
        security_issues: List[str] = None
    ) -> str:
        """
        Generate intelligent feedback for code evaluation
        Uses the grading API key if available.
        """
        # Preprocess data
        code_snippet = code[:2000] if len(code) > 2000 else code
        passed_count = sum(1 for t in test_results if t.get("passed", False))
        total_count = len(test_results)

        # Format test results
        test_results_formatted = ""
        for i, result in enumerate(test_results[:5]):  # Limit to first 5
            status = "[PASSED]" if result.get("passed") else "[FAILED]"
            test_results_formatted += f"\nTest {i+1}: {status}"
            if not result.get("passed"):
                test_results_formatted += f"\n  Input: {result.get('input', 'N/A')[:50]}"
                test_results_formatted += f"\n  Expected: {result.get('expected', 'N/A')[:50]}"
                test_results_formatted += f"\n  Got: {result.get('actual', 'N/A')[:50]}"
                if result.get("error"):
                    test_results_formatted += f"\n  Error: {result.get('error')[:100]}"

        security_str = ", ".join(security_issues) if security_issues else "None detected"

        prompt = f"""TASK: {task_description[:500]}
LANGUAGE: {language}
CODE:
```{language}
{code_snippet}
```

TEST RESULTS:
- Passed: {passed_count}/{total_count}
{test_results_formatted}

SECURITY ISSUES: {security_str}

Provide constructive feedback in 2-3 paragraphs:
1. What the student did well
2. Why specific tests failed (be specific about the logic error)
3. One concrete suggestion for improvement

Keep response under 300 words. Be encouraging but specific."""

        system_prompt = "You are a coding instructor providing feedback on student code. Be constructive, specific, and encouraging."

        fallback = f"Passed {passed_count}/{total_count} test cases. "
        if security_issues:
            fallback += f"Security warning: {', '.join(security_issues)}. "
        fallback += "Review failed test cases and check your logic."

        return await self.safe_call(
            feature="code_feedback",
            user_uid=user_uid,
            prompt=prompt,
            system_prompt=system_prompt,
            fallback=fallback,
            use_cache=False,  # Don't cache code feedback
            max_tokens=500,
            temperature=0.7,
            use_grading_key=True
        )

    async def grade_code_submission(
        self,
        *,
        user_uid: str,
        code: str,
        language: str,
        task_title: str,
        task_description: str,
        role: str = "teacher",
    ) -> dict:
        code_snippet = (code or "")[:12000]

        prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description[:1200]}
LANGUAGE: {language}

SUBMITTED CODE:
```{language}
{code_snippet}
```

Grade this code WITHOUT executing it. Evaluate:
- apparent correctness vs the requirements (best-effort from static reading)
- code quality and clarity
- edge cases handled or missed
- structure, naming, and style

Return ONLY valid JSON in this format:
{{
  "correctness_assessment": "string",
  "quality_assessment": "string",
  "key_issues": ["issue 1", "issue 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "suggested_score": 75
}}

Rules:
- Do not invent missing requirements.
- If requirements are vague, state assumptions.
- suggested_score must be an integer 0-100."""

        fallback_response = {
            "correctness_assessment": "Unable to grade code automatically.",
            "quality_assessment": "Groq unavailable.",
            "key_issues": ["Groq unavailable"],
            "improvements": [],
            "suggested_score": 0,
            "raw_response": "Fallback - Groq unavailable",
        }

        try:
            response = await self.safe_call(
                feature="code_grade",
                user_uid=user_uid,
                role=role if role in {"teacher", "student"} else "teacher",
                prompt=prompt,
                system_prompt="You are a strict but fair programming assignment grader. Always output valid JSON only.",
                fallback=json.dumps(fallback_response),
                use_cache=True,
                cache_ttl=86400,
                max_tokens=800,
                temperature=0.0,
                use_grading_key=True,
            )

            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            parsed = json.loads(response)
            if not isinstance(parsed, dict):
                return fallback_response
            return parsed
        except Exception as e:
            logger.error(f"Error grading code submission: {e}")
            return fallback_response

    def _split_text(self, text: str, *, max_chars: int, overlap_chars: int = 0) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return [""]
        if len(raw) <= max_chars:
            return [raw]

        parts = re.split(r"\n{2,}", raw)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for p in parts:
            p = p.strip()
            if not p:
                continue
            add_len = len(p) + (2 if current else 0)
            if current and current_len + add_len > max_chars:
                chunk = "\n\n".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                current = []
                current_len = 0

                if overlap_chars > 0 and chunks:
                    tail = chunks[-1][-overlap_chars:]
                    tail = tail.strip()
                    if tail:
                        current = [tail]
                        current_len = len(tail)

            current.append(p)
            current_len += add_len

        if current:
            chunk = "\n\n".join(current).strip()
            if chunk:
                chunks.append(chunk)

        if not chunks:
            return [raw[:max_chars]]
        return chunks

    async def analyze_document(
        self,
        user_uid: str,
        content: str,
        word_count: int,
        required_keywords: List[str],
        found_keywords: List[str],
        missing_keywords: List[str],
        readability: dict,
        task_title: str,
        task_description: str,
        min_words: int = 0
    ) -> dict:
        """
        Analyze document submission with Groq
        Uses grading API key if available.
        """
        content = content or ""
        is_long = len(content) > 12000
        content_preview = content[:3000] if len(content) > 3000 else content
        content_tail = content[-2000:] if len(content) > 5000 else ""

        chunk_summaries: list[str] = []
        if is_long:
            chunks = self._split_text(content, max_chars=8500, overlap_chars=350)
            chunk_tasks: list[str] = []
            for idx, chunk in enumerate(chunks, 1):
                part_prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description[:800]}

SUBMISSION PART {idx}/{len(chunks)}:
\"\"\"{chunk}\"\"\"

Summarize this part for grading:
- Main points (bullets)
- Evidence/examples used (bullets)
- Missing/unclear items (bullets, if any)

Do not invent facts. Keep under 180 words."""

                chunk_tasks.append(
                    self.safe_call(
                        feature="doc_analysis_part",
                        user_uid=user_uid,
                        prompt=part_prompt,
                        system_prompt="You extract faithful summaries to support grading.",
                        fallback="",
                        use_cache=True,
                        cache_ttl=86400,
                        max_tokens=300,
                        temperature=0.0,
                        use_grading_key=True,
                        role="teacher",
                    )
                )
            chunk_summaries = [s for s in await asyncio.gather(*chunk_tasks) if isinstance(s, str) and s.strip()]

        tail_block = ""
        if content_tail:
            tail_block = f"""
SUBMISSION ENDING (excerpt):
\"\"\"{content_tail}\"\"\""""

        chunks_block = ""
        if chunk_summaries:
            parts_text = "\n".join([f"[Part {i + 1}] {t}" for i, t in enumerate(chunk_summaries)])
            chunks_block = f"""
CHUNKED PART SUMMARIES (covers the full submission):
{parts_text}"""

        prompt = f"""ASSIGNMENT: {task_title}
REQUIREMENTS: {task_description[:500]}
MINIMUM WORDS: {min_words}

SUBMISSION PREVIEW:
\"\"\"{content_preview}\"\"\"{tail_block}{chunks_block}

METRICS:
- Word count: {word_count}
- Found keywords: {', '.join(found_keywords) if found_keywords else 'None'}
- Missing keywords: {', '.join(missing_keywords) if missing_keywords else 'None'}
- Readability: Grade level {readability.get('grade_level', 'N/A')}

Evaluate this submission and provide your response in the following JSON format:
{{
  "quality_assessment": "Brief assessment of content quality",
  "structure_feedback": "Feedback on organization and flow",
  "improvements": ["improvement 1", "improvement 2"],
  "suggested_score": 75
}}

Be constructive and specific. The score should be 0-100."""

        system_prompt = "You are an academic writing evaluator. Always respond with valid JSON. Use the provided summaries and excerpts only."

        fallback_response = {
            "quality_assessment": "Document meets basic requirements.",
            "structure_feedback": f"Word count: {word_count}. {'Meets' if word_count >= min_words else 'Below'} minimum requirement.",
            "improvements": [
                f"Include missing keywords: {', '.join(missing_keywords)}" if missing_keywords else "Good keyword coverage"
            ],
            "suggested_score": 70 if word_count >= min_words and not missing_keywords else 50,
            "raw_response": "Fallback response - Groq unavailable"
        }

        try:
            response = await self.safe_call(
                feature="doc_analysis",
                user_uid=user_uid,
                prompt=prompt,
                system_prompt=system_prompt,
                fallback=json.dumps(fallback_response),
                use_cache=True,
                cache_ttl=86400,
                max_tokens=700,
                temperature=0.0,
                use_grading_key=True
            )
            
            # Clean up response to ensure valid JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode Groq JSON response: {response}")
            return fallback_response
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            return fallback_response

    async def summarize_document(
        self,
        *,
        user_uid: str,
        content: str,
        task_title: str,
        task_description: str,
        role: str = "teacher",
    ) -> str:
        content = content or ""
        is_long = len(content) > 12000
        content_preview = content[:9000] if len(content) > 9000 else content

        if is_long:
            chunks = self._split_text(content, max_chars=9000, overlap_chars=400)
            chunk_tasks: list[str] = []
            for idx, chunk in enumerate(chunks, 1):
                part_prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description[:800]}

SUBMISSION PART {idx}/{len(chunks)}:
\"\"\"{chunk}\"\"\"

Write a faithful summary of this part:
- Key points (bullets)
- Important technical details (bullets)
- Anything missing/unclear (bullets, if any)

Keep under 220 words."""
                chunk_tasks.append(
                    self.safe_call(
                        feature="doc_summary_part",
                        user_uid=user_uid,
                        prompt=part_prompt,
                        system_prompt="You summarize student submissions for teachers. Be faithful to the text.",
                        fallback="",
                        use_cache=True,
                        cache_ttl=86400,
                        max_tokens=350,
                        temperature=0.0,
                        use_grading_key=True,
                        role=role if role in {"teacher", "student"} else "teacher",
                    )
                )
            chunk_summaries = [s for s in await asyncio.gather(*chunk_tasks) if isinstance(s, str) and s.strip()]

            combined_prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description[:800]}

You are given summaries of all parts of the student's submission. Produce a single detailed summary for a teacher:
1) One-paragraph executive summary
2) Key points as bullets (10-16 bullets)
3) What is missing or unclear (if any)

PART SUMMARIES:
{chr(10).join([f"[Part {i+1}] {t}" for i, t in enumerate(chunk_summaries)])}

Do not invent facts. Keep it under 900 words."""

            return await self.safe_call(
                feature="doc_summary",
                user_uid=user_uid,
                prompt=combined_prompt,
                system_prompt="You summarize student submissions for teachers. Be faithful to the text.",
                fallback="",
                use_cache=True,
                cache_ttl=86400,
                max_tokens=1200,
                temperature=0.0,
                use_grading_key=True,
                role=role if role in {"teacher", "student"} else "teacher",
            )

        prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description[:800]}

SUBMISSION:
\"\"\"{content_preview}\"\"\"

Write a detailed, teacher-friendly summary with:
1) One-paragraph executive summary
2) Key points as bullets (8-12 bullets)
3) What is missing or unclear (if any)

Do not invent facts. Keep it under 700 words."""

        fallback = content_preview.strip()
        if fallback:
            words = re.findall(r"\\S+", fallback)
            fallback = " ".join(words[:300])
        else:
            fallback = "No content provided."

        return await self.safe_call(
            feature="doc_summary",
            user_uid=user_uid,
            prompt=prompt,
            system_prompt="You summarize student submissions for teachers. Be faithful to the text.",
            fallback=fallback,
            use_cache=True,
            cache_ttl=86400,
            max_tokens=900,
            temperature=0.0,
            use_grading_key=True,
            role=role if role in {"teacher", "student"} else "teacher",
        )

    async def generate_test_cases(
        self,
        user_uid: str,
        code: str,
        language: str,
        num_tests: int = 5
    ) -> List[dict]:
        """
        Auto generate test cases from code
        """
        code_snippet = code[:3000]

        prompt = f"""Generate {num_tests} test cases for the following {language} code.
The code is:
```{language}
{code_snippet}
```

Return ONLY a JSON array of objects with 'input' (string) and 'expected' (string) fields.
Example:
[
  {{"input": "2", "expected": "4"}},
  {{"input": "3", "expected": "9"}}
]

If the function takes no arguments, input can be empty string or relevant setup.
Ensure inputs cover edge cases.
"""
        system_prompt = "You are a QA engineer generating test cases. Output valid JSON only."
        
        fallback = []

        try:
            response = await self.safe_call(
                feature="test_generation",
                user_uid=user_uid,
                prompt=prompt,
                system_prompt=system_prompt,
                fallback="[]",
                use_cache=True,
                max_tokens=1000,
                temperature=0.3
            )
             # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return fallback

    async def extract_tasks_from_doc(
        self,
        user_uid: str,
        content: str
    ) -> List[dict]:
        """
        Auto create tasks from document content
        """
        content_preview = content[:4000]

        prompt = f"""Analyze the following document and extract actionable tasks.
Document content:
"{content_preview}"

Return ONLY a JSON array of task objects with the following fields:
- title: string (short summary)
- description: string (details)
- priority: "high", "medium", or "low"
- estimated_minutes: int

Example:
[
  {{"title": "Review Chapter 1", "description": "Read and summarize chapter 1", "priority": "high", "estimated_minutes": 60}}
]
"""
        system_prompt = "You are a project manager extracting tasks from documents. Output valid JSON only."
        
        fallback = []

        try:
            response = await self.safe_call(
                feature="task_extraction",
                user_uid=user_uid,
                prompt=prompt,
                system_prompt=system_prompt,
                fallback="[]",
                use_cache=True,
                max_tokens=1000,
                temperature=0.3
            )
             # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error extracting tasks: {e}")
            return fallback

    async def analyze_project_submission(
        self,
        user_uid: str,
        content: str,
        task_title: str,
        task_description: str,
        submission_type: str = "project"
    ) -> dict:
        """
        Enhanced project analysis with automatic category selection.
        Groq AI decides which analysis framework to use based on submission type.

        Available frameworks:
        - Academic: Introduction, Methodology, Results, Discussion, Conclusion
        - Technical: Problem, Solution, Implementation, Testing, Documentation
        - General Quality: Content, Structure, Clarity, Research, Formatting
        - Custom: Based on teacher's task description

        Args:
            user_uid: Student's user ID
            content: Project submission text
            task_title: Project title
            task_description: Teacher's requirements
            submission_type: Type of submission (project, assignment, extra_credit)

        Returns:
            Dict with category_scores, overall_score, feedback, and analysis_framework_used
        """
        content_preview = content[:5000] if len(content) > 5000 else content

        prompt = f"""TASK: {task_title}
REQUIREMENTS: {task_description}
SUBMISSION TYPE: {submission_type}

SUBMISSION CONTENT:
"{content_preview}"

Analyze this submission intelligently:
1. Choose the BEST analysis framework from these options:
   - ACADEMIC: For research papers (Intro, Methodology, Results, Discussion, Conclusion)
   - TECHNICAL: For engineering/coding projects (Problem, Solution, Implementation, Testing, Docs)
   - GENERAL: For essays/reports (Content, Structure, Clarity, Research, Formatting)
   - CUSTOM: Extract categories from teacher's requirements

2. Score EACH category (0-100)

3. Provide specific feedback for each category

4. Calculate overall weighted score

Respond in this EXACT JSON format:
{{
  "framework_used": "ACADEMIC | TECHNICAL | GENERAL | CUSTOM",
  "categories": {{
    "category_name_1": {{
      "score": 85,
      "feedback": "Specific feedback about this category",
      "weight": 0.25
    }},
    "category_name_2": {{
      "score": 78,
      "feedback": "Specific feedback",
      "weight": 0.20
    }}
  }},
  "overall_score": 82,
  "overall_feedback": "2-3 sentences summary",
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"]
}}

Be thorough and constructive. All scores 0-100."""

        system_prompt = """You are an expert educational evaluator with expertise in:
- Academic research assessment
- Technical project evaluation
- Writing quality analysis
- Adaptive grading frameworks

Always respond with valid JSON. Be fair, thorough, and constructive."""

        fallback_response = {
            "framework_used": "GENERAL",
            "categories": {
                "Content Quality": {"score": 70, "feedback": "Meets basic requirements", "weight": 0.40},
                "Structure": {"score": 65, "feedback": "Adequate organization", "weight": 0.30},
                "Clarity": {"score": 68, "feedback": "Generally clear", "weight": 0.30}
            },
            "overall_score": 68,
            "overall_feedback": "Submission meets basic requirements. Review for improvements.",
            "strengths": ["Submitted on time"],
            "improvements": ["Add more detail", "Improve structure"],
            "raw_response": "Fallback - Groq unavailable"
        }

        try:
            response = await self.safe_call(
                feature="doc_analysis",
                user_uid=user_uid,
                prompt=prompt,
                system_prompt=system_prompt,
                fallback=json.dumps(fallback_response),
                use_cache=False,
                max_tokens=1500,
                temperature=0.4,
                use_grading_key=True
            )

            # Clean up response to ensure valid JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            result = json.loads(response)
            result["raw_response"] = response
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Groq JSON response for project analysis: {e}")
            logger.error(f"Response was: {response}")
            return fallback_response
        except Exception as e:
            logger.error(f"Error in project analysis: {e}")
            return fallback_response

    async def generate_quiz_questions(
        self,
        user_uid: str,
        document_content: str,
        topic: str,
        num_questions: int = 10
    ) -> List[dict]:
        """
        Generate multiple-choice quiz questions from a document and topic.

        Args:
            user_uid: Teacher's user ID
            document_content: Source material (textbook content, etc.)
            topic: Specific topic/chapter to focus on
            num_questions: Number of questions to generate (5-50)

        Returns:
            List of question objects with format:
            {
                "question": "What is...?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,  # Index of correct option (0-3)
                "explanation": "Brief explanation of correct answer"
            }
        """
        content_preview = document_content[:8000] if len(document_content) > 8000 else document_content
        target_count = max(5, min(50, num_questions))

        system_prompt = """You are an expert educational assessment designer.
Create high-quality multiple-choice questions that:
- Test comprehension and application, not just recall
- Have clear, unambiguous correct answers
- Include plausible distractors
- Are appropriately challenging
Return ONLY a valid JSON array. No markdown, no prose."""

        def clean_json_array(text: str) -> str:
            t = (text or "").strip()
            if t.startswith("```json"):
                t = t[7:]
            if t.startswith("```"):
                t = t[3:]
            if t.endswith("```"):
                t = t[:-3]
            t = t.strip()
            start = t.find("[")
            end = t.rfind("]")
            if start != -1 and end != -1 and end > start:
                return t[start : end + 1].strip()
            return t

        def is_valid_question(q: Any) -> bool:
            return (
                isinstance(q, dict)
                and isinstance(q.get("question"), str)
                and isinstance(q.get("options"), list)
                and len(q.get("options")) == 4
                and all(isinstance(opt, str) for opt in q.get("options"))
                and isinstance(q.get("correct_answer"), int)
                and 0 <= q.get("correct_answer") <= 3
            )

        async def run_batch(batch_size: int, avoid: list[str]) -> list[dict]:
            avoid_block = ""
            if avoid:
                avoid_trimmed = [a.strip() for a in avoid if isinstance(a, str) and a.strip()]
                avoid_trimmed = avoid_trimmed[-30:]
                if avoid_trimmed:
                    avoid_block = "\n\nDo NOT repeat or paraphrase these questions:\n" + "\n".join(
                        f"- {q}" for q in avoid_trimmed
                    )

            prompt = f"""Generate {batch_size} multiple-choice questions from the following educational content.

TOPIC: {topic}

SOURCE MATERIAL:
\"{content_preview}\"

Requirements:
1. Each question must have EXACTLY 4 answer choices (A, B, C, D)
2. Only ONE answer is correct
3. Questions should test understanding, not just memorization
4. Vary difficulty levels (easy, medium, hard)
5. Make incorrect options plausible but clearly wrong
6. Cover different aspects of the topic
7. All questions must be unique (no rephrases)
8. Return ONLY a JSON array of EXACTLY {batch_size} objects (no extra keys, no markdown){avoid_block}

JSON schema (array):
[
  {{
    "question": "…",
    "options": ["…", "…", "…", "…"],
    "correct_answer": 0,
    "explanation": "…",
    "difficulty": "easy|medium|hard"
  }}
]"""

            role = "teacher"
            if not self.rate_limiter.check_limit(user_uid, "test_generation"):
                raise RateLimitExceeded("Rate limit exceeded for quiz generation. Please try again later.")
            if not self.role_quota_limiter.check_limit(role):
                raise RateLimitExceeded("Global Groq quota exceeded for your role. Please try again later.")

            response = await self._call_groq(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=3000,
                temperature=0.4,
                client=client,
            )
            self.rate_limiter.record_usage(user_uid, "test_generation")
            self.role_quota_limiter.record_usage(role)

            cleaned = clean_json_array(response)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                response2 = await self._call_groq(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=3000,
                    temperature=0.2,
                    client=client,
                )
                self.rate_limiter.record_usage(user_uid, "test_generation")
                self.role_quota_limiter.record_usage(role)
                cleaned2 = clean_json_array(response2)
                data = json.loads(cleaned2)

            if not isinstance(data, list):
                return []

            out: list[dict] = []
            for q in data:
                if is_valid_question(q):
                    out.append(q)
            return out[:batch_size]

        client = self.grading_client or self.client
        if not client:
            raise GroqServiceError("Groq client not initialized")

        cache_key = None
        if settings.groq_enable_caching:
            cache_key = self._generate_cache_key(
                "test_generation",
                {"document_content": content_preview, "topic": topic, "num_questions": target_count},
            )
            cached = self.cache.get(cache_key)
            if cached:
                try:
                    cached_questions = json.loads(cached)
                    if isinstance(cached_questions, list):
                        valid_cached = [q for q in cached_questions if is_valid_question(q)]
                        if len(valid_cached) >= target_count:
                            return valid_cached[:target_count]
                except Exception:
                    self.cache.delete(cache_key)

        try:
            batch_size = 10 if target_count > 15 else target_count
            unique_questions: list[dict] = []
            seen = set()
            attempts = 0

            while len(unique_questions) < target_count and attempts < 30:
                attempts += 1
                remaining = target_count - len(unique_questions)
                request_size = min(12, max(5, min(batch_size, remaining) + 3))
                avoid = [q.get("question", "") for q in unique_questions if isinstance(q, dict)]
                new_questions = await run_batch(request_size, avoid)
                if not new_questions:
                    continue
                for q in new_questions:
                    text = str(q.get("question", "")).strip().lower()
                    if not text or text in seen:
                        continue
                    seen.add(text)
                    unique_questions.append(q)
                    if len(unique_questions) >= target_count:
                        break

            result = unique_questions[:target_count]
            if len(result) < target_count:
                raise GroqServiceError(
                    f"AI could only generate {len(result)} unique questions out of {target_count}. Try again or reduce question count."
                )

            if cache_key:
                self.cache.set(cache_key, json.dumps(result), 7200)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode quiz questions JSON: {e}")
            raise GroqServiceError("AI returned invalid JSON for quiz questions")
        except (GroqServiceError, RateLimitExceeded):
            raise
        except Exception as e:
            logger.error(f"Error generating quiz questions: {e}")
            raise GroqServiceError(str(e))


# Create singleton instance
groq_service = GroqService()
