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
        options.add_argument('--headless=new')  # New headless mode (faster)
        
        # === HEADLESS OPTIMIZATIONS ===
        # Disable images (saves bandwidth and memory)
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Additional memory optimizations
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--memory-pressure-off')
        options.add_argument('--single-process')
        
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

def check_account_health():
    """
    Check if the Twitter account is healthy (not shadowbanned or restricted).
    Returns a dict with health status and details.
    """
    print("🩺 Checking account health...")
    driver = setup_driver(headless=True)
    
    result = {
        "status": "UNKNOWN",
        "can_search": False,
        "can_see_tweets": False,
        "warnings": [],
        "recommendation": ""
    }
    
    try:
        # 1. Navigate to Twitter
        driver.get("https://x.com")
        time.sleep(3)
        
        # 2. Inject cookies
        if COOKIES_DICT:
            for cookie_name, cookie_value in COOKIES_DICT.items():
                if cookie_value:
                    try:
                        driver.add_cookie({
                            "name": cookie_name,
                            "value": cookie_value,
                            "domain": ".x.com"
                        })
                    except: pass
            driver.refresh()
            time.sleep(3)
        
        # 3. Check if logged in (look for home timeline or compose button)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button'], div[data-testid='tweetButtonInline']"))
            )
            print("   ✅ Login successful")
        except:
            result["status"] = "ERROR"
            result["warnings"].append("Login failed - cookies may be expired")
            result["recommendation"] = "Please update your cookies in cookies_config.json"
            return result
        
        # 4. Try searching for a common term
        driver.get("https://x.com/search?q=test&src=typed_query&f=live")
        time.sleep(4)
        
        # 5. Check if search results appear
        try:
            articles = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            if len(articles) > 0:
                result["can_search"] = True
                result["can_see_tweets"] = True
                print(f"   ✅ Search works - found {len(articles)} tweets")
            else:
                # Check for "No results" message
                no_results = driver.find_elements(By.XPATH, "//*[contains(text(), 'No results')]")
                if no_results:
                    result["warnings"].append("Search returned no results - possible shadowban")
                else:
                    result["warnings"].append("Could not load tweets - possible rate limit")
        except Exception as e:
            result["warnings"].append(f"Search test failed: {str(e)}")
        
        # 6. Determine overall status
        if result["can_search"] and result["can_see_tweets"]:
            result["status"] = "HEALTHY"
            result["recommendation"] = "Account is healthy. Safe to scrape."
        elif result["warnings"]:
            result["status"] = "WARNING"
            result["recommendation"] = "Account may have issues. Consider waiting 24h or using backup account."
        else:
            result["status"] = "UNKNOWN"
            result["recommendation"] = "Could not determine status. Proceed with caution."
            
    except Exception as e:
        result["status"] = "ERROR"
        result["warnings"].append(str(e))
        result["recommendation"] = "Health check failed. Check your internet connection."
    finally:
        driver.quit()
    
    print(f"🩺 Health Status: {result['status']}")
    return result

# ... (previous imports)
import random
import os
import re

# ... (cookies dict)

def random_delay(min_sec=1.5, max_sec=4.0):
    """Sleep for a random amount of time to simulate human behavior"""
    time.sleep(random.uniform(min_sec, max_sec))

import html
import unicodedata

