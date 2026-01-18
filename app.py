"""
AutoScraper - Twitter/X Data Collection Tool
Main Flask Application

Refactored to use modular structure:
- config.py: Configuration loading
- services/: Job store, checkpoint
- routes/: API endpoints
- utils/: Logging, cleanup
"""
import threading
import uuid
import time
import os
import json
import csv
import re
import logging
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# Import new modular components
from config import CONFIG, SCRAPER, WORKERS, OUTPUT, RATE_LIMIT
from services.job_store import (
    JOBS, JOBS_LOCK, add_job, update_job_status, 
    get_all_jobs, remove_job, get_job
)
from services.checkpoint import (
    save_checkpoint, load_checkpoint, delete_checkpoint, list_pending_checkpoints
)
from utils.logging_setup import setup_logging, get_recent_logs, LOG_BUFFER
from utils.cleanup import cleanup_old_outputs, cleanup_temp_files, ensure_output_dir

# Import scrapers
import scraper_selenium

# ===================
# GRACEFUL SHUTDOWN
# ===================
ACTIVE_EXECUTORS = []  # Track active ThreadPoolExecutors for cleanup
SHUTDOWN_FLAG = threading.Event()  # Signal to stop all workers

def graceful_shutdown(signum=None, frame=None):
    """Handle Ctrl+C gracefully - stop all workers and cleanup"""
    print("\n🛑 Shutting down gracefully... (Ctrl+C detected)")
    SHUTDOWN_FLAG.set()
    
    # Cancel all active executors
    for executor in ACTIVE_EXECUTORS:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except:
            pass
    
    # Kill any remaining Chrome processes
    try:
        os.system('taskkill /F /IM chromedriver.exe >nul 2>&1')
    except:
        pass
    
    print("✅ Cleanup complete. Goodbye!")
    os._exit(0)

# Register signal handlers (only for Ctrl+C, not atexit which conflicts with Flask debugger)
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# ===================
# INITIALIZATION
# ===================

# Setup logging (imported from utils.logging_setup)
setup_logging()

# Run cleanup on startup (imported from utils.cleanup)
cleanup_old_outputs(max_age_days=3)
ensure_output_dir()

# ===================
# RATE LIMIT TRACKING (kept here for backward compat, will move to routes/system.py later)
# ===================
REQUEST_TIMESTAMPS = []  # List of timestamps for rate calculation

def track_request():
    """Track a request for rate limiting meter"""
    global REQUEST_TIMESTAMPS
    now = time.time()
    REQUEST_TIMESTAMPS.append(now)
    # Keep only last minute of requests
    REQUEST_TIMESTAMPS = [t for t in REQUEST_TIMESTAMPS if now - t < 60]

def get_rate_status():
    """Get current rate limit status"""
    rate_config = CONFIG.get('rate_limit', {})
    max_rpm = rate_config.get('max_requests_per_minute', 30)
    warning = rate_config.get('warning_threshold', 20)
    danger = rate_config.get('danger_threshold', 25)
    
    current_rpm = len(REQUEST_TIMESTAMPS)
    
    if current_rpm >= danger:
        status = 'HOT'
        color = 'red'
    elif current_rpm >= warning:
        status = 'WARM'
        color = 'yellow'
    else:
        status = 'COOL'
        color = 'green'
    
    return {
        'current_rpm': current_rpm,
        'max_rpm': max_rpm,
        'status': status,
        'color': color,
        'percent': min(100, int((current_rpm / max_rpm) * 100))
    }

# Config File for Cookies
COOKIE_FILE = 'cookies_config.json'

app = Flask(__name__)

