"""
Batch Scraping Script for AutoScraper
=====================================
Run this script to scrape multiple keywords in parallel batches.
This maximizes data collection by splitting queries.

Usage:
    python batch_scrape.py

The script will create separate jobs for each keyword and merge results at the end.
"""

import requests
import time
import os
import csv
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
OUTPUT_DIR = "outputs"

# Keywords to scrape - split for maximum coverage
KEYWORDS = [
    "banjirsumatra",
    "banjiraceh", 
    "acehtamiang",
    "banjir aceh",
    "korban banjir sumatra",
    "bencana aceh 2025",
    "#PrayForSumatera",
    "#BanjirAceh",
    "#banjirsumatra",
    "longsor aceh"
]

# How many tweets per keyword
COUNT_PER_KEYWORD = 2000

# Worker mode (1=safe, 3=normal, 5=aggressive)
WORKER_MODE = 3

# Enable Smart Mode for each job
SMART_MODE = True


def create_job(keyword, count, smart_mode=True, worker_mode=3):
    """Create a scraping job via API"""
    try:
        response = requests.post(f"{BASE_URL}/api/jobs", json={
            "keyword": keyword,
            "count": count,
            "smart_mode": smart_mode,
            "worker_mode": worker_mode
        })
        data = response.json()
        print(f"✅ Created job for '{keyword}': {data}")
        return data.get('job_id') or data.get('job_ids', [None])[0]
    except Exception as e:
        print(f"❌ Failed to create job for '{keyword}': {e}")
        return None


def check_job_status(job_id):
    """Check job status"""
    try:
        response = requests.get(f"{BASE_URL}/api/jobs")
        jobs = response.json()
        for job in jobs:
            if job['id'] == job_id:
                return job
        return None
    except:
        return None


def wait_for_jobs(job_ids, check_interval=30):
    """Wait for all jobs to complete"""
    print(f"\n⏳ Waiting for {len(job_ids)} jobs to complete...")
    
    while True:
        completed = 0
        failed = 0
        running = 0
        
        for job_id in job_ids:
            status = check_job_status(job_id)
            if status:
                if status['status'] == 'COMPLETED':
                    completed += 1
                elif status['status'] == 'FAILED':
                    failed += 1
                else:
                    running += 1
        
        print(f"   Progress: {completed} completed, {running} running, {failed} failed")
        
        if completed + failed == len(job_ids):
            break
            
        time.sleep(check_interval)
    
    print(f"\n🎉 All jobs finished! Completed: {completed}, Failed: {failed}")
    return completed


def merge_csv_files(output_filename="merged_batch_results.csv"):
    """Merge all CSV files in outputs folder"""
    all_rows = []
    seen_urls = set()  # For deduplication
    
    csv_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv')]
    
    print(f"\n📦 Merging {len(csv_files)} CSV files...")
    
    fieldnames = None
    
    for csv_file in csv_files:
        filepath = os.path.join(OUTPUT_DIR, csv_file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                
                for row in reader:
                    # Deduplicate by URL
                    url = row.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_rows.append(row)
        except Exception as e:
            print(f"   ⚠️ Error reading {csv_file}: {e}")
    
    # Write merged file
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"✅ Merged {len(all_rows)} unique tweets into {output_path}")
    return output_path, len(all_rows)


def main():
    print("=" * 50)
    print("🚀 AutoScraper Batch Processor")
    print("=" * 50)
    print(f"Keywords: {len(KEYWORDS)}")
    print(f"Target per keyword: {COUNT_PER_KEYWORD}")
    print(f"Total potential: {len(KEYWORDS) * COUNT_PER_KEYWORD}")
    print("=" * 50)
    
    # Create jobs
    job_ids = []
    for keyword in KEYWORDS:
        print(f"\n🔄 Creating job: '{keyword}'")
        job_id = create_job(keyword, COUNT_PER_KEYWORD, SMART_MODE, WORKER_MODE)
        if job_id:
            job_ids.append(job_id)
        time.sleep(2)  # Small delay between job creation
    
    if not job_ids:
        print("❌ No jobs created!")
        return
    
    # Wait for completion
    wait_for_jobs(job_ids)
    
    # Merge results
    timestamp = int(datetime.now().timestamp())
    output_file, total_count = merge_csv_files(f"batch_merged_{timestamp}.csv")
    
    print("\n" + "=" * 50)
    print(f"🎉 BATCH COMPLETE!")
    print(f"   Total unique tweets: {total_count}")
    print(f"   Output file: {output_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()
