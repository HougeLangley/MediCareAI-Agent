"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health() -> dict:
    """Service health status."""
    return {"status": "healthy"}
