"""
Task API routes.

RESTful endpoints for task submission, status, results, and streaming.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.config import api_config
from api.core.auth import api_key_store, rate_limiter
from api.core.events import EventBus, TaskEvent
from api.core.storage import task_storage
from api.models import (
    ErrorResponse,
    FileInfo,
    IterationStartEvent,
    ObservationEvent,
    PlanStep,
    PlanUpdateEvent,
    TaskCreateRequest,
    TaskFilesResponse,
    TaskMode,
    TaskResponse,
    TaskResult,
    TaskStatus,
    TaskStatusResponse,
    ToolCallEvent,
    ToolResultEvent,
)


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
event_bus = EventBus()


def validate_api_key(request: Request) -> str:
    """Validate API key from request header."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    key_info = api_key_store.validate_key(api_key)
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check rate limit
    allowed, reason = rate_limiter.check_rate_limit(
        key_info.id,
        key_info.rate_limit_rpm,
        key_info.rate_limit_rph,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    
    return str(key_info.id)


def get_task_or_404(task_id: UUID) -> TaskStatusResponse:
    """Get task or raise 404."""
    task = task_storage.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_task(request: Request, task_req: TaskCreateRequest):
    """Submit a new agent task."""
    # Validate API key
    api_key_id = validate_api_key(request)
    
    # Generate task ID
    task_id = UUID(int=time.time_ns(), version=4)
    
    # Create task metadata
    task_storage.create_task(
        task_id=task_id,
        goal=task_req.goal,
        mode=task_req.mode,
        timeout_seconds=task_req.timeout_seconds,
        max_iterations=task_req.max_iterations,
        llm_model=task_req.llm_model,
    )
    
    # Enqueue task for background processing
    # TODO: Enqueue to Redis Queue
    # For now, we'll mark as queued and let worker pick it up
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.QUEUED,
        created_at=datetime.utcnow(),
    )


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_status(task_id: UUID):
    """Get task status and current state."""
    return get_task_or_404(task_id)


@router.get(
    "/{task_id}/result",
    response_model=TaskResult,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_result(task_id: UUID):
    """Get final task result."""
    result = task_storage.get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task result not found")
    return result


@router.get(
    "/{task_id}/stream",
    responses={200: {"description": "SSE stream"}},
)
async def stream_task_events(task_id: UUID, request: Request):
    """Stream task events via Server-Sent Events."""
    # Validate API key
    validate_api_key(request)
    
    # Check task exists
    task = task_storage.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create async generator for SSE
    async def event_generator():
        from api.core.events import event_bus
        
        # Local queue for events
        events_queue = []
        event_lock = __import__("threading").Lock()
        
        def event_callback(event: TaskEvent):
            with event_lock:
                events_queue.append(event)
        
        # Subscribe to task events
        event_bus.subscribe(task_id, event_callback)
        
        try:
            # Yield initial status
            yield f"event: status\ndata: {task.status.value}\n\n"
            
            # Stream events until done
            last_event_time = time.time()
            timeout = 300  # 5 minutes max stream
            
            while True:
                with event_lock:
                    if events_queue:
                        event = events_queue.pop(0)
                        yield f"event: {event.event_type}\ndata: {event.data}\n\n"
                        last_event_time = time.time()
                
                # Check task completion
                current_task = task_storage.get_task_status(task_id)
                if current_task and current_task.status in [
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.TIMEOUT,
                ]:
                    # Send final done event
                    if current_task.status == TaskStatus.COMPLETED:
                        result = task_storage.get_result(task_id)
                        duration = result.total_duration_ms if result else 0
                    elif current_task.status == TaskStatus.FAILED:
                        meta = task_storage.get_task(task_id)
                        duration = 0
                    else:
                        duration = current_task.timeout_seconds * 1000
                    
                    yield f"event: done\ndata: {{'status': '{current_task.status.value}', 'total_duration_ms': {duration}}}\n\n"
                    break
                
                # Check timeout
                if time.time() - last_event_time > timeout:
                    yield f"event: error\ndata: {{'error_class': 'TimeoutError', 'message': 'Stream timeout', 'recoverable': false}}\n\n"
                    break
                
                # Wait a bit
                import asyncio
                await asyncio.sleep(0.5)
        
        finally:
            # Unsubscribe
            event_bus.unsubscribe(task_id, event_callback)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{task_id}/files",
    response_model=TaskFilesResponse,
    responses={404: {"model": ErrorResponse}},
)
async def list_task_files(task_id: UUID):
    """List all files in task workspace."""
    task = get_task_or_404(task_id)
    files = task_storage.list_files(task_id)
    return TaskFilesResponse(task_id=task_id, files=files)


@router.get(
    "/{task_id}/files/{path:path}",
    responses={404: {"model": ErrorResponse}},
)
async def download_task_file(task_id: UUID, path: str):
    """Download a specific file from task workspace."""
    task = get_task_or_404(task_id)
    
    content = task_storage.get_file(task_id, path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={path}"},
    )


@router.get(
    "",
    response_model=list[TaskStatusResponse],
)
async def list_tasks(
    request: Request,
    limit: int = 100,
    offset: int = 0,
):
    """List all tasks (paginated)."""
    validate_api_key(request)
    return task_storage.list_tasks(limit=limit, offset=offset)