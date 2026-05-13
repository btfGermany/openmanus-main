"""
OpenManus wrapper for API integration.

Wraps the existing OpenManus agent for async execution.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

from api.config import api_config
from api.core.events import EventBus, TaskEvent
from api.models import TaskMode, TaskStatus


class ManusWrapper:
    """Wrapper for OpenManus agent execution via API."""

    def __init__(
        self,
        task_id: UUID,
        goal: str,
        mode: TaskMode = TaskMode.FLOW,
        timeout_seconds: int = 300,
        max_iterations: int = 20,
        llm_model: Optional[str] = None,
    ):
        """Initialize wrapper."""
        self.task_id = task_id
        self.goal = goal
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.max_iterations = max_iterations
        self.llm_model = llm_model
        
        self.agent = None
        self.event_bus: Optional[EventBus] = None
        self.started_at: Optional[float] = None
        self.iteration_count = 0

    async def __aenter__(self) -> "ManusWrapper":
        """Async context manager entry."""
        # Import here to avoid circular imports
        from app.agent.manus import Manus
        from app.config import config
        
        # Emit plan created event (placeholder for flow mode)
        if self.mode == TaskMode.FLOW:
            steps = [
                {"id": 1, "description": "Analyze task and create plan", "status": "pending"},
                {"id": 2, "description": "Execute plan steps", "status": "pending"},
                {"id": 3, "description": "Generate final result", "status": "pending"},
            ]
            self.event_bus.plan_created(self.task_id, steps)
        
        # Create workspace directory
        workspace = api_config.storage.base_path / str(self.task_id)
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Set workspace root for config override
        # We'll set environment variable for this task
        import os
        os.environ["WORKSPACE_ROOT"] = str(workspace)
        
        # Create agent - Note: this loads MCP servers from config
        self.agent = await Manus.create()
        
        self.started_at = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Async context manager exit."""
        if self.agent:
            await self.agent.cleanup()
        return False  # Don't suppress exceptions

    async def run(self) -> dict:
        """Run the agent with timeout and event streaming."""
        if not self.agent:
            raise RuntimeError("Agent not initialized. Use async with statement.")
        
        # Emit initial iteration start
        self.event_bus = EventBus()
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                self._execute(),
                timeout=self.timeout_seconds,
            )
            return result
        
        except asyncio.TimeoutError:
            self.event_bus.error(
                self.task_id,
                "TimeoutError",
                f"Task timed out after {self.timeout_seconds}s",
                recoverable=False,
            )
            raise
        
        except Exception as e:
            self.event_bus.error(
                self.task_id,
                type(e).__name__,
                str(e),
                recoverable=False,
            )
            raise

    async def _execute(self) -> dict:
        """Execute the agent."""
        current_step = 0
        
        while current_step < self.max_iterations:
            current_step += 1
            self.iteration_count = current_step
            
            # Emit iteration start
            self.event_bus.iteration_start(
                self.task_id,
                iteration=current_step,
                thought=f"Executing step {current_step}...",
            )
            
            # Process step - this calls think() then act()
            # The actual execution happens inside the agent
            try:
                step_result = await self.agent.step()
                
                # Check if agent is finished
                from app.schema import AgentState
                if self.agent.state == AgentState.FINISHED:
                    break
                
                # Emit observation
                self.event_bus.observation(
                    self.task_id,
                    stdout=step_result,
                )
            
            except Exception as e:
                self.event_bus.error(
                    self.task_id,
                    type(e).__name__,
                    str(e),
                    recoverable=True,
                    retry_count=0,
                )
        
        # Calculate duration
        duration_ms = 0
        if self.started_at:
            duration_ms = int((time.time() - self.started_at) * 1000)
        
        # Generate final result
        final_answer = self._generate_result()
        
        # Emit final result
        output_files = self._get_output_files()
        self.event_bus.final_result(
            self.task_id,
            final_answer=final_answer,
            output_files=output_files,
        )
        
        # Emit done
        self.event_bus.done(
            self.task_id,
            status=TaskStatus.COMPLETED.value,
            total_duration_ms=duration_ms,
        )
        
        return {
            "final_answer": final_answer,
            "output_files": output_files,
            "duration_ms": duration_ms,
        }

    def _generate_result(self) -> str:
        """Generate final result from agent memory."""
        if not self.agent or not self.agent.memory:
            return "Task completed."
        
        messages = self.agent.memory.messages
        if not messages:
            return "Task completed."
        
        # Get last assistant message content
        for msg in reversed(messages):
            if msg.role == "assistant" and msg.content:
                return msg.content
        
        return "Task completed."

    def _get_output_files(self) -> list[str]:
        """Get list of output files from workspace."""
        workspace = api_config.storage.base_path / str(self.task_id)
        reports_dir = workspace / "reports"
        
        if not reports_dir.exists():
            return []
        
        files = []
        for f in reports_dir.iterdir():
            if f.is_file():
                files.append(f"reports/{f.name}")
        
        return files


async def run_task(
    task_id: UUID,
    goal: str,
    mode: TaskMode = TaskMode.FLOW,
    timeout_seconds: int = 300,
    max_iterations: int = 20,
    llm_model: Optional[str] = None,
) -> dict:
    """Run an agent task."""
    async with ManusWrapper(
        task_id=task_id,
        goal=goal,
        mode=mode,
        timeout_seconds=timeout_seconds,
        max_iterations=max_iterations,
        llm_model=llm_model,
    ) as wrapper:
        return await wrapper.run()