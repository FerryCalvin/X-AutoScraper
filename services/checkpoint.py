"""
Checkpoint System for AutoScraper
Enables pause/resume for long-running scraping jobs
"""
import os
import json
import logging
from datetime import datetime

# Checkpoint directory
CHECKPOINT_DIR = 'checkpoints'

# Ensure directory exists
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def save_checkpoint(job_id, data):
    """
    Save checkpoint for resumable scraping.
    
    Args:
        job_id: Job identifier
        data: Dictionary containing job state (tweets, seen_urls, progress, etc.)
    """
    try:
        checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{job_id}.json")
        data['saved_at'] = datetime.now().isoformat()
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logging.debug(f"💾 Checkpoint saved: {job_id}")
    except Exception as e:
        logging.error(f"❌ Failed to save checkpoint {job_id}: {e}")


def load_checkpoint(job_id):
    """
    Load checkpoint if exists.
    
    Args:
        job_id: Job identifier
        
    Returns:
        dict or None: Checkpoint data if exists, None otherwise
    """
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{job_id}.json")
    
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logging.info(f"♻️ Checkpoint loaded: {job_id}")
            return data
        except Exception as e:
            logging.error(f"❌ Failed to load checkpoint {job_id}: {e}")
            return None
    
    return None


def delete_checkpoint(job_id):
    """
    Delete checkpoint after successful completion.
    
    Args:
        job_id: Job identifier
    """
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{job_id}.json")
    
    if os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
            logging.debug(f"🗑️ Checkpoint deleted: {job_id}")
        except Exception as e:
            logging.error(f"❌ Failed to delete checkpoint {job_id}: {e}")


def list_pending_checkpoints():
    """
    List all pending checkpoints for resume.
    
    Returns:
        list: List of checkpoint metadata dicts
    """
    pending = []
    
    if not os.path.exists(CHECKPOINT_DIR):
        return pending
    
    for filename in os.listdir(CHECKPOINT_DIR):
        if filename.endswith('.json'):
            try:
                filepath = os.path.join(CHECKPOINT_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                job_id = filename.replace('.json', '')
                pending.append({
                    'job_id': job_id,
                    'keyword': data.get('base_keyword', 'Unknown'),
                    'progress': f"{data.get('current_chunk_idx', 0)}/{data.get('total_chunks', '?')}",
                    'tweets_collected': len(data.get('all_tweets', [])),
                    'saved_at': data.get('saved_at', 'Unknown'),
                    'worker_mode': data.get('worker_mode', 3)
                })
            except Exception as e:
                logging.error(f"Error reading checkpoint {filename}: {e}")
    
    return pending


def checkpoint_exists(job_id):
    """
    Check if a checkpoint exists for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        bool: True if checkpoint exists
    """
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{job_id}.json")
    return os.path.exists(checkpoint_file)