def normalize_unicode_fonts(text):
    """
    Convert fancy Unicode fonts (Mathematical Bold, Script, etc.) to regular ASCII.
    These are commonly used in Twitter for stylized text like 𝗕𝗼𝗹𝗱 𝗧𝗲𝘅𝘁.
    """
    if not text:
        return text
    
    # Unicode block mappings for common styled fonts
    # Mathematical Bold (𝗔-𝗭, 𝗮-𝘇, 𝟬-𝟵)
    # Mathematical Sans-Serif Bold (𝗔-𝗭, 𝗮-𝘇)
    result = []
    for char in text:
        code = ord(char)
        
        # Mathematical Bold Caps (𝐀-𝐙) -> A-Z
        if 0x1D400 <= code <= 0x1D419:
            result.append(chr(code - 0x1D400 + ord('A')))
        # Mathematical Bold Small (𝐚-𝐳) -> a-z
        elif 0x1D41A <= code <= 0x1D433:
            result.append(chr(code - 0x1D41A + ord('a')))
        # Mathematical Sans-Serif Bold Caps (𝗔-𝗭) -> A-Z
        elif 0x1D5D4 <= code <= 0x1D5ED:
            result.append(chr(code - 0x1D5D4 + ord('A')))
        # Mathematical Sans-Serif Bold Small (𝗮-𝘇) -> a-z
        elif 0x1D5EE <= code <= 0x1D607:
            result.append(chr(code - 0x1D5EE + ord('a')))
        # Mathematical Bold Digits (𝟎-𝟗) -> 0-9
        elif 0x1D7CE <= code <= 0x1D7D7:
            result.append(chr(code - 0x1D7CE + ord('0')))
        # Mathematical Sans-Serif Bold Digits (𝟬-𝟵) -> 0-9  
        elif 0x1D7EC <= code <= 0x1D7F5:
            result.append(chr(code - 0x1D7EC + ord('0')))
        # Fullwidth Latin (Ａ-Ｚ, ａ-ｚ) -> A-Z, a-z
        elif 0xFF21 <= code <= 0xFF3A:
            result.append(chr(code - 0xFF21 + ord('A')))
        elif 0xFF41 <= code <= 0xFF5A:
            result.append(chr(code - 0xFF41 + ord('a')))
        else:
            result.append(char)
    
    return ''.join(result)

def is_indonesian_text(text):
    """
    Check if text is likely Indonesian/Latin-based.
    Returns False for Korean, Chinese, Japanese, Arabic, etc.
    """
    if not text:
        return False
    
    # Count Latin characters vs non-Latin
    latin_count = 0
    non_latin_count = 0
    
    for char in text:
        code = ord(char)
        # Basic Latin, Latin Extended, Latin Supplement
        if (0x0000 <= code <= 0x024F) or char.isspace() or char.isdigit():
            latin_count += 1
        # Korean (Hangul)
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            non_latin_count += 1
        # Chinese (CJK)
        elif 0x4E00 <= code <= 0x9FFF:
            non_latin_count += 1
        # Japanese (Hiragana, Katakana)
        elif 0x3040 <= code <= 0x30FF:
            non_latin_count += 1
        # Arabic
        elif 0x0600 <= code <= 0x06FF:
            non_latin_count += 1
    
    # If more than 20% non-Latin, likely not Indonesian
    total = latin_count + non_latin_count
    if total == 0:
        return True
    
    return (non_latin_count / total) < 0.2

def clean_text(text):
    """Start-of-the-art preprocessing with Unicode normalization"""
    if not text: return ""
    
    # 0. Normalize Unicode fancy fonts (𝗕𝗼𝗹𝗱 -> Bold)
    text = normalize_unicode_fonts(text)
    
    # 1. Decode HTML entities (&amp; -> &)
    text = html.unescape(text)
    
    # 2. Remove URLs
    text = re.sub(r'http\S+', '', text)
    
    # 3. Remove Mentions (@user)
    text = re.sub(r'@\w+', '', text)
    
    # 4. Remove Emojis & Special Symbols (Keep only alphanumeric, punctuation, and basic latin)
    # This regex keeps letters, numbers, spaces, and basic punctuation
    text = re.sub(r'[^\w\s,.:;!?#"\'-]', '', text)
    
    # 5. Remove extra whitespace
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
        # Clean keyword for filename and TRUNCATE to avoid Windows 260 char path limit
        clean_kw = "".join([c if c.isalnum() else "_" for c in keyword])
        clean_kw = clean_kw[:100]  # Truncate to 100 chars max
        # Save to outputs folder by default
        os.makedirs("outputs", exist_ok=True)
        filename = f"outputs/tweets_{clean_kw}.json"

    
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
        max_scroll_attempts = 30 # More aggressive (was 15)
        
        while len(tweets) < count and scroll_attempts < max_scroll_attempts:
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
                    
                    # Filter out non-Indonesian text (Korean, Chinese, Japanese, Arabic)
                    if not is_indonesian_text(original_text):
                        continue  # Skip this tweet
                    
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
                # Try harder: Super scroll + wait
                if scroll_attempts % 5 == 0:
                    log(f"   🔄 Retrying scroll (Attempt {scroll_attempts}/{max_scroll_attempts})...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
            else:
                last_height = new_height
                scroll_attempts = max(0, scroll_attempts - 1) # Decay if making progress
        
        # Final status
        if len(tweets) < count:
            log(f"⚠️ Only found {len(tweets)} tweets (Target: {count}). Twitter might not have more data for this query.")
                
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

