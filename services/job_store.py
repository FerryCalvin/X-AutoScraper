"""
In-Memory Job Store for AutoScraper
Thread-safe job tracking without database dependency
"""
import threading
import logging
from datetime import datetime


# In-memory job storage
JOBS = {}  # {job_id: {keyword, target_count, status, progress, result_file, created_at, worker_mode}}
JOBS_LOCK = threading.Lock()


def add_job(job_id, keyword, target_count, worker_mode=3):
    """
    Add a new job to in-memory store.
    
    Args:
        job_id: Unique job identifier
        keyword: Search keyword(s)
        target_count: Target number of tweets
        worker_mode: Number of parallel workers (1, 3, or 5)
    """
    with JOBS_LOCK:
        JOBS[job_id] = {
            'id': job_id,
            'keyword': keyword,
            'target_count': target_count,
            'status': 'RUNNING',
            'progress': 'Starting...',
            'result_file': None,
            'created_at': datetime.now().isoformat(),
            'worker_mode': worker_mode
        }
    logging.info(f"📝 Job added: {job_id} ({keyword})")


def update_job_status(job_id, status, progress=None, result_file=None):
    """
    Update job status in memory.
    
    Args:
        job_id: Job identifier
        status: New status (RUNNING, COMPLETED, FAILED)
        progress: Optional progress message
        result_file: Optional result filename
    """
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]['status'] = status
            if progress:
                JOBS[job_id]['progress'] = progress
            if result_file:
                JOBS[job_id]['result_file'] = result_file


def get_job(job_id):
    """
    Get a single job by ID.
    
    Args:
        job_id: Job identifier
        
    Returns:
        dict or None: Job data if found
    """
    with JOBS_LOCK:
        return JOBS.get(job_id)


def get_all_jobs():
    """
    Get all jobs for UI display.
    
    Returns:
        list: List of all job dictionaries
    """
    with JOBS_LOCK:
        return list(JOBS.values())


def remove_job(job_id):
    """
    Remove job from memory (after completion/cleanup).
    
    Args:
        job_id: Job identifier
    """
    with JOBS_LOCK:
        if job_id in JOBS:
            del JOBS[job_id]
            logging.info(f"🗑️ Job removed: {job_id}")


def job_exists(job_id):
    """
    Check if a job exists.
    
    Args:
        job_id: Job identifier
        
    Returns:
        bool: True if job exists
    """
    with JOBS_LOCK:
        return job_id in JOBS


def get_job_count():
    """
    Get total number of active jobs.
    
    Returns:
        int: Number of jobs
    """
    with JOBS_LOCK:
        return len(JOBS)
