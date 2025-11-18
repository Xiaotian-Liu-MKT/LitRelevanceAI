"""Task management for cancellable long-running operations.

This module provides a unified interface for managing cancellable tasks
with proper cleanup and state tracking.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional


class TaskCancelledException(Exception):
    """Raised when a task is cancelled by user."""
    pass


class CancellableTask:
    """Manages a cancellable long-running task.

    Provides thread-safe cancellation with proper cleanup of resources.
    """

    def __init__(self):
        """Initialize a new cancellable task."""
        self.cancelled = threading.Event()
        self.executor: Optional[ThreadPoolExecutor] = None
        self.running = False
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Cancel the task.

        This will:
        1. Set the cancellation flag
        2. Shutdown the executor (if any) without waiting for pending tasks
        3. Mark the task as not running
        """
        with self._lock:
            if not self.running:
                return

            self.cancelled.set()

            # Shutdown executor without waiting for pending tasks
            if self.executor:
                try:
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    # Python < 3.9 doesn't support cancel_futures
                    self.executor.shutdown(wait=False)

            self.running = False

    def check_cancelled(self) -> None:
        """Check if task has been cancelled.

        Raises:
            TaskCancelledException: If the task has been cancelled
        """
        if self.cancelled.is_set():
            raise TaskCancelledException("Task was cancelled by user")

    def is_cancelled(self) -> bool:
        """Check if task is cancelled without raising exception.

        Returns:
            True if task is cancelled, False otherwise
        """
        return self.cancelled.is_set()

    def reset(self) -> None:
        """Reset the task state for reuse.

        Should only be called when the task is not running.
        """
        with self._lock:
            if self.running:
                raise RuntimeError("Cannot reset a running task")

            self.cancelled.clear()
            self.executor = None
            self.running = False

    def start(self) -> None:
        """Mark task as started.

        Should be called at the beginning of task execution.
        """
        with self._lock:
            if self.running:
                raise RuntimeError("Task is already running")

            self.running = True
            self.cancelled.clear()

    def finish(self) -> None:
        """Mark task as finished.

        Should be called when task completes (successfully or with error).
        """
        with self._lock:
            self.running = False

    def run_with_cancellation(
        self,
        func: Callable,
        *args,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        **kwargs
    ) -> threading.Thread:
        """Run a function in a background thread with cancellation support.

        Args:
            func: Function to run
            *args: Positional arguments for func
            on_complete: Callback when task completes successfully (called with result)
            on_error: Callback when task fails (called with exception)
            on_cancel: Callback when task is cancelled
            **kwargs: Keyword arguments for func

        Returns:
            The thread running the task
        """
        def wrapper():
            try:
                self.start()
                result = func(*args, **kwargs)

                if not self.is_cancelled() and on_complete:
                    on_complete(result)

            except TaskCancelledException:
                if on_cancel:
                    on_cancel()

            except Exception as e:
                if not self.is_cancelled() and on_error:
                    on_error(e)

            finally:
                self.finish()

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread


class TaskManager:
    """Manages multiple cancellable tasks.

    Useful for managing tasks across multiple tabs or components.
    """

    def __init__(self):
        """Initialize task manager."""
        self.tasks: dict[str, CancellableTask] = {}
        self._lock = threading.Lock()

    def create_task(self, task_id: str) -> CancellableTask:
        """Create a new task with given ID.

        Args:
            task_id: Unique identifier for the task

        Returns:
            The created CancellableTask
        """
        with self._lock:
            if task_id in self.tasks:
                # Cancel existing task with same ID
                self.tasks[task_id].cancel()

            task = CancellableTask()
            self.tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[CancellableTask]:
        """Get existing task by ID.

        Args:
            task_id: Task identifier

        Returns:
            CancellableTask if found, None otherwise
        """
        with self._lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel task by ID.

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled, False if not found
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.cancel()
                return True
            return False

    def cancel_all(self) -> None:
        """Cancel all active tasks."""
        with self._lock:
            for task in self.tasks.values():
                task.cancel()

    def cleanup_finished(self) -> None:
        """Remove finished tasks from manager."""
        with self._lock:
            finished = [
                task_id for task_id, task in self.tasks.items()
                if not task.running
            ]
            for task_id in finished:
                del self.tasks[task_id]


# Global task manager instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance.

    Returns:
        The global TaskManager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