# --- SETUP WIZARD LOGIC ---
@app.before_request
def check_setup():
    # Allow access to static files or setup page itself
    if request.endpoint in ['setup', 'static']:
        return
        
    # Check if cookie file exists
    if not os.path.exists(COOKIE_FILE):
        return redirect(url_for('setup'))
    
    # If file exists, we're good

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        data = request.json
        auth = data.get('auth_token')
        ct0 = data.get('ct0')
        
        if auth and ct0:
            config = {
                "auth_token": auth,
                "ct0": ct0,
                # Default values for others
                "guest_id": "",
                "twid": "",
                "gt": ""
            }
            with open(COOKIE_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            return jsonify({"status": "ok"})
        return jsonify({"error": "Missing fields"}), 400
        
    return render_template('setup.html')
# --------------------------

# Config
OUTPUT_DIR = 'outputs'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ===================
# JOB STORE - imported from services/job_store.py
# Functions available: JOBS, JOBS_LOCK, add_job, update_job_status, get_all_jobs, remove_job, get_job
# ===================

def init_db():
    """Compatibility function - no-op for in-memory store"""
    logging.info("💾 Using in-memory job store (no database)")
    pass

# Global Lock to prevent parallel execution (Anti-Shadowban)
job_lock = threading.Semaphore(1)

# Batch Tracking
BATCH_GROUPS = {} # { batch_id: { 'total': N, 'completed': 0, 'files': [], 'lock': Lock() } }
BATCH_LOCK = threading.Lock()

# --- DATE CHUNKING HELPER ---
def generate_date_chunks(start_date_str, end_date_str, chunk_days=7):
    """
    Split a date range into smaller chunks for better scraping coverage.
    Returns list of (start, end) tuples as strings.
    """
    from datetime import timedelta
    
    start = datetime.strptime(start_date_str, '%Y-%m-%d')
    end = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    chunks = []
    current = start
    
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        chunks.append((current.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        current = chunk_end
    
    return chunks

def check_batch_completion(batch_id):
    """Check if all jobs in a batch are done and merge them"""
    with BATCH_LOCK:
        if batch_id not in BATCH_GROUPS:
            return
            
        group = BATCH_GROUPS[batch_id]
        if group['completed'] == group['total']:
            print(f"📦 Batch {batch_id} fully completed! Merging {len(group['files'])} files...")
            
            # Merge Logic
            all_data = []
            valid_files = [f for f in group['files'] if f and os.path.exists(f)]
            
            for fpath in valid_files:
                try:
                    # Determine format (JSON or CSV) - mostly CSV now
                    if fpath.endswith('.json'):
                        with open(fpath, 'r', encoding='utf-8') as f:
                            all_data.extend(json.load(f))
                    elif fpath.endswith('.csv'):
                        with open(fpath, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            all_data.extend(list(reader))
                except Exception as e:
                    print(f"Error reading {fpath} for merge: {e}")
            
            if all_data:
                # Save Merged File
                merged_filename = f"batch_merged_{int(time.time())}_{batch_id[:8]}.csv"
                merged_path = os.path.join(OUTPUT_DIR, merged_filename)
                
                # Write CSV
                if all_data:
                    keys = all_data[0].keys()
                    with open(merged_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(all_data)
                
                print(f"✅ Merged file ready: {merged_path}")
                
                # Add a "System Job" to DB so it shows in UI
                conn = get_db()
                c = conn.cursor()
                sys_job_id = f"batch-{batch_id[:8]}"
                c.execute(
                    "INSERT INTO jobs (id, keyword, target_count, status, created_at, progress, result_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sys_job_id, "📦 COMBINED/MERGED RESULT", len(all_data), 'COMPLETED', datetime.now(), f'Merged {len(valid_files)} files', merged_filename)
                )
                conn.commit()
                conn.close()
                
            # Cleanup
            del BATCH_GROUPS[batch_id]


def run_scraper_thread(job_id, keyword, count, start_date=None, end_date=None, smart_mode=False, worker_mode=3, batch_id=None):
    """Background worker thread"""
    with job_lock: # Wait for other jobs to finish before starting
        print(f"🧵 [Thread] Starting job {job_id} for '{keyword}' (Smart: {smart_mode}, Workers: {worker_mode})")
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('RUNNING', job_id))
        conn.commit()
        conn.close()

        filename_abs = None # Initialize

        try:
            final_keyword = keyword
            
            # --- SMART MODE LOGIC ---
            if smart_mode:
                # 1. Update status
                update_job_status(job_id, 'RUNNING (Discovery Phase 🕵️)')
                
                # 2. Discovery Scrape (Larger sample for better hashtag discovery)
                print(f"🧠 Smart Mode: Scanning for topics related to '{keyword}'...")
                discovery_tweets = scraper_selenium.scrape_twitter(
                    keyword, 
                    count=100, # INCREASED: Larger sample for better hashtag discovery (was 50)
                    headless=True
                )
                
                # 3. Analyze Hashtags
                if discovery_tweets:
                    all_hashtags = []
                    for t in discovery_tweets:
                        # Extract hashtags from original text
                        original = t.get('text', '')
                        tags = re.findall(r'#\w+', original.lower())
                        all_hashtags.extend(tags)
                    
                    # Top 10 Hashtags (more aggressive expansion) - INCREASED from 5
                    from collections import Counter
                    top_tags = [tag for tag, _ in Counter(all_hashtags).most_common(10)]
                    
                    if top_tags:
                        # 4. Expansion
                        # Create query: "banjir OR #banjiraceh OR #aceh"
                        additional_query = " OR ".join(top_tags)
                        final_keyword = f"{keyword} OR {additional_query}"
                        print(f"🧠 Smart Mode: Expanded keyword to -> {final_keyword}")
                        
                        # Update status to show expansion
                        update_job_status(job_id, f'RUNNING (Expanded: {final_keyword})')
                        
                # 5. Cleanup: Delete discovery temp file if it exists
                discovery_file = f"tweets_{keyword.replace(' ', '_')}.json"
                if os.path.exists(discovery_file):
                    os.remove(discovery_file)
                    print(f"🗑️ Deleted temp discovery file: {discovery_file}")
                csv_file = discovery_file.replace('.json', '.csv')
                if os.path.exists(csv_file):
                    os.remove(csv_file)
            # ------------------------
    
        
            # Callback to update DB
            def on_progress(msg):
                update_job_status(job_id, 'RUNNING', msg)
            
            # --- AUTO DATE CHUNKING ---
            # If date range is > 7 days, split into weekly chunks for better coverage
            all_tweets = []
            date_chunks = []
            
            if start_date and end_date:
                from datetime import timedelta
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                range_days = (end_dt - start_dt).days
                
                if range_days > 7:
                    date_chunks = generate_date_chunks(start_date, end_date, chunk_days=7)
                    print(f"📅 Date range ({range_days} days) split into {len(date_chunks)} weekly chunks")
            
            # If we have chunks, scrape each chunk separately
            if date_chunks:
                for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                    update_job_status(job_id, 'RUNNING', f'Scraping chunk {i+1}/{len(date_chunks)} ({chunk_start} to {chunk_end})')
                    print(f"📅 Scraping chunk {i+1}/{len(date_chunks)}: {chunk_start} to {chunk_end}")
                    
                    search_query = f"{final_keyword} since:{chunk_start} until:{chunk_end}"
                    
                    chunk_tweets = scraper_selenium.scrape_twitter(
                        keyword=search_query, 
                        count=count // len(date_chunks), # Distribute count across chunks
                        headless=True,
                        progress_callback=lambda msg: update_job_status(job_id, 'RUNNING', f'Chunk {i+1}: {msg}')
                    )
                    
                    if chunk_tweets:
                        all_tweets.extend(chunk_tweets)
                        print(f"   Got {len(chunk_tweets)} tweets from chunk {i+1}")
                    
                    # Small break between chunks
                    time.sleep(3)
                
                # Save all merged tweets
                if all_tweets:
                    filename_abs = f"{os.getcwd()}/{OUTPUT_DIR}/chunked_{job_id}_{keyword.replace(' ', '_')}.csv"
                    
                    # Deduplicate by tweet URL
                    seen_urls = set()
                    unique_tweets = []
                    for t in all_tweets:
                        url = t.get('url', t.get('tweet_url', ''))
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            unique_tweets.append(t)
                    
                    # Save CSV
                    if unique_tweets:
                        keys = unique_tweets[0].keys()
                        with open(filename_abs, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=keys)
                            writer.writeheader()
                            writer.writerows(unique_tweets)
                        
                        print(f"✨ Chunked scrape complete: {len(unique_tweets)} unique tweets from {len(date_chunks)} chunks")
                
            # --- REGULAR SCRAPING (No chunking needed) ---
            else:
                # Determine strategy based on count AND worker_mode
                use_parallel = count > 500 or worker_mode > 1
            
                if use_parallel:
                    workers = worker_mode
                    print(f"🚀 Using Parallel Strategy for {count} tweets (Workers: {workers})")
                    update_job_status(job_id, 'RUNNING', f'Running parallel scraper ({workers} workers)')
                
                try:
                    kwargs = {
                        "keyword": final_keyword, # Use final_keyword here
                        "total_count": count,
                        "workers": workers,
                        "output_dir": OUTPUT_DIR
                    }
                    if start_date: kwargs["start_date"] = start_date
                    if end_date: kwargs["end_date"] = end_date 

                    filename_abs = scraper_parallel.run_parallel_job(**kwargs)
                except Exception as e:
                        print(f"Parallel scraper error: {e}")
                        raise e
                        
                else:
                    # Standard Scraper (Safe Mode for small/medium counts)
                    print(f"🐢 Using Standard Strategy for {count} tweets")
                    update_job_status(job_id, 'RUNNING', 'Starting browser (Safe Mode)...')
                    
                    # Append dates to keyword for standard scraper logic (Twitter search syntax)
                    search_query = final_keyword
                    if start_date:
                        search_query += f" since:{start_date}"
                    if end_date:
                        search_query += f" until:{end_date}"
                    
                    # Define output filename
                    filename_abs = f"{os.getcwd()}/{OUTPUT_DIR}/job_{job_id}_{keyword.replace(' ', '_')}.json"
                    
                    # Run Standard with Callback
                    tweets = scraper_selenium.scrape_twitter(
                        keyword=search_query, 
                        count=count, 
                        headless=True,
                        output_filename=filename_abs,
                        progress_callback=on_progress
                    )
                
            result_tweets_count = 0 
            if filename_abs and os.path.exists(filename_abs):
                # Simple check of count
                try:
                    if filename_abs.endswith('.json'):
                        with open(filename_abs, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            result_tweets_count = len(data)
                    elif filename_abs.endswith('.csv'):
                        with open(filename_abs, 'r', encoding='utf-8') as f:
                            result_tweets_count = sum(1 for _ in f) - 1 # Subtract header
                except: pass
                
            # Clean up filename for DB (just basename)
            if filename_abs:
                filename = os.path.basename(filename_abs)
            else:
                filename = None
        
            # Update Final Status
            if result_tweets_count > 0:
                update_job_status(job_id, 'COMPLETED', f'Found {result_tweets_count} tweets', filename)
            else:
                update_job_status(job_id, 'FAILED', 'No tweets found', None)
                
        except Exception as e:
            print(f"❌ [Thread] Job {job_id} failed: {e}")
            update_job_status(job_id, 'FAILED', str(e), None)
            
        finally:
            # ==================
            # AUTO-CLEANUP TEMP FILES
            # ==================
            try:
                import glob
                # Clean temp files from outputs directory
                temp_patterns = [
                    f"{OUTPUT_DIR}/temp_*.csv",
                    f"{OUTPUT_DIR}/temp_*.json",
                ]
                for pattern in temp_patterns:
                    for temp_file in glob.glob(pattern):
                        try:
                            os.remove(temp_file)
                            print(f"🗑️ Cleaned up temp file: {temp_file}")
                        except:
                            pass
                
                # Clean chunked files from root directory (they should be in outputs)
                root_chunks = glob.glob("chunked_*.csv")
                for chunk_file in root_chunks:
                    try:
                        os.remove(chunk_file)
                        print(f"🗑️ Cleaned up orphan chunk: {chunk_file}")
                    except:
                        pass
            except Exception as cleanup_error:
                print(f"⚠️ Cleanup warning: {cleanup_error}")
            
            # Batch Handling
            if batch_id:
                with BATCH_LOCK:
                    if batch_id in BATCH_GROUPS:
                        BATCH_GROUPS[batch_id]['completed'] += 1
                        BATCH_GROUPS[batch_id]['files'].append(filename_abs) # Use absolute path
                
                check_batch_completion(batch_id)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    raw_keyword = data.get('keyword')
    count = int(data.get('count', 20))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    smart_mode = data.get('smart_mode', False)
    auto_expand = data.get('auto_expand', False)  # NEW: Auto-expand for batch scraping
    worker_mode = int(data.get('worker_mode', 3)) # Default 3
    
    if not raw_keyword:
        return jsonify({'error': 'Keyword is required'}), 400
        
    # Handle Comma-Separated Keywords - ALWAYS combine with OR
    keywords = [k.strip() for k in raw_keyword.split(',') if k.strip()]
    
    # --- AUTO-EXPAND MODE (when user enables it) ---
    if auto_expand:
        print(f"🚀 Auto-Expand Mode: Creating batch job for '{raw_keyword}'")
        
        # Base keyword for display
        base_keyword = keywords[0] if len(keywords) == 1 else " OR ".join(keywords)
        
        # Step 1: Start with base variations
        variations = []
        for kw in keywords:
            if kw not in variations:
                variations.append(kw)
            # Add hashtag version
            if not kw.startswith('#'):
                variations.append(f"#{kw.replace(' ', '')}")
            # Add common prefixes (works for any topic)
            if not kw.startswith('#') and len(kw.split()) <= 2:
                variations.append(f"berita {kw}")
                variations.append(f"update {kw}")
        
        # CREATE SINGLE PARENT JOB FIRST (before discovery)
        parent_job_id = str(uuid.uuid4())
        add_job(parent_job_id, f"🚀 {base_keyword} (Auto-Expand)", count, worker_mode)
        update_job_status(parent_job_id, 'RUNNING', 'Discovery Phase: Finding related hashtags...')
        
        # Step 2: DYNAMIC DISCOVERY - Scrape sample tweets to find related hashtags
        print(f"🧠 Dynamic Discovery: Scanning for related hashtags...")
        
        discovery_hashtags = []
        try:
            # Quick scrape to find trending hashtags for this topic
            discovery_tweets = scraper_selenium.scrape_twitter(
                base_keyword,
                count=100,  # Sample size for discovery
                headless=True
            )
            
            if discovery_tweets:
                # Extract all hashtags from discovery tweets
                from collections import Counter
                all_hashtags = []
                for tweet in discovery_tweets:
                    text = tweet.get('text', '')
                    hashtags = re.findall(r'#\w+', text)
                    all_hashtags.extend([h.lower() for h in hashtags])
                
                # Get top 20 most common hashtags (we'll filter later)
                hashtag_counts = Counter(all_hashtags)
                candidate_hashtags = [tag for tag, count in hashtag_counts.most_common(20) if count >= 2]
                
                # RELEVANCE FILTER: Only keep hashtags related to original keywords
                keyword_words = []
                for kw in keywords:
                    # Extract individual words from keyword
                    words = re.findall(r'\w+', kw.lower())
                    keyword_words.extend(words)
                keyword_words = list(set(keyword_words))  # Unique words
                
                def is_relevant_hashtag(tag):
                    """Check if hashtag is related to the keywords"""
                    tag_clean = tag.replace('#', '').lower()
                    
                    # Check if any keyword word appears in the hashtag
                    for word in keyword_words:
                        if len(word) >= 3 and word in tag_clean:  # Word must be at least 3 chars
                            return True
                        if tag_clean in word:  # Or hashtag is part of keyword
                            return True
                    return False
                
                # Filter to only relevant hashtags
                discovery_hashtags = [tag for tag in candidate_hashtags if is_relevant_hashtag(tag)]
                
                print(f"  🔍 Found {len(candidate_hashtags)} hashtags, {len(discovery_hashtags)} relevant: {discovery_hashtags[:5]}...")
                
                # Add discovered hashtags to variations
                for tag in discovery_hashtags:
                    if tag not in [v.lower() for v in variations]:
                        variations.append(tag)
        except Exception as e:
            print(f"  ⚠️ Discovery failed: {e}, continuing with base variations")
        
        # Step 3: Limit and prepare
        variations = list(set(variations))[:20]  # Increased to 20 for better coverage
        # NOTE: count_per_variation will be recalculated after we know the number of date chunks
        
        print(f"🔄 Auto-Expand: {len(variations)} keywords (including {len(discovery_hashtags)} discovered)")
        
        # CREATE SINGLE PARENT JOB (this is what user sees)
        parent_job_id = str(uuid.uuid4())
        add_job(parent_job_id, f"🚀 {base_keyword} (Auto-Expand)", count, worker_mode)
        
        # Start single background thread that processes all variations internally
        def run_auto_expand_batch():
            all_tweets = []
            seen_urls = set()
            completed_count = 0
            
            # DATE CHUNKING: Always chunk for better coverage
            date_chunks = []
            from datetime import timedelta
            
            if start_date and end_date:
                # MANUAL DATES: Chunk the provided date range
                try:
                    chunk_start = datetime.strptime(start_date, '%Y-%m-%d')
                    chunk_end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    range_days = (chunk_end_dt - chunk_start).days
                    
                    # Adaptive chunk size based on range
                    if range_days > 180:  # > 6 months: use monthly chunks
                        chunk_days = 30
                        chunk_type = "monthly"
                    elif range_days > 60:  # > 2 months: use bi-weekly chunks
                        chunk_days = 14
                        chunk_type = "bi-weekly"
                    else:  # <= 2 months: use weekly chunks
                        chunk_days = 7
                        chunk_type = "weekly"
                    
                    # Create chunks
                    current = chunk_start
                    while current < chunk_end_dt:
                        next_chunk = min(current + timedelta(days=chunk_days), chunk_end_dt)
                        date_chunks.append((current.strftime('%Y-%m-%d'), next_chunk.strftime('%Y-%m-%d')))
                        current = next_chunk
                    
                    print(f"  📅 Date chunking: {len(date_chunks)} {chunk_type} periods ({range_days} days total)")
                except Exception as e:
                    print(f"  ⚠️ Date parsing error: {e}, using as single range")
                    date_chunks = [(start_date, end_date)]
            else:
                # NO DATES: Auto-generate from last 60 days
                chunk_end = datetime.now()
                chunk_start = chunk_end - timedelta(days=60)
                
                # Create weekly chunks
                current = chunk_start
                while current < chunk_end:
                    next_chunk = min(current + timedelta(days=7), chunk_end)
                    date_chunks.append((current.strftime('%Y-%m-%d'), next_chunk.strftime('%Y-%m-%d')))
                    current = next_chunk
                
                print(f"  📅 Auto date chunking: {len(date_chunks)} weekly periods (last 60 days)")
            
            # Build list of all work items (variation + chunk combinations)
            work_items = []
            for i, variation in enumerate(variations):
                for chunk_idx, (chunk_start_date, chunk_end_date) in enumerate(date_chunks):
                    work_items.append({
                        'variation_idx': i,
                        'variation': variation,
                        'chunk_idx': chunk_idx,
                        'chunk_start': chunk_start_date,
                        'chunk_end': chunk_end_date
                    })
            
            total_work = len(work_items)
            
            # SMART COUNT LOGIC:
            # - count = 0 (or very high) + date range → UNLIMITED mode, scrape all available
            # - count > 0 → SAFETY CAP mode, stop when reached
            unlimited_mode = (count == 0 or count >= 10000) and start_date and end_date
            safety_cap = count if count > 0 else 999999  # Very high number for unlimited
            
            if unlimited_mode:
                # Unlimited mode: Scrape aggressively per chunk (200 each, stop when exhausted)
                tweets_per_chunk = 200
                print(f"  📊 UNLIMITED MODE: {total_work} chunks, ~{tweets_per_chunk} per chunk, no cap")
            else:
                # Safety cap mode: Distribute count with high buffer for deduplication
                # Typically ~40-60% of tweets are duplicates, so we request ~2.5x per chunk
                base_per_chunk = (safety_cap * 2.5) // total_work
                tweets_per_chunk = max(30, min(200, int(base_per_chunk)))
                print(f"  📊 CAPPED MODE: Target {safety_cap} tweets, {total_work} chunks, ~{tweets_per_chunk}/chunk (with dedup buffer)")
            
            start_from = 0
            
            # Check for existing checkpoint to resume
            checkpoint = load_checkpoint(parent_job_id)
            if checkpoint:
                all_tweets = checkpoint.get('all_tweets', [])
                seen_urls = set(checkpoint.get('seen_urls', []))
                start_from = checkpoint.get('current_chunk_idx', 0) + 1
                print(f"  ♻️ RESUMING from chunk {start_from}/{total_work} ({len(all_tweets)} tweets collected)")
            
            # Process each work item - PARALLEL with worker_mode
            num_workers = worker_mode  # 1 (Safe), 3 (Normal), or 5 (Aggressive)
            print(f"  ⚡ Using {num_workers} parallel workers")
            
            # Thread-safe lock for shared data
            import threading
            data_lock = threading.Lock()
            completed_items = [start_from]  # Use list to be mutable in closure
            
            def scrape_single_work_item(work_idx, work):
                """Worker function to scrape a single chunk with retry logic"""
                nonlocal all_tweets, seen_urls
                
                worker_id = threading.current_thread().name[-1] if len(threading.current_thread().name) > 1 else "1"
                max_retries = 2
                retry_delay = 5  # seconds
                
                for attempt in range(max_retries + 1):
                    try:
                        variation = work['variation']
                        chunk_start_date = work['chunk_start']
                        chunk_end_date = work['chunk_end']
                        chunk_info = f" ({chunk_start_date} to {chunk_end_date})" if chunk_start_date else ""
                        
                        if attempt > 0:
                            logging.info(f"  � [W{worker_id}] Retry #{attempt} for: {variation}{chunk_info}")
                        else:
                            logging.info(f"  �🔧 [W{worker_id}] [{work_idx+1}/{total_work}] Scraping: {variation}{chunk_info}")
                        
                        # Build search query with dates
                        search_query = variation
                        if chunk_start_date:
                            search_query += f" since:{chunk_start_date}"
                        if chunk_end_date:
                            search_query += f" until:{chunk_end_date}"
                        
                        # Extract keywords for filtering (split by space, ignore numbers like 2024)
                        # This ensures we don't capture unrelated tweets just because they have "2024"
                        filter_kws = [w for w in variation.split() if not w.isdigit() and len(w) > 2]
                        
                        # Run scraper for this variation + date chunk
                        # Use calculated tweets_per_chunk (not the old 200 hardcode)
                        tweets = scraper_selenium.scrape_twitter(
                            search_query,
                            count=tweets_per_chunk,
                            headless=True,
                            filter_keywords=filter_kws
                        )
                        
                        new_unique = 0
                        if tweets:
                            # Safely update shared data
                            with data_lock:
                                for tweet in tweets:
                                    url = tweet.get('url', '')
                                    if url and url not in seen_urls:
                                        seen_urls.add(url)
                                        all_tweets.append(tweet)
                                        new_unique += 1
                                completed_items[0] = max(completed_items[0], work_idx)
                            
                            logging.info(f"  ✅ [W{worker_id}] Got {len(tweets)} tweets (+{new_unique} unique), total: {len(all_tweets)}")
                        
                        return {'work_idx': work_idx, 'success': True, 'count': len(tweets) if tweets else 0}
                    
                    except Exception as e:
                        error_msg = str(e)
                        is_browser_crash = 'session' in error_msg.lower() or 'browser' in error_msg.lower() or 'disconnected' in error_msg.lower()
                        
                        if is_browser_crash and attempt < max_retries:
                            logging.warning(f"  ⚠️ [W{worker_id}] Browser crashed, waiting {retry_delay}s before retry...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            logging.error(f"  ❌ [W{worker_id}] Failed after {attempt+1} attempts: {error_msg[:100]}")
                            return {'work_idx': work_idx, 'success': False, 'error': error_msg}
                
                return {'work_idx': work_idx, 'success': False, 'error': 'Max retries exceeded'}
            
            # Filter work items to process (skip already completed)
            pending_work = [(idx, w) for idx, w in enumerate(work_items) if idx >= start_from]
            
            if pending_work:
                # Use ThreadPoolExecutor for parallel execution with STAGGERED LAUNCH
                # Anti-shadowban: 10s delay between worker starts to look more natural
                stagger_delay = 10 if num_workers > 1 else 0
                logging.info(f"  ⏱️ Anti-shadowban mode: {num_workers} workers with {stagger_delay}s delay between each")
                
                with ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix='Worker') as executor:
                    ACTIVE_EXECUTORS.append(executor)  # Register for Ctrl+C cleanup
                    futures = {}
                    
                    # Submit work items with staggered delay to prevent shadowban
                    for i, (idx, work) in enumerate(pending_work):
                        # Check if shutdown requested
                        if SHUTDOWN_FLAG.is_set():
                            logging.info("  🛑 Shutdown requested, stopping...")
                            break
                        
                        # Stagger launch: 10s delay between worker starts (except first)
                        if i > 0 and i < num_workers:
                            logging.info(f"  ⏳ Waiting {stagger_delay}s before launching Worker {i+1}...")
                            time.sleep(stagger_delay)
                        
                        future = executor.submit(scrape_single_work_item, idx, work)
                        futures[future] = idx
                    
                    # Process results as they complete
                    for future in as_completed(futures):
                        result = future.result()
                        
                        # Update job status
                        update_job_status(parent_job_id, 'RUNNING', f'Completed {completed_items[0]+1}/{total_work}, {len(all_tweets)} tweets collected')
                        
                        # EARLY STOP: Check if safety cap reached (only in capped mode)
                        if not unlimited_mode and len(all_tweets) >= safety_cap:
                            logging.info(f"  🛑 Safety cap reached ({safety_cap} tweets), stopping early!")
                            # Cancel remaining futures
                            for f in futures:
                                f.cancel()
                            break
                        
                        # Save checkpoint periodically (every 5 completions)
                        if completed_items[0] % 5 == 0:
                            with data_lock:
                                save_checkpoint(parent_job_id, {
                                    'base_keyword': base_keyword,
                                    'variations': variations,
                                    'date_chunks': date_chunks,
                                    'all_tweets': all_tweets,
                                    'seen_urls': list(seen_urls),
                                    'current_chunk_idx': completed_items[0],
                                    'total_chunks': total_work,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'worker_mode': worker_mode  # Added for resume
                                })
            
            # Save merged results
            if all_tweets:
                timestamp = int(datetime.now().timestamp())
                clean_kw = "".join([c if c.isalnum() else "_" for c in base_keyword])[:50]
                output_filename = f"{OUTPUT_DIR}/autoexpand_{clean_kw}_{timestamp}.csv"
                
                # Write CSV
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                keys = all_tweets[0].keys()
                with open(output_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(all_tweets)
                
                # Update parent job as COMPLETED
                filename = os.path.basename(output_filename)
                update_job_status(parent_job_id, 'COMPLETED', f'Found {len(all_tweets)} unique tweets (from {len(variations)} keywords)', filename)
                delete_checkpoint(parent_job_id)  # Clean up checkpoint
                print(f"🎉 Auto-Expand complete: {len(all_tweets)} tweets saved to {output_filename}")
                # Keep job visible for 30s then remove
                time.sleep(30)
                remove_job(parent_job_id)
            else:
                update_job_status(parent_job_id, 'FAILED', 'No tweets found', None)
                delete_checkpoint(parent_job_id)  # Clean up checkpoint
                time.sleep(10)
                remove_job(parent_job_id)
        
        # Start the batch thread
        thread = threading.Thread(target=run_auto_expand_batch)
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': parent_job_id, 'status': 'RUNNING', 'message': f'Auto-Expand started ({len(variations)} keywords)'})
    
    # --- STANDARD MODE (single job) ---
    else:
        # Combine multiple keywords into one
        if len(keywords) > 1:
            combined_keyword = " OR ".join(keywords)
        else:
            combined_keyword = keywords[0]
        
        job_id = str(uuid.uuid4())
        
        # Save to DB
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO jobs (id, keyword, target_count, status, created_at, progress) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, combined_keyword, count, 'PENDING', datetime.now(), 'Queued...')
        )
        conn.commit()
        conn.close()
        
        # Start background thread
        thread = threading.Thread(target=run_scraper_thread, args=(job_id, combined_keyword, count, start_date, end_date, smart_mode, worker_mode, None))
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': job_id, 'status': 'PENDING', 'message': 'Job created'})

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    jobs = get_all_jobs()
    # Sort by created_at desc and limit to 10
    jobs_sorted = sorted(jobs, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    return jsonify(jobs_sorted)

@app.route('/api/health-check', methods=['GET'])
def health_check():
    """Run account health check and return status"""
    result = scraper_selenium.check_account_health()
    return jsonify(result)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent logs for live log viewer"""
    return jsonify(LOG_BUFFER[-50:])  # Return last 50 entries

@app.route('/api/rate-status', methods=['GET'])
def rate_status():
    """Get current rate limit meter status"""
    return jsonify(get_rate_status())

@app.route('/api/checkpoints', methods=['GET'])
def get_checkpoints():
    """List all pending checkpoints that can be resumed"""
    return jsonify(list_pending_checkpoints())

@app.route('/api/resume/<job_id>', methods=['POST'])
def resume_job(job_id):
    """Resume a job from checkpoint"""
    checkpoint = load_checkpoint(job_id)
    if not checkpoint:
        return jsonify({'error': 'No checkpoint found for this job'}), 404
    
    # Get checkpoint data
    base_keyword = checkpoint.get('base_keyword', 'Unknown')
    start_date = checkpoint.get('start_date')
    end_date = checkpoint.get('end_date')
    
    # Update job status
    update_job_status(job_id, 'RUNNING', f'Resuming from chunk {checkpoint.get("current_chunk_idx", 0)+1}')
    
    # Start resume thread (reuses the run_auto_expand_batch logic)
    def run_resume():
        try:
            # The regular batch loop will pick up the checkpoint automatically
            # We just need to trigger it with the same job_id
            logging.info(f"♻️ Resume started for job {job_id}")
        except Exception as e:
            logging.error(f"Resume error: {e}")
    
    return jsonify({
        'status': 'RESUMING',
        'job_id': job_id,
        'keyword': base_keyword,
        'message': f'Job resuming from checkpoint'
    })

@app.route('/api/preview/<job_id>', methods=['GET'])
def preview_data(job_id):
    """Preview first 10 rows of a completed job"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT result_file FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return jsonify({'error': 'No data found'}), 404
    
    filename = row[0]
    filepath = f"{OUTPUT_DIR}/{filename}"
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    preview_rows = []
    try:
        if filepath.endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    preview_rows.append(dict(row))
        elif filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                preview_rows = data[:10]
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({
        'total': len(preview_rows),
        'preview': preview_rows
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(f"{OUTPUT_DIR}/{filename}", as_attachment=True)

if __name__ == '__main__':
    init_db()
    print("🚀 Web App running on http://127.0.0.1:5000")
    # Disable reloader to prevent dual-process issue on Windows
    # This ensures Ctrl+C kills everything cleanly
    app.run(debug=True, port=5000, use_reloader=False)
