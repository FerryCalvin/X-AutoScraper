"""
File Cleanup Utilities for AutoScraper
Handles cleanup of old outputs, temp files, and orphan processes
"""
import os
import glob
import time
import logging
from datetime import datetime, timedelta
from config import OUTPUT


OUTPUT_DIR = OUTPUT.get('directory', 'outputs')


def cleanup_old_outputs(max_age_days=3):
    """
    Delete output files older than max_age_days.
    
    Args:
        max_age_days: Maximum age in days before deletion
    """
    if not os.path.exists(OUTPUT_DIR):
        return
    
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    deleted_count = 0
    
    for filename in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            
            if file_mtime < cutoff_time:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    logging.debug(f"🗑️ Deleted old file: {filename}")
                except Exception as e:
                    logging.error(f"Failed to delete {filename}: {e}")
    
    if deleted_count > 0:
        logging.info(f"🧹 Cleaned up {deleted_count} old output files (>{max_age_days} days)")


def cleanup_temp_files():
    """
    Clean up temporary files from outputs directory.
    Removes temp_*.csv, temp_*.json, and orphan chunk files.
    """
    try:
        temp_patterns = [
            f"{OUTPUT_DIR}/temp_*.csv",
            f"{OUTPUT_DIR}/temp_*.json",
            "chunked_*.csv",  # Orphan chunks in root
        ]
        
        deleted_count = 0
        for pattern in temp_patterns:
            for temp_file in glob.glob(pattern):
                try:
                    os.remove(temp_file)
                    deleted_count += 1
                    logging.debug(f"🗑️ Cleaned temp file: {temp_file}")
                except Exception as e:
                    logging.error(f"Failed to delete temp file {temp_file}: {e}")
        
        if deleted_count > 0:
            logging.info(f"🧹 Cleaned up {deleted_count} temp files")
            
    except Exception as e:
        logging.warning(f"⚠️ Cleanup warning: {e}")


def cleanup_chrome_processes():
    """
    Kill any orphaned Chrome/Chromedriver processes.
    Windows-specific implementation.
    """
    try:
        os.system('taskkill /F /IM chromedriver.exe >nul 2>&1')
        os.system('taskkill /F /IM chrome.exe >nul 2>&1')
    except Exception as e:
        logging.warning(f"Chrome cleanup warning: {e}")


def ensure_output_dir():
    """Ensure output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR
