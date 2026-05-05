"""LLM proxy endpoints.

Provides direct access to the unified LLM service for:
- Health checks
- Quick chat completions
- Streaming chat (SSE)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.services.llm import LLMService, get_llm_service

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat completion request."""

    messages: list[dict[str, str]] = Field(..., min_length=1)
    model: str | None = None
    provider: str | None = Field(None, description="Provider name (e.g. openai, moonshot). Uses default if omitted.")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=8192)
    system_prompt: str | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    provider: str
    usage_prompt_tokens: int
    usage_completion_tokens: int


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Non-streaming chat completion."""
    try:
        service = await get_llm_service(
            db, platform=current_user.platform, model_type="diagnosis"
        )
        if req.provider:
            service = LLMService(provider=req.provider, platform=current_user.platform, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    resp = await service.chat(
        messages=req.messages,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        system_prompt=req.system_prompt,
    )
    return ChatResponse(
        content=resp.content,
        model=resp.model,
        provider=resp.provider,
        usage_prompt_tokens=resp.usage_prompt_tokens,
        usage_completion_tokens=resp.usage_completion_tokens,
    )


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Streaming chat completion via SSE."""
    try:
        service = await get_llm_service(
            db, platform=current_user.platform, model_type="diagnosis"
        )
        if req.provider:
            service = LLMService(provider=req.provider, platform=current_user.platform, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    async def event_generator():
        async for chunk in service.chat_stream(
            messages=req.messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            system_prompt=req.system_prompt,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/health")
async def llm_health(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    provider: str | None = None,
) -> dict:
    """Check LLM provider connectivity."""
    try:
        if provider:
            service = LLMService(provider=provider, platform=current_user.platform, db=db)
        else:
            service = await get_llm_service(db, platform=current_user.platform)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return await service.health_check()
