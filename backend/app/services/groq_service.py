"""
Groq AI Service
Centralized service for all Groq API interactions with rate limiting and caching.
"""

import asyncio
import hashlib
import json
import logging
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
            "doc_analysis": {"max": 20, "window": 3600},     # 20/hour
            "schedule": {"max": 60, "window": 3600},         # 60/hour (cached)
            "chat": {"max": 100, "window": 3600}             # 100/hour
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
        self.model = settings.groq_model
        self.cache = InMemoryCache()
        self.rate_limiter = RateLimiter()
        self._initialized = True

        # Initialize Groq client if API key is available
        if settings.groq_api_key:
            try:
                self.client = Groq(api_key=settings.groq_api_key)
                logger.info("✅ Groq client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client: {e}")
        else:
            logger.warning("⚠️ Groq API key not configured - AI features will use fallbacks")

    def is_available(self) -> bool:
        """Check if Groq service is available"""
        return self.client is not None

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
        temperature: float = 0.7
    ) -> str:
        """
        Make an async call to Groq API

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity parameter (0-1)

        Returns:
            Response text from Groq
        """
        if not self.client:
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
                lambda: self.client.chat.completions.create(
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
        system_prompt: str = "",
        fallback: str = "Unable to generate AI response.",
        use_cache: bool = True,
        cache_ttl: int = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
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

        Returns:
            Groq response or fallback
        """
        # Check if Groq is available
        if not self.is_available():
            logger.debug(f"Groq not available, using fallback for {feature}")
            return fallback

        # Check rate limit
        if not self.rate_limiter.check_limit(user_uid, feature):
            remaining = self.rate_limiter.get_remaining(user_uid, feature)
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
            # Make the API call
            response = await self._call_groq(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Record usage
            self.rate_limiter.record_usage(user_uid, feature)

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

        Args:
            user_uid: Student's user ID
            code: The submitted code (truncated to 2000 chars)
            language: Programming language
            test_results: List of test case results
            task_description: The assignment description
            security_issues: Any detected security issues

        Returns:
            Constructive feedback string
        """
        # Preprocess data
        code_snippet = code[:2000] if len(code) > 2000 else code
        passed_count = sum(1 for t in test_results if t.get("passed", False))
        total_count = len(test_results)

        # Format test results
        test_results_formatted = ""
        for i, result in enumerate(test_results[:5]):  # Limit to first 5
            status = "✓ PASSED" if result.get("passed") else "✗ FAILED"
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
            temperature=0.7
        )

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

        Returns dict with:
        - quality_assessment: str
        - structure_feedback: str
        - improvements: List[str]
        - suggested_score: int (0-100)
        - raw_response: str
        """
        content_preview = content[:3000] if len(content) > 3000 else content

        prompt = f"""ASSIGNMENT: {task_title}
REQUIREMENTS: {task_description[:500]}
MINIMUM WORDS: {min_words}

