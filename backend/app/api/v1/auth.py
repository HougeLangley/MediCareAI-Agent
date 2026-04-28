"""Authentication endpoints.

Supports:
- Patient/Doctor/Admin login & register
- Guest mode token issuance
- Role switch
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.post("/register")
async def register(db: AsyncSession = Depends(get_db)) -> dict:
    """Register a new user (patient or doctor)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/login")
async def login(db: AsyncSession = Depends(get_db)) -> dict:
    """Authenticate and issue JWT."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/guest")
async def create_guest_session(db: AsyncSession = Depends(get_db)) -> dict:
    """Create a time-limited guest session."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/switch-role")
async def switch_role(db: AsyncSession = Depends(get_db)) -> dict:
    """Switch between patient and doctor identities."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
