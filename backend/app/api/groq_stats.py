"""
Groq API statistics and quota monitoring endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.groq_client.router import get_model_router
from app.config import settings
from app.utils.dependencies import get_current_teacher

router = APIRouter()


@router.get("/quota")
async def get_quota_status(current_teacher: dict = Depends(get_current_teacher)):
    """
    Get current quota usage for all Groq models.

    Only accessible by teachers.

    Returns:
        Dict with quota usage and limits for each model
    """
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API not configured",
        )

    router_instance = get_model_router()
    stats = await router_instance.get_routing_stats()

    return {
        "status": "ok",
        "routing_enabled": stats["routing_enabled"],
        "models": stats["quotas"],
        "cache": stats["cache"],
    }


@router.get("/health")
async def health_check():
    """
    Check if Groq integration is healthy.

    Returns:
        Health status
    """
    if not settings.groq_api_key:
        return {
            "status": "unavailable",
            "reason": "Groq API key not configured",
        }

    try:
        router_instance = get_model_router()
        stats = await router_instance.get_routing_stats()

        # Check if any model is approaching limits
        warnings = []
        for model_name, model_stats in stats["quotas"].items():
            rpd_pct = model_stats["percentage"]["rpd"]
            if rpd_pct >= 80:
                warnings.append(f"{model_name}: {rpd_pct:.1f}% of daily requests used")

        return {
            "status": "healthy" if not warnings else "warning",
            "warnings": warnings,
            "routing_enabled": stats["routing_enabled"],
            "cache_enabled": stats["cache"].get("enabled", False),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)[:200],
        }


@router.post("/cache/clear")
async def clear_cache(current_teacher: dict = Depends(get_current_teacher)):
    """
    Clear the Groq response cache.

    Only accessible by teachers. Use with caution!

    Returns:
        Number of entries cleared
    """
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API not configured",
        )

    router_instance = get_model_router()
    count = await router_instance.cache.clear_all()

    return {
        "status": "ok",
        "entries_cleared": count,
        "message": f"Cleared {count} cache entries",
    }


@router.get("/cache/stats")
async def get_cache_stats(current_teacher: dict = Depends(get_current_teacher)):
    """
    Get cache statistics.

    Only accessible by teachers.

    Returns:
        Cache stats including hit rate, size, etc.
    """
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API not configured",
        )

    router_instance = get_model_router()
    stats = await router_instance.cache.get_stats()

    return {
        "status": "ok",
        "cache": stats,
    }
