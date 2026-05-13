"""
Background worker for task execution.

RQ worker that processes tasks from Redis queue.
"""

import asyncio
import signal
import sys
import time
from pathlib import Path
from uuid import UUID

import rq
from rq import get_current_job

from api.config import api_config
from api.core.events import EventBus, TaskEvent
from api.core.storage import task_storage
from api.core.wrapper import ManusWrapper
from api.models import TaskMode, TaskStatus


def execute_task(task_id: str, task_data: dict) -> dict:
    """Execute a task in the background worker."""
    task_uuid = UUID(task_id)
    task_meta = task_storage.get_task(task_uuid)
    
    if not task_meta:
        return {"error": "Task not found"}
    
    # Update status to running
    task_storage.update_task(
        task_uuid,
        status=TaskStatus.RUNNING,
        started_at=asyncio.get_event_loop().time(),
    )
    
    # Emit start event
    event_bus = EventBus()
    event_bus.connect()
    
    event_bus.emit(TaskEvent(
        event_type="status",
        task_id=task_uuid,
        data={"status": "running"},
    ))
    
    try:
        # Run the task
        result = asyncio.run(_run_task(
            task_id=task_uuid,
            goal=task_meta["goal"],
            mode=TaskMode(task_meta["mode"]),
            timeout_seconds=task_meta["timeout_seconds"],
            max_iterations=task_meta["max_iterations"],
            llm_model=task_meta.get("llm_model"),
        ))
        
        # Update result
        task_storage.update_task(
            task_uuid,
            status=TaskStatus.COMPLETED,
            completed_at=asyncio.get_event_loop().time(),
            result=result,
        )
        
        return result
    
    except asyncio.TimeoutError:
        task_storage.update_task(
            task_uuid,
            status=TaskStatus.TIMEOUT,
            completed_at=asyncio.get_event_loop().time(),
            error="Task timed out",
        )
        return {"error": "Task timed out"}
    
    except Exception as e:
        task_storage.update_task(
            task_uuid,
            status=TaskStatus.FAILED,
            completed_at=asyncio.get_event_loop().time(),
            error=str(e),
        )
        return {"error": str(e)}
    
    finally:
        event_bus.disconnect()


async def _run_task(
    task_id: UUID,
    goal: str,
    mode: TaskMode,
    timeout_seconds: int,
    max_iterations: int,
    llm_model: str = None,
) -> dict:
    """Run task with async context."""
    async with ManusWrapper(
        task_id=task_id,
        goal=goal,
        mode=mode,
        timeout_seconds=timeout_seconds,
        max_iterations=max_iterations,
        llm_model=llm_model,
    ) as wrapper:
        return await wrapper.run()


def main():
    """Main entry point for worker."""
    import redis
    from rq import Worker
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="OpenManus Task Worker")
    parser.add_argument(
        "--url",
        default=api_config.redis.url,
        help="Redis URL",
    )
    parser.add_argument(
        "--queue",
        default="default",
        help="Queue name",
    )
    args = parser.parse_args()
    
    # Connect to Redis
    redis_conn = redis.from_url(args.url)
    
    # Create worker
    worker = Worker([args.queue], connection=redis_conn)
    
    print(f"Starting worker for queue: {args.queue}")
    print(f"Worker: {worker.name}")
    
    # Run worker with signal handling
    def signal_handler(signum, frame):
        print("Shutdown signal received, cleaning up...")
        worker.request_shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Work
    worker.work()


if __name__ == "__main__":
    main()