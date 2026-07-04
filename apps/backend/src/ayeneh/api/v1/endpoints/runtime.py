"""Runtime API endpoints — wired to real LLM pipeline."""

from __future__ import annotations

import asyncio
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
from ayeneh.logging.pipeline_logger import PipelineLogger

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
    """Send a message through the full Ayeneh pipeline."""
    msg_id = str(uuid.uuid4())
    conv_id = body.conversation_id or str(uuid.uuid4())
    start = time.monotonic()

    try:
        # Retrieve conversation history from database
        conversation_history = []
        try:
            import sqlite3
            conn = sqlite3.connect("/home/hadi/ayeneh/Ayeneh/ayeneh.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE conversation_id=? AND deleted_at IS NULL ORDER BY sequence_number LIMIT 20",
                (conv_id,)
            )
            for row in cursor.fetchall():
                conversation_history.append({"role": row[0], "content": row[1]})
            conn.close()
        except Exception:
            pass

        context = {
            "user_id": "web-user",
            "conversation_id": conv_id,
            "user_message": body.content,
            "conversation_history": conversation_history,
        }

        # Run full pipeline
        from ayeneh.runtime.pipeline import AyenehPipeline
        pipeline = AyenehPipeline()
        pipeline_result = await pipeline.run(context)

        response_text = pipeline_result.final_response
        if not response_text:
            response_text = "I couldn't generate a response."

        # Save assistant message to database
        try:
            import sqlite3
            conn = sqlite3.connect("/home/hadi/ayeneh/Ayeneh/ayeneh.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(sequence_number) FROM messages WHERE conversation_id=?",
                (conv_id,)
            )
            last_seq = cursor.fetchone()[0]
            seq = (last_seq + 1) if last_seq else 1

            cursor.execute(
                "INSERT INTO messages (id, conversation_id, user_id, role, content, sequence_number, token_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (msg_id, conv_id, str(uuid.uuid4()), "assistant", response_text, seq, 0)
            )
            conn.commit()
            conn.close()
        except Exception as db_exc:
            logger.warning("failed_to_save_message", error=str(db_exc))

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "pipeline_completed",
            conversation_id=conv_id,
            stages=len(pipeline_result.stages),
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
    """Send a message through the full pipeline and stream the response."""
    conv_id = body.conversation_id or str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    pipeline_logger = PipelineLogger()

    async def event_stream() -> Any:
        yield f"event: message_start\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'role': 'assistant', 'created_at': now})}\n\n"

        try:
            # Retrieve conversation history
            conversation_history = []
            try:
                import sqlite3
                conn = sqlite3.connect("/home/hadi/ayeneh/Ayeneh/ayeneh.db")
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content FROM messages WHERE conversation_id=? AND deleted_at IS NULL ORDER BY sequence_number LIMIT 20",
                    (conv_id,)
                )
                for row in cursor.fetchall():
                    conversation_history.append({"role": row[0], "content": row[1]})
                conn.close()
            except Exception:
                pass

            context = {
                "user_id": "web-user",
                "conversation_id": conv_id,
                "user_message": body.content,
                "conversation_history": conversation_history,
            }

            # Queue for interleaving pipeline events with token streaming
            stage_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

            async def on_stage(name: str, status: str, details: dict[str, Any]) -> None:
                await stage_queue.put({
                    "type": "pipeline_stage",
                    "stage": name,
                    "status": status,
                    "confidence": details.get("confidence", 0),
                    "duration_ms": details.get("duration_ms", 0),
                    "error": details.get("error"),
                    "message": details.get("message"),
                    "details": details.get("details"),
                })
                # Log to file
                pipeline_logger.log_event(
                    request_id=request_id,
                    stage=name,
                    status=status,
                    confidence=details.get("confidence", 0),
                    duration_ms=details.get("duration_ms", 0),
                    error=details.get("error"),
                    details={k: v for k, v in details.items() if k not in ("confidence", "duration_ms", "error")},
                )

            # Run pipeline in background task
            from ayeneh.runtime.pipeline import AyenehPipeline
            pipeline = AyenehPipeline()
            pipeline_task = asyncio.create_task(pipeline.run(context, on_stage=on_stage))

            # Drain stage events while pipeline runs
            while not pipeline_task.done():
                try:
                    event = await asyncio.wait_for(stage_queue.get(), timeout=0.1)
                    yield f"event: {event['type']}\ndata: {json.dumps({k: v for k, v in event.items() if k != 'type'})}\n\n"
                except asyncio.TimeoutError:
                    pass

            # Drain remaining events
            pipeline_result = pipeline_task.result()
            while not stage_queue.empty():
                event = stage_queue.get_nowait()
                yield f"event: {event['type']}\ndata: {json.dumps({k: v for k, v in event.items() if k != 'type'})}\n\n"

            # Pipeline complete
            yield f"event: pipeline_complete\ndata: {json.dumps({'total_duration_ms': round(pipeline_result.total_duration_ms, 2), 'stages_count': len(pipeline_result.stages)})}\n\n"

            # Log completion
            pipeline_logger.log_complete(
                request_id=request_id,
                total_duration_ms=pipeline_result.total_duration_ms,
                stages_count=len(pipeline_result.stages),
                errors=pipeline_result.errors,
            )

            # Now stream the response
            agent = pipeline._get_conversation_agent()
            enriched_context = pipeline._build_enriched_context(context, pipeline_result)

            token_count = 0
            accumulated = ""

            async for chunk in agent.stream(enriched_context):
                if chunk:
                    delta = json.dumps({"delta": chunk, "index": token_count})
                    yield f"event: content_delta\ndata: {delta}\n\n"
                    accumulated += chunk
                    token_count += 1

            # Save to database
            try:
                import sqlite3
                conn = sqlite3.connect("/home/hadi/ayeneh/Ayeneh/ayeneh.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (id, conversation_id, user_id, role, content, sequence_number, token_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (str(uuid.uuid4()), conv_id, str(uuid.uuid4()), "assistant", accumulated, 1, token_count)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

            yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': accumulated, 'token_count': token_count})}\n\n"

            logger.info("stream_completed", conversation_id=conv_id, tokens=token_count)

        except Exception as exc:
            logger.exception("stream_failed", error=str(exc))
            yield f"event: message_end\ndata: {json.dumps({'id': msg_id, 'conversation_id': conv_id, 'content': f'Error: {str(exc)[:200]}', 'token_count': 0})}\n\n"

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
