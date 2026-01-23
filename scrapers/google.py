from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import BaseScraper
import time
import logging
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote_plus

class GoogleScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        print("🚀 GoogleScraper LOADED (V2 - Optimized)")
        self.base_url = "https://www.google.com/search?q="
        # Utilize fake_useragent for randomizing the User-Agent
        try:
            self.ua = UserAgent()
        except Exception as e:
            print(f"⚠️ Could not load fake_useragent: {e}. using default.")
            self.ua = None

    def default_chrome_options(self, headless=True):
        options = Options()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        return options

    def setup_driver(self, headless=True, options=None):
        if options is None:
            options = self.default_chrome_options(headless)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def scrape(self, keyword, count=50, headless=True, **kwargs):
        """
        Scrapes Google Search results for a keyword.
        """
        logging.info(f"🔎 GoogleScraper: Starting search for '{keyword}' (Target: {count})")
        
        # Setup driver with random User-Agent
        chrome_options = self.default_chrome_options(headless)
        if self.ua:
            try:
                user_agent = self.ua.random
                logging.info(f"🎭 Using User-Agent: {user_agent}")
                chrome_options.add_argument(f'user-agent={user_agent}')
            except Exception as e:
                logging.warning(f"⚠️ Failed to generate random UA: {e}")
        
        driver = self.setup_driver(headless, options=chrome_options)
        
        results = []
        collected_hashes = set()
        
        # URL Encode the keyword (Critical for hashtags with #)
        encoded_keyword = quote_plus(keyword)
        search_url = f"{self.base_url}{encoded_keyword}&num=100&hl=id" # Request 100 results per page, Indonesian
        
        try:
            driver.get(search_url)
            
            while len(results) < count:
                # Scroll to bottom to trigger any lazy loading
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                new_items = self._extract_results(driver)
                
                if not new_items:
                    logging.warning(f"⚠️ No new items found on current page.")
                    
                    # DEBUG: Dump page source if 0 results found (and we haven't collected anything yet)
                    if len(results) == 0:
                        debug_filename = "debug_google_0_results.html"
                        try:
                            with open(debug_filename, "w", encoding="utf-8") as f:
                                f.write(driver.page_source)
                            logging.warning(f"📸 Dumped page source to {debug_filename} for inspection.")
                        except Exception as e:
                            logging.error(f"❌ Failed to dump debug file: {e}")
                    
                    break

                for item in new_items:
                    # Deduplicate
                    item_hash = hash(item['url'])
                    if item_hash not in collected_hashes:
                        results.append(item)
                        collected_hashes.add(item_hash)
                        
                    if len(results) >= count:
                        break
                
                logging.info(f"   Google Found {len(new_items)} items (Total: {len(results)})")

                if len(results) >= count:
                    break

                # Pagination
                try:
                    next_button = driver.find_element(By.ID, "pnnext")
                    next_button.click()
                    time.sleep(3) # Wait for next page
                except Exception:
                    logging.info("   No 'Next' button found. End of results.")
                    break
                    
        except Exception as e:
            logging.error(f"❌ GoogleScraper Error: {e}")
        finally:
            driver.quit()
            
        logging.info(f"✅ GoogleScraper finished. Total collected: {len(results)}")
        return results

    def _extract_results(self, driver):
        results = []
        # Robust Selectors Strategy
        # We try multiple selector patterns that Google uses
        result_sub_selectors = [
            'div.g',          # Standard result
            'div.tF2Cxc',     # Valid result container
            'div.v7W49e',     # Another container type
            'div[data-header-feature]' # Feature snippets (sometimes)
        ]
        
        found_elements = []
        
        # Try to gather all potential result elements
        for selector in result_sub_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logging.debug(f"   Found {len(elements)} elements using selector: {selector}")
                found_elements.extend(elements)
        
        # Iterate and extract
        for res in found_elements:
            try:
                # Title
                try:
                    title = res.find_element(By.TAG_NAME, 'h3').text
                except:
                    continue # Skip if no title
                
                # Link
                try:
                    link = res.find_element(By.TAG_NAME, 'a').get_attribute('href')
                except:
                    continue # Skip if no link
                
                # Snippet (Text)
                try:
                    text = res.text
                except:
                    text = ""

                if title and link:
                     results.append({
                        'text': f"{title}\n{text}", # Combine for consistent 'text' field
                        'url': link,
                        'source': 'google',
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception:
                continue
                
        return results

    def health_check(self):
        try:
            # Simple connectivity check
            import requests # Local import to avoid dependency if not used
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("🧪 Running GoogleScraper direct test...")
    scraper = GoogleScraper()
    # Test with a HASHTAG to verify URL encoding
    res = scraper.scrape("#python", count=5, headless=True)
    for r in res:
        print(f"- {r['text'][:50]}... ({r['url']})")
    print(f"Total: {len(res)}")
