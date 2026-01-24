from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from app.services.groq_service import GroqService
from app.utils.dependencies import get_current_user

router = APIRouter()

class TestGenerationRequest(BaseModel):
    code: str
    language: str
    num_tests: int = Field(default=5, ge=1, le=20)

class TaskExtractionRequest(BaseModel):
    content: str

class DocumentGradingRequest(BaseModel):
    content: str
    task_title: str
    task_description: str
    min_words: int = 0
    word_count: int
    found_keywords: List[str] = []
    missing_keywords: List[str] = []
    readability: Dict[str, Any] = {}

class CodeGradingRequest(BaseModel):
    code: str
    language: str
    test_results: List[dict]
    task_description: str
    security_issues: List[str] = []

@router.post("/tests/generate")
async def generate_test_cases(
    request: TestGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    groq_service = GroqService()
    user_uid = current_user.get("uid")
    
    test_cases = await groq_service.generate_test_cases(
        user_uid=user_uid,
        code=request.code,
        language=request.language,
        num_tests=request.num_tests
    )
    return test_cases

@router.post("/tasks/extract")
async def extract_tasks(
    request: TaskExtractionRequest,
    current_user: dict = Depends(get_current_user)
):
    groq_service = GroqService()
    user_uid = current_user.get("uid")
    
    tasks = await groq_service.extract_tasks_from_doc(
        user_uid=user_uid,
        content=request.content
    )
    return tasks

@router.post("/grading/document")
async def grade_document(
    request: DocumentGradingRequest,
    current_user: dict = Depends(get_current_user)
):
    groq_service = GroqService()
    user_uid = current_user.get("uid")
    
    result = await groq_service.analyze_document(
        user_uid=user_uid,
        content=request.content,
        word_count=request.word_count,
        required_keywords=[], # passed implicitly via found/missing
        found_keywords=request.found_keywords,
        missing_keywords=request.missing_keywords,
        readability=request.readability,
        task_title=request.task_title,
        task_description=request.task_description,
        min_words=request.min_words
    )
    return result

@router.post("/grading/code")
async def grade_code(
    request: CodeGradingRequest,
    current_user: dict = Depends(get_current_user)
):
    groq_service = GroqService()
    user_uid = current_user.get("uid")
    
    feedback = await groq_service.generate_code_feedback(
        user_uid=user_uid,
        code=request.code,
        language=request.language,
        test_results=request.test_results,
        task_description=request.task_description,
        security_issues=request.security_issues
    )
    return {"feedback": feedback}
