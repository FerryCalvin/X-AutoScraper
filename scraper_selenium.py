"""
Twitter/X Scraper using Selenium
Uses existing Chrome browser + Cookies
Reliable & Anti-Ban Friendly

Built by Friday for skripsi project
"""
import time
import json
import csv
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# User Cookies (Loaded from file)
def load_cookies():
    try:
        with open('cookies_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ 'cookies_config.json' not found. Using dummy cookies.")
        return {}

COOKIES_DICT = load_cookies()

def setup_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    
    # Anti-detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ... (previous imports)
import random
import os
import re

# ... (cookies dict)

def random_delay(min_sec=1.5, max_sec=4.0):
    """Sleep for a random amount of time to simulate human behavior"""
    time.sleep(random.uniform(min_sec, max_sec))

def clean_text(text):
    """Start-of-the-art preprocessing"""
    # 1. Remove URLs
    text = re.sub(r'http\S+', '', text)
    # 2. Remove Mentions (@user)
    text = re.sub(r'@\w+', '', text)
    # 3. Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower() # Optional: Lowercase

def parse_metric(element):
    """Extract number from aria-label or text"""
    try:
        val = element.get_attribute("aria-label").split()[0] # "15 replies" -> "15"
        val = val.replace(',', '').replace('.', '')
        if 'K' in val: return int(float(val.replace('K', '')) * 1000)
        if 'M' in val: return int(float(val.replace('M', '')) * 1000000)
        return int(val)
    except:
        return 0

def save_intermediate(tweets, filename):
    """Save progress incrementally (JSON + CSV)"""
    # JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
        
    # CSV
    csv_filename = filename.replace('.json', '.csv')
    if tweets:
        keys = tweets[0].keys()
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(tweets)

def scrape_twitter(keyword, count=20, headless=False, output_filename=None, progress_callback=None):
    def log(msg):
        print(msg, flush=True) # Ensure stdout is flushed for terminal
        if progress_callback:
            progress_callback(msg)

    log(f"🐦 Starting Selenium Scraper (Safe Mode)")
    log(f"   Keyword: {keyword}")
    log(f"   Target: {count} tweets")
    
    driver = setup_driver(headless)
    tweets = []

    
    # Determine filename
    if output_filename:
        filename = output_filename
    else:
        # Clean keyword for filename
        clean_kw = "".join([c if c.isalnum() else "_" for c in keyword])
        filename = f"tweets_{clean_kw}.json"

    
    try:
        # 1. Login/Cookie Injection (Same as before)
        log("🌍 Navigating to x.com...")
        driver.get("https://x.com/404")
        random_delay(2, 3)
        
        log("🍪 Injecting cookies...")
        for name, value in COOKIES_DICT.items():
            driver.add_cookie({'name': name, 'value': value, 'domain': '.x.com', 'path': '/'})
            try:
                driver.add_cookie({'name': name, 'value': value, 'domain': '.twitter.com', 'path': '/'})
            except: pass

        # 3. Search
        log("🔍 Going to search page...")
        search_url = f"https://x.com/search?q={keyword}&src=typed_query&f=live"
        driver.get(search_url)
        random_delay(3, 5)
        
        # 4. Wait for content
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
            )
        except:
            log("⚠️ Timeout. Login might have failed.")
            return []
        
        # 5. Scrape loop
        log("📜 Scrolling and collecting...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        consecutive_no_new_tweets = 0
        
        while len(tweets) < count and scroll_attempts < 15:
            # Get articles
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            new_tweets_found = False
            
            for article in articles:
                if len(tweets) >= count:
                    break
                try:
                    # Parse Tweet
                    text_el = article.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                    original_text = text_el.text
                    
                    user_el = article.find_element(By.CSS_SELECTOR, "div[data-testid='User-Name'] a")
                    username = user_el.get_attribute("href").split('/')[-1]
                    
                    # Filter out Grok AI
                    if username.strip().lower() == 'grok':
                        continue
                    
                    # Time & URL
                    time_el = article.find_element(By.TAG_NAME, "time")
                    timestamp = time_el.get_attribute("datetime")
                    tweet_url = user_el.get_attribute("href") # Actually the link is on the time element usually, but username link is to profile. 
                    # Correct URL logic: usually the timestamp IS the permalink
                    try:
                        tweet_url = time_el.find_element(By.XPATH, "./..").get_attribute("href")
                    except:
                        tweet_url = f"https://x.com/{username}"

                    # Metrics
                    replies = 0
                    retweets = 0
                    likes = 0
                    views = 0
                    
                    try:
                        replies = parse_metric(article.find_element(By.CSS_SELECTOR, "div[data-testid='reply']"))
                        retweets = parse_metric(article.find_element(By.CSS_SELECTOR, "div[data-testid='retweet']"))
                        likes = parse_metric(article.find_element(By.CSS_SELECTOR, "div[data-testid='like']"))
                        # Views often don't have a distinct test-id easily found without hover sometimes, but let's try
                        # views = parse_metric(article.find_element(By.CSS_SELECTOR, "div[data-testid='app-text-transition-container']")) 
                    except: pass
                    
                    tweets.append({
                        "username": username,
                        "text": original_text,
                        "text_clean": clean_text(original_text),
                        "hashtags": re.findall(r'#\w+', original_text),
                        "timestamp": timestamp,
                        "url": tweet_url,
                        "replies": replies,
                        "retweets": retweets,
                        "likes": likes,
                        "scraped_at": datetime.now().isoformat(),
                    })
                    new_tweets_found = True
                    
                    # Log progress
                    if len(tweets) % 10 == 0:
                        log(f"   Collected {len(tweets)}/{count} tweets...")
                        save_intermediate(tweets, filename)
                        
                    # LONG BREAK every 100 tweets
                    if len(tweets) % 100 == 0:
                        log("   ☕ Taking a coffee break (10s) to be safe...")
                        time.sleep(10)
                        
                except:
                    continue
            
            # Scroll logic
            if new_tweets_found:
                consecutive_no_new_tweets = 0
                scroll_attempts = 0
            else:
                consecutive_no_new_tweets += 1
            
            # Scroll down
            scroll_px = random.randint(800, 1200) # Random scroll amount
            driver.execute_script(f"window.scrollBy(0, {scroll_px});")
            random_delay(1.5, 3.0) # Variable delay
            
            # Check if stuck
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                last_height = new_height
                
        print(f"\n✅ Successfully scraped {len(tweets)} tweets!")
        return tweets
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return tweets
        
    finally:
        if tweets:
            save_intermediate(tweets, filename)
            print(f"📁 Saved to {filename}")
        driver.quit()


def export_json(tweets, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"📁 Exported to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selenium Twitter Scraper")
    parser.add_argument('-k', '--keyword', required=True)
    parser.add_argument('-c', '--count', type=int, default=20)
    parser.add_argument('-o', '--output', help="Custom output filename")
    parser.add_argument('--headless', action='store_true')
    
    args = parser.parse_args()
    
    # Allow custom output filename
    if args.output:
        # Override the logic inside (requires small change or just pass it differently)
        # Actually easier to just modify the filename logic inside scrape_twitter or pass it here
        # Let's modify scrape_twitter to accept filename
        pass 

    # For parallel scraping, the 'keyword' might actually be a full query string like "jokowi since:2024-01-01"
    # The existing script puts it into f"https://x.com/search?q={keyword}..." which works fine!
    
    final_filename = args.output
    tweets = scrape_twitter(args.keyword, args.count, args.headless, output_filename=final_filename)

