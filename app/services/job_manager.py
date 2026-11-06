"""In-memory async job manager for multi-core LaTeX compilation with Server-Sent Events (SSE)."""
import os
import uuid
import time
from typing import Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor

_MAX_WORKERS = min(8, max(2, (os.cpu_count() or 4)))
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="latex_worker")

# In-memory job registry: job_id -> dict
_JOBS: Dict[str, Dict[str, Any]] = {}


def create_job(total: int = 1) -> str:
    job_id = str(uuid.uuid4())[:8]
    _JOBS[job_id] = {
        "id": job_id,
        "total": max(1, total),
        "completed": 0,
        "status": "processing",
        "errors": [],
        "created_at": time.time(),
        "result": None,
    }
    return job_id


def get_job(job_id: str) -> Dict[str, Any] | None:
    return _JOBS.get(job_id)


def update_job_progress(job_id: str, increment: int = 1, error: str | None = None):
    job = _JOBS.get(job_id)
    if not job:
        return
    job["completed"] = min(job["total"], job["completed"] + increment)
    if error:
        job["errors"].append(error)


def finish_job(job_id: str, result: Any = None, error: str | None = None):
    job = _JOBS.get(job_id)
    if not job:
        return
    if error:
        job["status"] = "failed"
        job["errors"].append(error)
    else:
        job["status"] = "completed"
        job["completed"] = job["total"]
        job["result"] = result


def submit_background_task(fn: Callable, *args, **kwargs):
    """Run a task in the thread pool without blocking the main event loop."""
    return _executor.submit(fn, *args, **kwargs)
