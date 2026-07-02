"""Runtime API endpoints — wired to real LLM pipeline."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ayeneh.api.deps import get_container

logger = structlog.get_logger(__name__)

router = APIRouter()


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    conversation_id: str | None = None


class SendMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence_number: int
    created_at: datetime


class RuntimeStatusResponse(BaseModel):
    status: str
    active_executions: int
    uptime_seconds: float
    version: str


class ExecutionRecord(BaseModel):
    id: str
    conversation_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None


class ExecutionHistoryResponse(BaseModel):
    data: list[ExecutionRecord]
    total: int
    has_more: bool = False


@router.post("/message", response_model=SendMessageResponse, status_code=201)
async def send_message(body: SendMessageRequest, user: Any = None) -> dict:
    """Send a message and get a complete response from the real LLM."""
    msg_id = str(uuid.uuid4())
    conv_id = body.conversation_id or str(uuid.uuid4())
    start = time.monotonic()

    try:
        container = get_container()
        agent = container.conversation_agent

        if agent is None:
            return {
                "id": msg_id,
                "conversation_id": conv_id,
                "role": "assistant",
                "content": "AI service is not configured. Please check your API key.",
                "sequence_number": 1,
                "created_at": datetime.now(UTC),
            }

        context = {
            "user_id": "web-user",
            "conversation_id": conv_id,
            "user_message": body.content,
            "conversation_history": [],
        }

        output = await agent.execute(context)
        response_text = output.data.get("response_text", "")

        if not response_text:
            response_text = "I received your message but couldn't generate a response."

        # Save assistant message to database
        if container.database:
            try:
                from sqlalchemy import select
                from ayeneh.infrastructure.persistence.models.message import MessageModel

                async with container.database.session_factory() as session:
                    # Get next sequence number
                    result = await session.execute(
                        select(MessageModel)
                        .where(MessageModel.conversation_id == uuid.UUID(conv_id))
                        .order_by(MessageModel.sequence_number.desc())
                        .limit(1)
                    )
                    last_msg = result.scalar_one_or_none()
                    seq = (last_msg.sequence_number + 1) if last_msg else 1

                    msg = MessageModel(
                        id=uuid.UUID(msg_id),
                        conversation_id=uuid.UUID(conv_id),
                        user_id=uuid.UUID(str(uuid.uuid4())),
                        role="assistant",
                        content=response_text,
                        sequence_number=seq,
                        token_count=output.metadata.get("total_tokens", 0),
                        created_at=datetime.now(UTC),
                    )
                    session.add(msg)
                    await session.commit()
            except Exception as db_exc:
                logger.warning("failed_to_save_message", error=str(db_exc))

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "message_completed",
            conversation_id=conv_id,
            response_length=len(response_text),
            duration_ms=round(duration_ms, 2),
        )

        return {
            "id": msg_id,
            "conversation_id": conv_id,
            "role": "assistant",
            "content": response_text,
            "sequence_number": 1,
            "created_at": datetime.now(UTC),
        }

    except Exception as exc:
        logger.exception("message_failed", error=str(exc))
        return {
            "id": msg_id,
            "conversation_id": conv_id,
            "role": "assistant",
            "content": f"Error: {str(exc)[:200]}",
            "sequence_number": 1,
            "created_at": datetime.now(UTC),
        }


@router.post("/message/stream")
async def send_message_stream(body: SendMessageRequest, user: Any = None) -> StreamingResponse:
    """Send a message and stream the response token-by-token from the real LLM."""
    conv_id = body.conversation_id or str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    async def event_stream() -> Any:
        yield f"event: message_start\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'role': 'assistant', 'created_at': now})}\n\n"

        try:
            container = get_container()
            agent = container.conversation_agent

            if agent is None:
                error_msg = "AI service is not configured. Please check your API key."
                yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': error_msg, 'token_count': 0})}\n\n"
                return

            context = {
                "user_id": "web-user",
                "conversation_id": conv_id,
                "user_message": body.content,
                "conversation_history": [],
            }

            token_count = 0
            accumulated = ""

            async for chunk in agent.stream(context):
                if chunk:
                    delta = json.dumps({"delta": chunk, "index": token_count})
                    yield f"event: content_delta\ndata: {delta}\n\n"
                    accumulated += chunk
                    token_count += 1

            yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': accumulated, 'token_count': token_count})}\n\n"

            logger.info(
                "stream_completed",
                conversation_id=conv_id,
                tokens=token_count,
                content_length=len(accumulated),
            )

        except Exception as exc:
            logger.exception("stream_failed", error=str(exc))
            error_msg = f"Stream error: {str(exc)[:200]}"
            yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': error_msg, 'token_count': 0})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status", response_model=RuntimeStatusResponse)
async def get_runtime_status() -> dict:
    return {
        "status": "healthy",
        "active_executions": 0,
        "uptime_seconds": 0,
        "version": "0.1.0",
    }


@router.get("/executions")
async def list_executions(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}