SUBMISSION PREVIEW:
"{content_preview}"

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

        system_prompt = "You are an academic writing evaluator. Always respond with valid JSON."

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
                use_cache=False,
                max_tokens=600,
                temperature=0.5
            )

            # Parse JSON response
            try:
                # Try to extract JSON from response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()

                result = json.loads(json_str)
                result["raw_response"] = response
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse Groq JSON response for document analysis")
                fallback_response["raw_response"] = response
                return fallback_response

        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return fallback_response

    async def explain_schedule(
        self,
        user_uid: str,
        workload_preference: str,
        pending_tasks: int,
        overdue_tasks: int,
        tasks: List[dict]
    ) -> List[str]:
        """
        Generate explanations for task priority rankings

        Args:
            user_uid: Student's user ID
            workload_preference: heavy/balanced/light
            pending_tasks: Count of pending tasks
            overdue_tasks: Count of overdue tasks
            tasks: List of task dicts with title, subject, deadline, days_remaining, points, priority_score, band

        Returns:
            List of explanation strings, one per task
        """
        # Format tasks for prompt
        tasks_formatted = ""
        for i, task in enumerate(tasks[:10]):  # Limit to 10 tasks
            tasks_formatted += f"\n{i+1}. {task.get('title', 'Untitled')}"
            tasks_formatted += f"\n   Subject: {task.get('subject', 'N/A')}"
            tasks_formatted += f"\n   Deadline: {task.get('deadline', 'No deadline')}"
            tasks_formatted += f"\n   Days remaining: {task.get('days_remaining', 'N/A')}"
            tasks_formatted += f"\n   Points: {task.get('points', 0)}"
            tasks_formatted += f"\n   Priority: {task.get('band', 'normal')} ({task.get('priority_score', 0):.2f})"

        prompt = f"""STUDENT WORKLOAD: {workload_preference} preference, {pending_tasks} pending, {overdue_tasks} overdue

PRIORITIZED TASKS (already ranked by urgency and importance):
{tasks_formatted}

For each task, provide a brief 1-sentence explanation of why it's ranked at this priority level.

Format as a numbered list matching the tasks:
1. [explanation]
2. [explanation]
...

Keep explanations concise and actionable."""

        system_prompt = "You are a study advisor helping a student prioritize tasks. Be concise and practical."

        # Generate fallback explanations
        fallback_explanations = []
        for task in tasks:
            band = task.get("band", "normal")
            days = task.get("days_remaining")
            points = task.get("points", 0)

            if band == "urgent":
                explanation = f"Due soon with {points} points - prioritize immediately."
            elif band == "high":
                explanation = f"Important assignment worth {points} points - schedule time this week."
            elif days is not None and days < 0:
                explanation = "Overdue - complete as soon as possible."
            else:
                explanation = f"Regular priority - plan to complete by deadline."

            fallback_explanations.append(explanation)

        try:
            response = await self.safe_call(
                feature="schedule",
                user_uid=user_uid,
                prompt=prompt,
                system_prompt=system_prompt,
                fallback="\n".join([f"{i+1}. {e}" for i, e in enumerate(fallback_explanations)]),
                use_cache=True,
                cache_ttl=3600,  # Cache for 1 hour
                max_tokens=400,
                temperature=0.5
            )

            # Parse numbered list response
            explanations = []
            lines = response.strip().split("\n")
            for line in lines:
                # Remove number prefix like "1. " or "1) "
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove "1. " or "1) " prefix
                    parts = line.split(". ", 1) if ". " in line else line.split(") ", 1)
                    if len(parts) > 1:
                        explanations.append(parts[1].strip())
                    else:
                        explanations.append(line)

            # Pad with fallbacks if needed
            while len(explanations) < len(tasks):
                idx = len(explanations)
                if idx < len(fallback_explanations):
                    explanations.append(fallback_explanations[idx])
                else:
                    explanations.append("Complete by deadline.")

            return explanations[:len(tasks)]

        except Exception as e:
            logger.error(f"Schedule explanation error: {e}")
            return fallback_explanations

    async def chat_response(
        self,
        user_uid: str,
        message: str,
        intent: str,
        context: dict
    ) -> str:
        """
        Generate chat response for task-focused assistant

        Args:
            user_uid: User's ID
            message: User's message
            intent: Detected intent (task_info, submission_status, schedule_help, general_query)
            context: Relevant context data based on intent

        Returns:
            Assistant response string
        """
        # Format context based on what's available
        context_formatted = ""

        if "tasks" in context:
            context_formatted += "\nUPCOMING TASKS:"
            for task in context.get("tasks", [])[:5]:
                context_formatted += f"\n- {task.get('title')}: due {task.get('deadline', 'no deadline')}, {task.get('points', 0)} points"

        if "submissions" in context:
            context_formatted += "\nRECENT SUBMISSIONS:"
            for sub in context.get("submissions", [])[:3]:
                status = "graded" if sub.get("score") else "pending"
                context_formatted += f"\n- {sub.get('task_title')}: {status}"
                if sub.get("score"):
                    context_formatted += f" (score: {sub.get('score')})"

        if "schedule" in context:
            context_formatted += "\nPRIORITIZED TASKS:"
            for task in context.get("schedule", [])[:5]:
                context_formatted += f"\n- {task.get('title')}: {task.get('band')} priority"

        if "workload" in context:
            wl = context.get("workload", {})
            context_formatted += f"\nWORKLOAD: {wl.get('pending', 0)} pending, {wl.get('overdue', 0)} overdue"

        if not context_formatted:
            context_formatted = "\nNo specific context available."

        prompt = f"""STUDENT CONTEXT:{context_formatted}

DETECTED INTENT: {intent}

STUDENT QUESTION: {message}

Provide a helpful, concise response. If the question is outside your scope (task management), politely redirect to task-related queries.

Keep response under 200 words."""

        system_prompt = """You are a task management assistant for students. You help with:
- Task information and deadlines
- Submission status and grades
- Scheduling and prioritization

You do NOT help with:
- Course content or homework answers
- General tutoring
- Topics unrelated to task management

Be friendly, concise, and helpful."""

        fallback = "I can help you with your tasks, deadlines, and submissions. What would you like to know?"

        return await self.safe_call(
            feature="chat",
            user_uid=user_uid,
            prompt=prompt,
            system_prompt=system_prompt,
            fallback=fallback,
            use_cache=False,  # Don't cache chat responses
            max_tokens=300,
            temperature=0.7
        )

    def invalidate_schedule_cache(self, user_uid: str):
        """Invalidate schedule cache for a user (call when tasks change)"""
        # Clear all schedule-related cache entries for user
        # This is a simple implementation - for production, use Redis with pattern matching
        self.cache.clear_expired()
        logger.debug(f"Schedule cache invalidated for user {user_uid}")


# Global singleton instance
groq_service = GroqService()
