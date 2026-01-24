"""
Intent Classifier for Chat Assistant
Rule-based intent classification to reduce Groq API calls.
"""

import re
from typing import Tuple, List
from enum import Enum


class ChatIntent(str, Enum):
    """Supported chat intents"""
    TASK_INFO = "task_info"           # Questions about tasks, deadlines
    SUBMISSION_STATUS = "submission_status"  # Questions about grades, feedback
    SCHEDULE_HELP = "schedule_help"   # Questions about prioritization, planning
    GENERAL_QUERY = "general_query"   # General help requests
    GREETING = "greeting"             # Hi, hello, etc.
    OUT_OF_SCOPE = "out_of_scope"     # Questions outside our scope


# Keywords for each intent
INTENT_KEYWORDS = {
    ChatIntent.TASK_INFO: [
        "task", "assignment", "homework", "project", "deadline", "due",
        "when", "what", "which", "submit", "submission deadline",
        "how many", "how much", "points", "marks", "grade worth",
        "upcoming", "pending", "list", "show me"
    ],
    ChatIntent.SUBMISSION_STATUS: [
        "submitted", "submission", "grade", "graded", "score", "scored",
        "feedback", "evaluation", "evaluated", "result", "results",
        "my grade", "my score", "how did i", "did i pass", "status",
        "checked", "reviewed", "comments"
    ],
    ChatIntent.SCHEDULE_HELP: [
        "priority", "prioritize", "first", "start", "begin", "order",
        "plan", "schedule", "organize", "which task", "what should",
        "most important", "urgent", "focus", "time management",
        "study plan", "work on", "next", "recommend"
    ],
    ChatIntent.GREETING: [
        "hi", "hello", "hey", "good morning", "good afternoon",
        "good evening", "howdy", "greetings", "sup", "yo",
        "what's up", "whats up"
    ],
    ChatIntent.OUT_OF_SCOPE: [
        "solve", "answer", "explain", "explain about", "explain the concept", "what is", "define", "tell me about",
        "how to code", "teach me", "tutorial", "help me solve", "do my homework",
        "write code", "fix my code", "debug", "fastapi", "fast api", "weather", "news",
        "joke", "story", "game"
    ]
}

# Patterns for more specific matching
INTENT_PATTERNS = {
    ChatIntent.TASK_INFO: [
        r"what.*tasks?",
        r"when.*due",
        r"deadline.*for",
        r"how many.*points",
        r"show.*tasks?",
        r"list.*assignments?",
        r"what.*assigned",
        r"any.*upcoming"
    ],
    ChatIntent.SUBMISSION_STATUS: [
        r"my.*grade",
        r"my.*score",
        r"did i.*submit",
        r"have i.*submitted",
        r"feedback.*on",
        r"how.*did i.*do",
        r"result.*for",
        r"status.*of.*submission"
    ],
    ChatIntent.SCHEDULE_HELP: [
        r"what.*should.*first",
        r"what.*should.*start",
        r"which.*task.*first",
        r"priorit(y|ize)",
        r"most.*important",
        r"urgent.*task",
        r"what.*next",
        r"recommend.*task"
    ]
}


def classify_intent(message: str) -> Tuple[ChatIntent, float]:
    """
    Classify the intent of a user message.

    Args:
        message: User's chat message

    Returns:
        Tuple of (intent, confidence_score)
        Confidence score is 0.0 to 1.0
    """
    message_lower = message.lower().strip()

    # Check for greetings first (highest priority)
    for keyword in INTENT_KEYWORDS[ChatIntent.GREETING]:
        if message_lower == keyword or message_lower.startswith(keyword + " ") or message_lower.startswith(keyword + ","):
            return (ChatIntent.GREETING, 0.95)

    # Check for out of scope queries
    for keyword in INTENT_KEYWORDS[ChatIntent.OUT_OF_SCOPE]:
        if keyword in message_lower:
            # But don't trigger for task-related questions
            task_related = any(
                tk in message_lower
                for tk in INTENT_KEYWORDS[ChatIntent.TASK_INFO]
            )
            if not task_related:
                return (ChatIntent.OUT_OF_SCOPE, 0.7)

    # Score each intent
    scores = {intent: 0.0 for intent in ChatIntent}

    # Keyword matching
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent in [ChatIntent.GREETING, ChatIntent.OUT_OF_SCOPE]:
            continue  # Already handled

        for keyword in keywords:
            if keyword in message_lower:
                # Longer keywords get higher scores
                scores[intent] += 0.1 * (1 + len(keyword.split()) * 0.5)

    # Pattern matching (higher confidence)
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                scores[intent] += 0.3

    # Find best match
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    # Normalize score to 0-1 range
    confidence = min(1.0, best_score)

    # If confidence is too low, classify as general query
    if confidence < 0.2:
        return (ChatIntent.GENERAL_QUERY, 0.5)

    return (best_intent, confidence)


def get_required_context(intent: ChatIntent) -> List[str]:
    """
    Get the context types needed for an intent.

    Args:
        intent: The classified intent

    Returns:
        List of context keys to fetch (tasks, submissions, schedule, workload)
    """
    context_map = {
        ChatIntent.TASK_INFO: ["tasks", "upcoming_deadlines"],
        ChatIntent.SUBMISSION_STATUS: ["submissions", "pending_evaluations"],
        ChatIntent.SCHEDULE_HELP: ["schedule", "workload"],
        ChatIntent.GENERAL_QUERY: ["tasks", "workload"],
        ChatIntent.GREETING: [],
        ChatIntent.OUT_OF_SCOPE: []
    }

    return context_map.get(intent, [])


def get_greeting_response() -> str:
    """Get a friendly greeting response"""
    return (
        "Hello! I'm your task management assistant. I can help you with:\n"
        "- Finding out about your tasks and deadlines\n"
        "- Checking your submission status and grades\n"
        "- Prioritizing what to work on next\n\n"
        "What would you like to know?"
    )


def get_out_of_scope_response() -> str:
    """Get response for out-of-scope queries"""
    return (
        "I'm a task management assistant, so I can't help with that specific request. "
        "However, I can help you with:\n"
        "- Your upcoming tasks and deadlines\n"
        "- Checking submission status and grades\n"
        "- Prioritizing your assignments\n\n"
        "Is there anything task-related I can help you with?"
    )


# Test function
if __name__ == "__main__":
    test_messages = [
        "hi",
        "what tasks do I have?",
        "when is my assignment due?",
        "what's my grade?",
        "did I submit the homework?",
        "what should I work on first?",
        "which task is most urgent?",
        "solve this math problem for me",
        "help me with my code",
        "show me upcoming deadlines",
        "how many points is the project worth?",
        "what's the weather today?"
    ]

    for msg in test_messages:
        intent, confidence = classify_intent(msg)
        print(f"'{msg}' -> {intent.value} (confidence: {confidence:.2f})")
