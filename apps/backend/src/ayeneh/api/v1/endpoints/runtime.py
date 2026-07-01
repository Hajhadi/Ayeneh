"""Runtime API endpoints."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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
    msg_id = str(uuid.uuid4())
    conv_id = body.conversation_id or str(uuid.uuid4())
    return {
        "id": msg_id,
        "conversation_id": conv_id,
        "role": "assistant",
        "content": "",
        "sequence_number": 1,
        "created_at": datetime.now(UTC),
    }


@router.post("/message/stream")
async def send_message_stream(body: SendMessageRequest, user: Any = None) -> StreamingResponse:
    conv_id = body.conversation_id or str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    async def event_stream() -> Any:
        yield f"event: message_start\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'role': 'assistant', 'created_at': now})}\n\n"

        tokens = [
            "Hello", "!", " I", " am", " Ayeneh", ",", " your", " cognitive",
            " companion", ".", " How", " can", " I", " help", " you", " today", "?",
        ]
        for i, token in enumerate(tokens):
            await asyncio.sleep(0.03)
            delta = json.dumps({"delta": token, "index": i})
            yield f"event: content_delta\ndata: {delta}\n\n"

        full_text = "".join(tokens)
        yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': full_text, 'token_count': len(tokens)})}\n\n"

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
