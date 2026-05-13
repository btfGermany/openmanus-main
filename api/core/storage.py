"""
Task storage and persistence.

Handles task metadata, results, and workspace management.
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from api.config import api_config
from api.models import (
    FileInfo,
    PlanStep,
    TaskMode,
    TaskResult,
    TaskStatus,
    TaskStatusResponse,
    TokenUsage,
)


class TaskStorage:
    """Storage for task metadata and results."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize storage with base path."""
        self.base_path = storage_path or api_config.storage.base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._tasks_meta_file = self.base_path / "_tasks_meta.json"

    def _get_task_path(self, task_id: UUID) -> Path:
        """Get the task workspace path."""
        return self.base_path / str(task_id)

    def _ensure_task_dir(self, task_id: UUID) -> Path:
        """Ensure task directory exists with subdirectories."""
        task_path = self._get_task_path(task_id)
        subdirs = ["data", "reports", "logs", "notes", "sandbox"]
        for subdir in subdirs:
            (task_path / subdir).mkdir(parents=True, exist_ok=True)
        return task_path

    def create_task(
        self,
        task_id: UUID,
        goal: str,
        mode: TaskMode = TaskMode.FLOW,
        timeout_seconds: int = 300,
        max_iterations: int = 20,
        llm_model: Optional[str] = None,
    ) -> Dict:
        """Create a new task."""
        task_path = self._ensure_task_dir(task_id)
        
        metadata = {
            "task_id": str(task_id),
            "goal": goal,
            "mode": mode.value,
            "timeout_seconds": timeout_seconds,
            "max_iterations": max_iterations,
            "llm_model": llm_model,
            "status": TaskStatus.QUEUED.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None,
            "started_at": None,
            "completed_at": None,
            "current_step": None,
            "iteration_count": 0,
            "result": None,
            "error": None,
            "plan": [],
            "token_usage": {},
        }
        
        # Save metadata
        meta_file = task_path / "metadata.json"
        with meta_file.open("w") as f:
            json.dump(metadata, f, indent=2)
        
        # Also add to index
        self._add_to_index(task_id, metadata)
        
        return metadata

    def get_task(self, task_id: UUID) -> Optional[Dict]:
        """Get task metadata."""
        meta_file = self._get_task_path(task_id) / "metadata.json"
        if not meta_file.exists():
            return None
        with meta_file.open() as f:
            return json.load(f)

    def update_task(
        self,
        task_id: UUID,
        status: Optional[TaskStatus] = None,
        current_step: Optional[str] = None,
        iteration_count: Optional[int] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        plan: Optional[List[Dict]] = None,
    ) -> Optional[Dict]:
        """Update task metadata."""
        meta = self.get_task(task_id)
        if not meta:
            return None
        
        if status:
            meta["status"] = status.value
        if current_step is not None:
            meta["current_step"] = current_step
        if iteration_count is not None:
            meta["iteration_count"] = iteration_count
        if started_at:
            meta["started_at"] = started_at.isoformat()
        if completed_at:
            meta["completed_at"] = completed_at.isoformat()
        if result:
            meta["result"] = result
        if error is not None:
            meta["error"] = error
        if plan is not None:
            meta["plan"] = plan
        
        meta["updated_at"] = datetime.utcnow().isoformat()
        
        # Save
        meta_file = self._get_task_path(task_id) / "metadata.json"
        with meta_file.open("w") as f:
            json.dump(meta, f, indent=2)
        
        return meta

    def get_task_status(self, task_id: UUID) -> Optional[TaskStatusResponse]:
        """Get task status response."""
        meta = self.get_task(task_id)
        if not meta:
            return None
        
        return TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus(meta["status"]),
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else None,
            started_at=datetime.fromisoformat(meta["started_at"]) if meta.get("started_at") else None,
            completed_at=datetime.fromisoformat(meta["completed_at"]) if meta.get("completed_at") else None,
            current_step=meta.get("current_step"),
            iteration_count=meta.get("iteration_count", 0),
            goal=meta.get("goal", ""),
        )

    def get_result(self, task_id: UUID) -> Optional[TaskResult]:
        """Get task result."""
        meta = self.get_task(task_id)
        if not meta:
            return None
        
        result_data = meta.get("result", {})
        plan_data = meta.get("plan", [])
        
        # Calculate duration
        total_duration_ms = 0
        if meta.get("started_at") and meta.get("completed_at"):
            start = datetime.fromisoformat(meta["started_at"])
            end = datetime.fromisoformat(meta["completed_at"])
            total_duration_ms = int((end - start).total_seconds() * 1000)
        
        return TaskResult(
            task_id=task_id,
            status=TaskStatus(meta["status"]),
            final_answer=result_data.get("final_answer") if result_data else None,
            output_files=result_data.get("output_files", []) if result_data else [],
            plan_summary=[PlanStep(**step) for step in plan_data],
            total_duration_ms=total_duration_ms,
            token_usage=meta.get("token_usage", {}),
            error=meta.get("error"),
        )

    def list_files(self, task_id: UUID) -> List[FileInfo]:
        """List all files in task workspace."""
        task_path = self._get_task_path(task_id)
        if not task_path.exists():
            return []
        
        files = []
        for path in task_path.rglob("*"):
            if path.is_file():
                stat = path.stat()
                files.append(FileInfo(
                    path=path.relative_to(task_path).as_posix(),
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    is_directory=False,
                ))
        
        return files

    def get_file(self, task_id: UUID, file_path: str) -> Optional[bytes]:
        """Get file contents."""
        task_path = self._get_task_path(task_id)
        full_path = task_path / file_path
        if not full_path.exists() or not full_path.is_file():
            return None
        return full_path.read_bytes()

    def _add_to_index(self, task_id: UUID, metadata: Dict):
        """Add task to index."""
        index = {}
        if self._tasks_meta_file.exists():
            with self._tasks_meta_file.open() as f:
                index = json.load(f)
        
        index[str(task_id)] = {
            "status": metadata["status"],
            "created_at": metadata["created_at"],
        }
        
        with self._tasks_meta_file.open("w") as f:
            json.dump(index, f)

    def list_tasks(self, limit: int = 100, offset: int = 0) -> List[TaskStatusResponse]:
        """List tasks with pagination."""
        tasks = []
        
        if not self.base_path.exists():
            return tasks
        
        for item in sorted(self.base_path.iterdir(), key=lambda x: x.name, reverse=True):
            if not item.is_dir():
                continue
            try:
                task_id = UUID(item.name)
            except ValueError:
                continue
            
            status = self.get_task_status(task_id)
            if status:
                tasks.append(status)
        
        return tasks[offset : offset + limit]

    def cleanup_old_tasks(self, days: int = None) -> int:
        """Clean up old task workspaces."""
        days = days or api_config.storage.cleanup_days
        cutoff = datetime.utcnow() - timedelta(days=days)
        cleaned = 0
        
        if not self.base_path.exists():
            return 0
        
        for item in self.base_path.iterdir():
            if not item.is_dir():
                continue
            try:
                task_id = UUID(item.name)
            except ValueError:
                continue
            
            meta = self.get_task(task_id)
            if not meta:
                continue
            
            # Don't delete failed tasks - keep them for debugging
            if meta["status"] == TaskStatus.FAILED.value:
                continue
            
            # Check age
            created = datetime.fromisoformat(meta["created_at"])
            if created < cutoff:
                shutil.rmtree(item)
                cleaned += 1
        
        return cleaned


# Global instance
task_storage = TaskStorage()