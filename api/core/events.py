"""
Event bus for task events using Redis Pub/Sub.

Handles real-time event streaming between workers and API.
"""

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

import redis

from api.config import api_config


@dataclass
class TaskEvent:
    """Base task event."""

    event_type: str
    task_id: UUID
    data: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_json(self) -> str:
        """Serialize to JSON for SSE."""
        return json.dumps({
            "event": self.event_type,
            "data": self.data,
        })

    def to_redis(self) -> str:
        """Serialize for Redis Pub/Sub."""
        return json.dumps({
            "event_type": self.event_type,
            "task_id": str(self.task_id),
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        })

    @classmethod
    def from_redis(cls, data: str) -> "TaskEvent":
        """Deserialize from Redis."""
        obj = json.loads(data)
        return cls(
            event_type=obj["event_type"],
            task_id=UUID(obj["task_id"]),
            data=obj["data"],
            timestamp=datetime.fromisoformat(obj["timestamp"]),
        )


class EventBus:
    """Redis Pub/Sub event bus for task events."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._channels: Dict[str, Callable] = {}
        self._local_listeners: Dict[UUID, List[Callable]] = {}

    def connect(self):
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(
                api_config.redis.url,
                decode_responses=False,  # We'll handle encoding
            )
        return self._redis

    def disconnect(self):
        """Disconnect from Redis."""
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None
        if self._redis:
            self._redis.close()
            self._redis = None

    def _get_channel_name(self, task_id: UUID) -> str:
        """Get channel name for task."""
        return f"task:{task_id}:events"

    def publish(self, event: TaskEvent):
        """Publish an event to the task channel."""
        redis_client = self.connect()
        channel = self._get_channel_name(event.task_id)
        redis_client.publish(channel, event.to_redis())

    def subscribe(self, task_id: UUID, callback: Callable[[TaskEvent], None]):
        """Subscribe to task events (local listener)."""
        if task_id not in self._local_listeners:
            self._local_listeners[task_id] = []
        self._local_listeners[task_id].append(callback)

    def unsubscribe(self, task_id: UUID, callback: Callable[[TaskEvent], None] = None):
        """Unsubscribe from task events."""
        if task_id not in self._local_listeners:
            return
        
        if callback is None:
            self._local_listeners[task_id].clear()
        else:
            self._local_listeners[task_id].remove(callback)
        
        if not self._local_listeners[task_id]:
            del self._local_listeners[task_id]

    def emit(self, event: TaskEvent):
        """Emit event to local listeners."""
        if event.task_id in self._local_listeners:
            for callback in self._local_listeners[event.task_id]:
                try:
                    callback(event)
                except Exception:
                    pass  # Log in production

    # Convenience methods for creating events
    def plan_created(self, task_id: UUID, steps: List[Dict]):
        """Emit plan created event."""
        self.emit(TaskEvent(
            event_type="plan_created",
            task_id=task_id,
            data={"task_id": str(task_id), "steps": steps},
        ))

    def iteration_start(self, task_id: UUID, iteration: int, thought: str):
        """Emit iteration start event."""
        self.emit(TaskEvent(
            event_type="iteration_start",
            task_id=task_id,
            data={"iteration": iteration, "thought": thought},
        ))

    def tool_call(self, task_id: UUID, tool: str, input_data: str):
        """Emit tool call event."""
        self.emit(TaskEvent(
            event_type="tool_call",
            task_id=task_id,
            data={
                "tool": tool,
                "input": input_data,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ))

    def tool_result(self, task_id: UUID, tool: str, output: str, duration_ms: int):
        """Emit tool result event."""
        self.emit(TaskEvent(
            event_type="tool_result",
            task_id=task_id,
            data={
                "tool": tool,
                "output": output[:10000],  # Truncate for streaming
                "duration_ms": duration_ms,
            },
        ))

    def observation(self, task_id: UUID, stdout: str = "", stderr: str = "", exit_code: int = 0):
        """Emit observation event."""
        self.emit(TaskEvent(
            event_type="observation",
            task_id=task_id,
            data={
                "stdout": stdout[:5000],
                "stderr": stderr[:5000],
                "exit_code": exit_code,
            },
        ))

    def error(
        self,
        task_id: UUID,
        error_class: str,
        message: str,
        recoverable: bool = False,
        retry_count: int = 0,
    ):
        """Emit error event."""
        self.emit(TaskEvent(
            event_type="error",
            task_id=task_id,
            data={
                "error_class": error_class,
                "message": message,
                "recoverable": recoverable,
                "retry_count": retry_count,
            },
        ))

    def plan_update(self, task_id: UUID, step_id: int, status: str):
        """Emit plan update event."""
        self.emit(TaskEvent(
            event_type="plan_update",
            task_id=task_id,
            data={"step_id": step_id, "status": status},
        ))

    def final_result(self, task_id: UUID, final_answer: str = None, output_files: List[str] = None):
        """Emit final result event."""
        self.emit(TaskEvent(
            event_type="final_result",
            task_id=task_id,
            data={
                "final_answer": final_answer,
                "output_files": output_files or [],
            },
        ))

    def done(self, task_id: UUID, status: str, total_duration_ms: int):
        """Emit done event."""
        self.emit(TaskEvent(
            event_type="done",
            task_id=task_id,
            data={
                "status": status,
                "total_duration_ms": total_duration_ms,
            },
        ))


# Global instance
event_bus = EventBus()