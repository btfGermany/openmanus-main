"""
Pydantic models for OpenManus API service.

Request/Response schemas for task submission, status, results, and streaming.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskMode(str, Enum):
    """Task execution modes."""

    DIRECT = "direct"
    FLOW = "flow"
    RESEARCH = "research"


class TaskStatus(str, Enum):
    """Task status states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""

    goal: str = Field(..., description="The task goal/prompt for the agent")
    mode: TaskMode = Field(default=TaskMode.FLOW, description="Execution mode")
    timeout_seconds: int = Field(default=300, description="Task timeout in seconds")
    max_iterations: int = Field(default=20, description="Maximum agent iterations")
    llm_model: Optional[str] = Field(default=None, description="Override default LLM model")

    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Research GPU prices and create a comparison report",
                "mode": "flow",
                "timeout_seconds": 180,
                "max_iterations": 15,
            }
        }


class TaskResponse(BaseModel):
    """Response after creating a task."""

    task_id: UUID = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    current_step: Optional[str] = Field(default=None, description="Current step description")
    iteration_count: int = Field(default=0, description="Number of iterations executed")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "created_at": "2026-05-13T12:00:00Z",
                "updated_at": None,
                "current_step": None,
                "iteration_count": 0,
            }
        }


class TaskStatusResponse(BaseModel):
    """Extended task status with metadata."""

    task_id: UUID
    status: TaskStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    iteration_count: int = 0
    goal: str = ""


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    id: int = Field(..., description="Step ID")
    description: str = Field(..., description="Step description")
    status: str = Field(default="pending", description="Step status")


class ToolCallEvent(BaseModel):
    """Tool call event data."""

    tool: str = Field(..., description="Tool name")
    input: str = Field(..., description="Tool input (JSON string)")
    timestamp: Optional[datetime] = Field(default=None, description="Event timestamp")


class ToolResultEvent(BaseModel):
    """Tool result event data."""

    tool: str = Field(..., description="Tool name")
    output: str = Field(..., description="Tool output (truncated)")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    timestamp: Optional[datetime] = None


class IterationStartEvent(BaseModel):
    """Iteration start event data."""

    iteration: int = Field(..., description="Iteration number")
    thought: str = Field(..., description="Agent's thought")


class ObservationEvent(BaseModel):
    """Stdout/stderr observation event."""

    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    exit_code: int = Field(default=0, description="Exit code")


class ErrorEvent(BaseModel):
    """Error event data."""

    error_class: str = Field(..., description="Exception class name")
    message: str = Field(..., description="Error message")
    recoverable: bool = Field(default=False, description="Is the error recoverable")
    retry_count: int = Field(default=0, description="Number of retries attempted")


class PlanUpdateEvent(BaseModel):
    """Plan update event data."""

    step_id: int = Field(..., description="Step ID")
    status: str = Field(..., description="New step status")


class FinalResultEvent(BaseModel):
    """Final result event data."""

    final_answer: Optional[str] = Field(default=None, description="Final answer text")
    output_files: List[str] = Field(default_factory=list, description="Output file paths")


class DoneEvent(BaseModel):
    """Task completion event."""

    status: TaskStatus = Field(..., description="Final status")
    total_duration_ms: int = Field(..., description="Total duration in milliseconds")


class TaskResult(BaseModel):
    """Final task result."""

    task_id: UUID
    status: TaskStatus
    final_answer: Optional[str] = None
    output_files: List[str] = Field(default_factory=list)
    plan_summary: List[PlanStep] = Field(default_factory=list)
    total_duration_ms: int = 0
    token_usage: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    error: Optional[str] = None


class SSEResponse(BaseModel):
    """SSE event wrapper."""

    event: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data payload")


class FileInfo(BaseModel):
    """File information in workspace."""

    path: str = Field(..., description="Relative file path")
    size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="Creation timestamp")
    is_directory: bool = Field(default=False, description="Is directory")


class TaskFilesResponse(BaseModel):
    """Response with list of task files."""

    task_id: UUID
    files: List[FileInfo] = Field(default_factory=list)


# Admin API Models
class ApiKeyCreateRequest(BaseModel):
    """Request to create an API key."""

    project_name: str = Field(..., description="Project name")
    owner_email: Optional[str] = Field(default=None, description="Owner email")
    rate_limit_rpm: int = Field(default=60, description="Requests per minute")
    rate_limit_rph: int = Field(default=1000, description="Requests per hour")
    concurrent_tasks: int = Field(default=3, description="Max concurrent tasks")
    total_tasks_limit: Optional[int] = Field(default=None, description="Lifetime task limit")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration datetime")


class ApiKeyResponse(BaseModel):
    """API key response (without full key)."""

    id: UUID
    key_prefix: str = Field(..., description="First 8 chars of key for identification")
    project_name: str
    owner_email: Optional[str] = None
    is_active: bool
    rate_limit_rpm: int
    rate_limit_rph: int
    concurrent_tasks: int
    total_tasks_limit: Optional[int] = None
    tasks_used: int = 0
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApiKeyWithSecret(BaseModel):
    """API key with secret (shown once on creation)."""

    id: UUID
    key: str = Field(..., description="The full API key")
    project_name: str
    expires_at: Optional[datetime] = None


class UsageStats(BaseModel):
    """Usage statistics."""

    total_requests: int = 0
    total_tasks: int = 0
    active_keys: int = 0
    tasks_by_status: Dict[str, int] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status")
    redis: str = Field(..., description="Redis connection status")
    llm: str = Field(..., description="LLM connectivity status")
    version: str = Field(default="1.0.0", description="API version")