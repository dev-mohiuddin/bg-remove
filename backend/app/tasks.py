"""
Async task manager for background-removal jobs.

Uses a thread pool for CPU/GPU-bound work and an in-memory store for
task status. This avoids the overhead of Celery+Redis for a single-GPU
serverless deployment while still providing non-blocking processing with
real-time progress via Server-Sent Events.

For multi-instance deployments, swap TaskStore for a Redis-backed store.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Task:
    id: str
    status: TaskStatus = TaskStatus.PENDING
    stage: str = "queued"
    progress: float = 0.0
    result: Optional[bytes] = None
    mask_result: Optional[bytes] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    # For SSE: a list of events that subscribers can drain.
    _events: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, stage: str, progress: float, status: TaskStatus | None = None):
        with self._lock:
            self.stage = stage
            self.progress = progress
            if status is not None:
                self.status = status
            self._events.append({
                "stage": stage,
                "progress": progress,
                "status": self.status.value,
                "ts": time.time(),
            })

    def drain_events(self) -> list[dict]:
        with self._lock:
            evts = self._events[:]
            self._events.clear()
            return evts


class TaskStore:
    """Thread-safe in-memory task store."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def create(self) -> Task:
        task_id = uuid.uuid4().hex[:12]
        task = Task(id=task_id)
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def remove(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)

    def cleanup_old(self, max_age_seconds: int = 3600):
        """Remove completed tasks older than max_age_seconds."""
        now = time.time()
        with self._lock:
            stale = [
                tid for tid, t in self._tasks.items()
                if t.completed_at and (now - t.completed_at) > max_age_seconds
            ]
            for tid in stale:
                del self._tasks[tid]


# Global singleton.
store = TaskStore()

# Thread pool for concurrent GPU jobs.
_executor: Optional[threading.Thread] = None


def submit_task(image_bytes: bytes, filename: str = "image.png") -> Task:
    """
    Submit a background-removal task for asynchronous processing.
    Returns immediately with a Task object.
    """
    task = store.create()

    def worker():
        try:
            task.update("loading", 0.02, TaskStatus.PROCESSING)

            from .processor import process_image

            def progress_cb(stage: str, frac: float):
                task.update(stage, frac)

            result = process_image(image_bytes, progress_cb=progress_cb)
            task.result = result
            task.completed_at = time.time()
            task.update("done", 1.0, TaskStatus.DONE)
            logger.info("Task %s completed", task.id)
        except Exception as exc:
            logger.exception("Task %s failed", task.id)
            task.error = str(exc)
            task.completed_at = time.time()
            task.update("error", 0.0, TaskStatus.ERROR)

    thread = threading.Thread(target=worker, daemon=True, name=f"task-{task.id}")
    thread.start()
    return task


def submit_mask_task(image_bytes: bytes) -> Task:
    """Submit a mask-only extraction task (for the frontend touch-up tool)."""
    task = store.create()

    def worker():
        try:
            task.update("loading", 0.05, TaskStatus.PROCESSING)
            from .processor import process_image_to_mask
            mask = process_image_to_mask(image_bytes)
            task.mask_result = mask
            task.completed_at = time.time()
            task.update("done", 1.0, TaskStatus.DONE)
        except Exception as exc:
            logger.exception("Mask task %s failed", task.id)
            task.error = str(exc)
            task.completed_at = time.time()
            task.update("error", 0.0, TaskStatus.ERROR)

    thread = threading.Thread(target=worker, daemon=True, name=f"mask-{task.id}")
    thread.start()
    return task