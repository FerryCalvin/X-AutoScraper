import sqlite3
import threading
import uuid
import time
import os
import json
import re # Added for Smart Mode regex
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# Import our scrapers
import scraper_selenium
import scraper_parallel

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

def run_scraper_thread(job_id, keyword, count, start_date=None, end_date=None, smart_mode=False):
    """Background worker thread"""
    print(f"🧵 [Thread] Starting job {job_id} for '{keyword}' (Smart: {smart_mode})")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE jobs SET status = ? WHERE id = ?", ('RUNNING', job_id))
    conn.commit()
    conn.close()

    try:
        final_keyword = keyword
        
        # --- SMART MODE LOGIC ---
        if smart_mode:
            # 1. Update status
            update_job_status(job_id, 'RUNNING (Discovery Phase 🕵️)')
            
            # 2. Discovery Scrape (Small batch)
            print(f"🧠 Smart Mode: Scanning for topics related to '{keyword}'...")
            discovery_tweets = scraper_selenium.scrape_twitter(
                keyword, 
                count=20, # Small sample
                headless=True
            )
            
            # 3. Analyze Hashtags
            if discovery_tweets:
                all_hashtags = []
                for t in discovery_tweets:
                    # Extract hashtags manually if not present in dict yet (safety)
                    tags = re.findall(r'#\w+', t.get('text', ''))
                    all_hashtags.extend(tags)
                
                # Top 3 Hashtags
                from collections import Counter
                top_tags = [tag for tag, _ in Counter(all_hashtags).most_common(3)]
                
                if top_tags:
                    # 4. Expansion
                    # Create query: "banjir OR #banjiraceh OR #aceh"
                    additional_query = " OR ".join(top_tags)
                    final_keyword = f"{keyword} OR {additional_query}"
                    print(f"🧠 Smart Mode: Expanded keyword to -> {final_keyword}")
                    
                    # Update status to show expansion
                    update_job_status(job_id, f'RUNNING (Expanded: {final_keyword})')
        # ------------------------

    
        # Callback to update DB
        def on_progress(msg):
            update_job_status(job_id, 'RUNNING', msg)
        
        # Determine strategy based on count
        if count > 500:
            print(f"🚀 Using Parallel Strategy for {count} tweets")
            update_job_status(job_id, 'RUNNING', f'Running parallel scraper (Target: {count})')
            
            # Run Parallel (3 workers default, could be dynamic)
            # Make sure to handle potential import errors
            try:
                # If start_date is not provided for parallel, it defaults inside the function
                # But if provided, we pass it.
                kwargs = {
                    "keyword": final_keyword, # Use final_keyword here
                    "total_count": count,
                    "workers": 5 if count >= 2000 else 3,
                    "output_dir": OUTPUT_DIR
                }
                if start_date: kwargs["start_date"] = start_date
                if end_date: kwargs["end_date"] = end_date # need to update scraper_parallel to accept end_date if not present

                filename_abs = scraper_parallel.run_parallel_job(**kwargs)
            except Exception as e:
                print(f"Parallel scraper error: {e}")
                raise e

            result_tweets_count = 0 
            if filename_abs and os.path.exists(filename_abs):
                try:
                    with open(filename_abs, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        result_tweets_count = len(data)
                except: pass
                
            # Clean up filename for DB (just basename)
            if filename_abs:
                filename = os.path.basename(filename_abs).replace('.json', '.csv')
                
        else:
            print(f"🐢 Using Standard Strategy for {count} tweets")
            update_job_status(job_id, 'RUNNING', 'Starting browser...')
            
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
            
            result_tweets_count = len(tweets) if tweets else 0
            # Prefer CSV for download
            filename = os.path.basename(filename_abs).replace('.json', '.csv')
        
        # Update Final Status
        if result_tweets_count > 0:
            update_job_status(job_id, 'COMPLETED', f'Found {result_tweets_count} tweets', filename)
        else:
            update_job_status(job_id, 'FAILED', 'No tweets found', None)
            
    except Exception as e:
        print(f"❌ [Thread] Job {job_id} failed: {e}")
        update_job_status(job_id, 'FAILED', str(e), None)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    keyword = data.get('keyword')
    count = int(data.get('count', 20))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    smart_mode = data.get('smart_mode', False)
    
    if not keyword:
        return jsonify({'error': 'Keyword is required'}), 400
        
    job_id = str(uuid.uuid4())
    
    # Save to DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO jobs (id, keyword, target_count, status, created_at, progress) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, keyword, count, 'PENDING', datetime.now(), 'Waiting to start...')
    )
    conn.commit()
    conn.close()
    
    # Start background thread
    thread = threading.Thread(target=run_scraper_thread, args=(job_id, keyword, count, start_date, end_date, smart_mode))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'PENDING'})

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10")
    jobs = c.fetchall()
    conn.close()
    
    return jsonify([dict(job) for job in jobs])

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(f"{OUTPUT_DIR}/{filename}", as_attachment=True)

if __name__ == '__main__':
    init_db()
    print("🚀 Web App running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
