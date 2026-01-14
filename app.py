import sqlite3
import threading
import uuid
import time
import os
import json
import csv # Added for CSV operations
import re # Added for Smart Mode regex
import yaml # Config file support
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# Import our scrapers
import scraper_selenium
import scraper_parallel

# ===================
# CONFIG LOADER
# ===================
def load_config():
    """Load configuration from YAML file"""
    config_path = 'config.yaml'
    default_config = {
        'scraper': {'default_count': 100, 'scroll_delay_min': 1.5, 'scroll_delay_max': 4.0},
        'workers': {'default_mode': 3, 'parallel_threshold': 500},
        'logging': {'enabled': True, 'file': 'logs/autoscraper.log', 'level': 'INFO'},
        'output': {'directory': 'outputs', 'format': 'csv'},
        'rate_limit': {'max_requests_per_minute': 30, 'warning_threshold': 20, 'danger_threshold': 25}
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Error loading config: {e}. Using defaults.")
            return default_config
    return default_config

CONFIG = load_config()

# ===================
# LOGGING SETUP
# ===================
def setup_logging():
    """Setup file and console logging"""
    log_config = CONFIG.get('logging', {})
    
    if not log_config.get('enabled', True):
        return
    
    # Create logs directory
    log_file = log_config.get('file', 'logs/autoscraper.log')
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Setup rotating file handler
    log_level = getattr(logging, log_config.get('level', 'INFO').upper(), logging.INFO)
    max_bytes = log_config.get('max_size_mb', 10) * 1024 * 1024
    backup_count = log_config.get('backup_count', 5)
    
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(console_handler)
    
    logging.info("🚀 AutoScraper started - Logging initialized")

setup_logging()

# ===================
# LIVE LOG BUFFER (for UI)
# ===================
LOG_BUFFER = []
LOG_BUFFER_MAX = 100  # Keep last 100 log entries

class BufferHandler(logging.Handler):
    """Custom handler to store logs in memory for live viewing"""
    def emit(self, record):
        global LOG_BUFFER
        log_entry = self.format(record)
        LOG_BUFFER.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': record.levelname,
            'message': log_entry
        })
        # Keep buffer size limited
        if len(LOG_BUFFER) > LOG_BUFFER_MAX:
            LOG_BUFFER = LOG_BUFFER[-LOG_BUFFER_MAX:]

# Add buffer handler
buffer_handler = BufferHandler()
buffer_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(buffer_handler)

# ===================
# RATE LIMIT TRACKING
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
DB_FILE = 'jobs.db'
OUTPUT_DIR = 'outputs'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and clean up stale jobs"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            keyword TEXT,
            target_count INTEGER,
            status TEXT, -- PENDING, RUNNING, COMPLETED, FAILED
            progress TEXT,
            result_file TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Reset stale jobs (jobs that were RUNNING when server stopped)
    c.execute('''
        UPDATE jobs 
        SET status = 'FAILED', progress = 'Interrupted by server restart' 
        WHERE status = 'RUNNING'
    ''')
    
    conn.commit()
    conn.close()

def update_job_status(job_id, status, progress=None, result_file=None):
    """Update job status in DB"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    updates = ["status = ?"]
    params = [status]
    
    if progress:
        updates.append("progress = ?")
        params.append(progress)
    if result_file:
        updates.append("result_file = ?")
        params.append(result_file)
        
    params.append(job_id)
    
    c.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

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
    
    # --- AUTO-EXPAND MODE (for large targets) ---
    if auto_expand and count > 2000:
        print(f"🚀 Auto-Expand Mode: Creating batch jobs for '{raw_keyword}'")
        
        # Base keyword
        base_keyword = keywords[0] if len(keywords) == 1 else " OR ".join(keywords)
        
        # Generate keyword variations (split into separate mini-jobs)
        variations = []
        for kw in keywords:
            # Add base keyword
            if kw not in variations:
                variations.append(kw)
            # Add common hashtag variants
            if not kw.startswith('#'):
                variations.append(f"#{kw.replace(' ', '')}")
        
        # Add additional related keywords based on common patterns
        extra_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if 'banjir' in kw_lower:
                extra_keywords.extend(['korban banjir', 'banjir bandang', '#prayforsumatera'])
            if 'aceh' in kw_lower:
                extra_keywords.extend(['#acehtamiang', 'bencana aceh', 'longsor aceh'])
            if 'sumatra' in kw_lower or 'sumatera' in kw_lower:
                extra_keywords.extend(['#banjirsumatra', 'bencana sumatera'])
        
        for extra in extra_keywords:
            if extra not in variations:
                variations.append(extra)
        
        # Limit to 8 variations max
        variations = list(set(variations))[:8]
        
        # Calculate count per variation
        count_per_variation = max(500, count // len(variations))
        
        print(f"🔄 Created {len(variations)} keyword variations, {count_per_variation} each")
        
        # Create batch group for merging
        batch_id = str(uuid.uuid4())
        with BATCH_LOCK:
            BATCH_GROUPS[batch_id] = {
                'total': len(variations),
                'completed': 0,
                'files': [],
                'base_keyword': base_keyword
            }
        
        job_ids = []
        for variation in variations:
            job_id = str(uuid.uuid4())
            
            # Save to DB
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT INTO jobs (id, keyword, target_count, status, created_at, progress) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, variation, count_per_variation, 'PENDING', datetime.now(), f'Queued (Batch: {variations.index(variation)+1}/{len(variations)})')
            )
            conn.commit()
            conn.close()
            
            # Start background thread
            thread = threading.Thread(target=run_scraper_thread, args=(job_id, variation, count_per_variation, start_date, end_date, smart_mode, worker_mode, batch_id))
            thread.daemon = True
            thread.start()
            
            job_ids.append(job_id)
        
        return jsonify({'job_ids': job_ids, 'status': 'PENDING', 'message': f'Created {len(variations)} batch jobs (Auto-Expand)'})
    
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10")
    jobs = c.fetchall()
    conn.close()
    
    return jsonify([dict(job) for job in jobs])

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
    app.run(debug=True, port=5000)
