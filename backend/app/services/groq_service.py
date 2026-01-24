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
            "doc_analysis": {"max": 20, "window": 3600},     # 20/hour
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
                logger.info("✅ Groq client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client: {e}")
        else:
            logger.warning("⚠️ Groq API key not configured - AI features will use fallbacks")

        # Initialize Groq grading client if API key is available
        if settings.groq_grading_api_key:
            try:
                self.grading_client = Groq(api_key=settings.groq_grading_api_key)
                logger.info("✅ Groq grading client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq grading client: {e}")

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
            temperature=0.7,
            use_grading_key=True
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
        Uses grading API key if available.
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
                temperature=0.5,
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


# Create singleton instance
groq_service = GroqService()
