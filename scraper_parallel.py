"""
Parallel Twitter Scraper Runner 🚀
Spawns multiple Selenium instances to scrape faster!

Usage:
python scraper_parallel.py -k "jokowi" -c 100 --workers 3

Built by Friday
"""

import argparse
import subprocess
import json
import csv # Added for CSV export
import time
import sys
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

def split_date_range(start_date, end_date, num_chunks):
    """Split a date range into equal chunks"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    diff = (end - start) / num_chunks
    
    ranges = []
    current = start
    for i in range(num_chunks):
        chunk_end = current + diff
        # Format: since:2023-01-01 until:2023-02-01
        ranges.append({
            'since': current.strftime("%Y-%m-%d"),
            'until': chunk_end.strftime("%Y-%m-%d")
        })
        current = chunk_end
    return ranges

def run_worker(worker_id, keyword, count, date_range, headless=False):
    """Run a single scraper instance"""
    
    # Construct query with date filter
    # e.g. "jokowi since:2023-01-01 until:2023-02-01"
    query = f"{keyword} since:{date_range['since']} until:{date_range['until']}"
    filename = f"temp_chunk_{worker_id}.json"
    
    print(f"🚀 [Worker {worker_id}] Starting: {query} -> Target: {count}")
    
    cmd = [
        sys.executable, "scraper_selenium.py",
        "-k", query,
        "-c", str(count),
        "-o", filename
    ]
    
    if headless:
        cmd.append("--headless")
        
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ [Worker {worker_id}] Finished!")
        return filename
    except subprocess.CalledProcessError as e:
        print(f"❌ [Worker {worker_id}] Failed: {e}")
        return None

def merge_results(filenames, output_file):
    """Merge all JSON files into one"""
    master_list = []
    
    print(f"\n📦 Merging {len(filenames)} files...")
    
    for fname in filenames:
        if not fname or not os.path.exists(fname):
            continue
            
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                master_list.extend(data)
            # Optional: Remove temp file
            # os.remove(fname)
        except Exception as e:
            print(f"⚠️ Error reading {fname}: {e}")
            
    # Remove duplicates based on text or user+text
    unique_tweets = {t['text']: t for t in master_list}.values()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(list(unique_tweets), f, ensure_ascii=False, indent=2)
        
    # Also save CSV
    csv_file = output_file.replace('.json', '.csv')
    if unique_tweets:
        keys = list(unique_tweets)[0].keys()
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(unique_tweets)
        
    print(f"✨ Merged {len(unique_tweets)} unique tweets into {output_file} & {csv_file}")

def run_parallel_job(keyword, total_count, workers=3, start_date=None, end_date=None, output_dir="outputs"):
    """
    Main function to be called by external scripts (like app.py)
    """
    if start_date is None:
        start_date = "2023-01-01" # Default fallback
        
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"⚡ Parallel Scraper Job: {keyword} ({total_count})")
    
    # 1. Prepare chunks
    chunks = split_date_range(start_date, end_date, workers)
    
    # GREEDY STRATEGY:
    # Instead of splitting count (1000/5 = 200), we give each worker the FULL target.
    # This fixes the issue where "Bursty" events (news happening in 1 week) get capped at 200.
    # We will deduplicate later. Better more data than less.
    tweets_per_worker = total_count 
    
    # 2. Launch workers
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            # Create a unique temp name in output_dir
            temp_name = os.path.join(output_dir, f"temp_{int(time.time())}_{i}.json")
            
            futures.append(
                executor.submit(
                    run_worker_subprocess, 
                    i+1, 
                    keyword, 
                    tweets_per_worker, 
                    chunk,
                    temp_name
                )
            )
            time.sleep(1) 
            
        results = [f.result() for f in futures]
        
    # 4. Merge
    final_filename = os.path.join(output_dir, f"parallel_{keyword.replace(' ', '_')}_{int(time.time())}.json")
    merge_results(results, final_filename)
    return final_filename

def run_worker_subprocess(worker_id, keyword, count, date_range, output_file):
    """Run a single scraper instance via subprocess"""
    query = f"{keyword} since:{date_range['since']} until:{date_range['until']}"
    
    # Ensure full path for scraper_selenium.py
    script_path = os.path.join(os.getcwd(), "scraper_selenium.py")
    
    cmd = [
        sys.executable, script_path,
        "-k", query,
        "-c", str(count),
        "-o", output_file,
        "--headless" # Force headless for parallel workers
    ]
    
    try:
        # Enable output so user sees progress in terminal
        subprocess.run(cmd, check=True) 
        return output_file
    except subprocess.CalledProcessError:
        return None

def main():
    parser = argparse.ArgumentParser(description="Parallel Twitter Scraper")
    parser.add_argument('-k', '--keyword', required=True)
    parser.add_argument('-c', '--total_count', type=int, default=100)
    parser.add_argument('-w', '--workers', type=int, default=3)
    parser.add_argument('--start', default="2023-01-01")
    
    args = parser.parse_args()
    
    run_parallel_job(args.keyword, args.total_count, args.workers, args.start, output_dir=".")

if __name__ == "__main__":
    main()

