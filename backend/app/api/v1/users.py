"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/me")
async def get_current_user(db: AsyncSession = Depends(get_db)) -> dict:
    """Get current authenticated user profile."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
