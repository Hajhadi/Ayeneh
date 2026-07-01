"""Goal API endpoints — CRUD, review, progress, milestones, dependencies, statistics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["goals"])


class CreateGoalRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    category: str = "other"
    goal_type: str = "outcome"
    deadline: str | None = None
    tags: list[str] = []


class UpdateGoalRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    category: str | None = None


class ProgressRequest(BaseModel):
    progress: float
    note: str = ""


class ReviewRequest(BaseModel):
    rating: float
    notes: str = ""


class MilestoneRequest(BaseModel):
    title: str
    target_value: float = 1.0


class DependencyRequest(BaseModel):
    dependency_id: str
    dependency_type: str = "blocks"


def _goal_dict(goal: Any) -> dict[str, Any]:
    return {
        "id": goal.id, "title": goal.title, "description": goal.description,
        "status": goal.status, "priority": goal.priority, "category": goal.category,
        "goal_type": goal.goal_type, "importance": goal.importance,
        "confidence": goal.confidence, "progress": goal.progress,
        "deadline": goal.deadline, "created_at": goal.created_at,
        "updated_at": goal.updated_at, "tags": goal.tags,
        "milestone_count": len(goal.milestones),
        "is_overdue": goal.is_overdue,
    }


def _get_goal_service(request: Any) -> Any:
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "goal_service"):
        return container.goal_service
    raise HTTPException(status_code=503, detail="Goal service not available")


@router.post("/", status_code=201)
async def create_goal(request: Request, body: CreateGoalRequest) -> dict[str, Any]:
    service = _get_goal_service(request)
    goal = await service.create_goal(
        user_id="default", title=body.title, description=body.description,
        priority=body.priority, category=body.category,
        goal_type=body.goal_type, deadline=body.deadline, tags=body.tags,
    )
    return _goal_dict(goal)


@router.get("/")
async def list_goals(
    request: Request,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    service = _get_goal_service(request)
    goals = await service.list_goals("default", status=status, category=category, priority=priority, limit=limit)
    return {"data": [_goal_dict(g) for g in goals], "total": len(goals)}


@router.get("/active")
async def get_active_goals(request: Request) -> dict[str, Any]:
    service = _get_goal_service(request)
    goals = await service.get_active_goals("default")
    return {"data": [_goal_dict(g) for g in goals], "total": len(goals)}


@router.get("/overdue")
async def get_overdue_goals(request: Request) -> dict[str, Any]:
    service = _get_goal_service(request)
    goals = await service.get_overdue_goals("default")
    return {"data": [_goal_dict(g) for g in goals], "total": len(goals)}


@router.get("/stats")
async def get_goal_stats(request: Request) -> dict[str, Any]:
    service = _get_goal_service(request)
    stats = await service.get_stats("default")
    return {
        "total": stats.total, "active": stats.active,
        "completed": stats.completed, "abandoned": stats.abandoned,
        "overdue": stats.overdue, "blocked": stats.blocked,
        "avg_progress": stats.avg_progress, "completion_rate": stats.completion_rate,
        "by_category": stats.by_category, "by_priority": stats.by_priority,
    }


@router.get("/{goal_id}")
async def get_goal(request: Request, goal_id: str) -> dict[str, Any]:
    service = _get_goal_service(request)
    goal = await service.get_goal(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _goal_dict(goal)


@router.patch("/{goal_id}")
async def update_goal(request: Request, goal_id: str, body: UpdateGoalRequest) -> dict[str, Any]:
    service = _get_goal_service(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    goal = await service.update_goal(goal_id, **updates)
    return _goal_dict(goal)


@router.post("/{goal_id}/activate")
async def activate_goal(request: Request, goal_id: str) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.activate_goal(goal_id)
    return {"goal_id": goal_id, "status": "active"}


@router.post("/{goal_id}/complete")
async def complete_goal(request: Request, goal_id: str) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.complete_goal(goal_id)
    return {"goal_id": goal_id, "status": "completed"}


@router.post("/{goal_id}/pause")
async def pause_goal(request: Request, goal_id: str) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.pause_goal(goal_id)
    return {"goal_id": goal_id, "status": "paused"}


@router.post("/{goal_id}/abandon")
async def abandon_goal(request: Request, goal_id: str) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.abandon_goal(goal_id)
    return {"goal_id": goal_id, "status": "abandoned"}


@router.post("/{goal_id}/archive")
async def archive_goal(request: Request, goal_id: str) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.archive_goal(goal_id)
    return {"goal_id": goal_id, "status": "archived"}


@router.post("/{goal_id}/progress")
async def update_progress(request: Request, goal_id: str, body: ProgressRequest) -> dict[str, Any]:
    service = _get_goal_service(request)
    goal = await service.update_progress(goal_id, body.progress, body.note)
    return _goal_dict(goal)


@router.post("/{goal_id}/milestones")
async def add_milestone(request: Request, goal_id: str, body: MilestoneRequest) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.add_milestone(goal_id, body.title, body.target_value)
    return {"goal_id": goal_id, "status": "milestone_added"}


@router.post("/{goal_id}/dependencies")
async def add_dependency(request: Request, goal_id: str, body: DependencyRequest) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.add_dependency(goal_id, body.dependency_id, body.dependency_type)
    return {"goal_id": goal_id, "status": "dependency_added"}


@router.post("/{goal_id}/reviews")
async def add_review(request: Request, goal_id: str, body: ReviewRequest) -> dict[str, str]:
    service = _get_goal_service(request)
    await service.add_review(goal_id, body.rating, body.notes)
    return {"goal_id": goal_id, "status": "review_added"}


@router.get("/{goal_id}/history")
async def get_history(request: Request, goal_id: str) -> list[dict[str, Any]]:
    service = _get_goal_service(request)
    return await service.get_history(goal_id)


@router.get("/metrics/goals")
async def get_goal_metrics(request: Request) -> dict[str, Any]:
    container = getattr(request.app.state, "container", None)
    if container and hasattr(container, "goal_metrics"):
        m = container.goal_metrics
        return {
            "retrieval_total": m.goal_retrieval_total,
            "prompt_tokens": m.goal_prompt_tokens,
            "context_size": m.goal_context_size,
            "scheduler_runs": m.goal_scheduler_runs,
            "overdue_total": m.goal_overdue_total,
            "completion_rate": m.goal_completion_rate,
            "abandonment_rate": m.goal_abandonment_rate,
            "blocked_total": m.goal_blocked_total,
            "conflicts_total": m.goal_conflicts_total,
            "evolution_total": m.goal_evolution_total,
            "failures": m.failures,
        }
    return {}
