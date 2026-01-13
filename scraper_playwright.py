"""
Twitter/X Scraper using Playwright
Browser automation - most reliable scraping method!

Built by Friday for skripsi project
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Please install playwright: pip install playwright")
    print("Then install browser: playwright install chromium")
    sys.exit(1)


# Twitter credentials
USERNAME = 'feiscrap'
PASSWORD = '@Fairnanda049#'

# Cookies from user (Full set)
COOKIES_DICT = {
    'auth_token': '598847410fe3cef2e7e8edc56d5ee4365ae7355a',
    'ct0': 'b72143b89ae2beb13c3b73af8e1a262bcf25ab0b2f7baf881e662a52bdda9cc19a87c322f77b26f59859a00b0316aa14823e1b6c9c87f0020be29f7da00fa22006696767bbfca73c30dc4fcbc0a17443',
    'guest_id': 'v1:176578571022714602',
    'guest_id_ads': 'v1:176578571022714602',
    'guest_id_marketing': 'v1:176578571022714602',
    'kdt': 'P4xr4OvMZXXF6EDV3Y6dUxAeb9ZAy9LEX0ySqbll',
    'twid': 'u=2011074182071926785',
    '_twitter_sess': 'BAh7CSIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%0ASGFzaHsABjoKQHVzZWR7ADoPY3JlYXRlZF9hdGwrCNiboLebAToMY3NyZl9p%0AZCIlOTViYmQ3ZDc2MmEzY2U0ZGUyYjhhM2EzYjkxYmE0Yjc6B2lkIiUyNWE1%0AMGU4MzdjYmQ2ODhiNDdmZWQ3Y2ZlZjA2NzJkMA%3D%3D--0cebcfc1968de5a4753505fc1895665ce43ff66c',
    'personalization_id': '"v1_wcuT2D34wK6pMs/vg89OWQ=="',
    'gt': '2011073648535486893',
    '__cf_bm': 'v5fa8r2vjTtvZ6T_jR0dwIRbbeOmTDwIrNIH1DRqvR4-1768314733.9047477-1.0.1.1-Jz6dmEmgQJ_SSUgiFkkpzrIGloEidyzjNx4PlzFEQJ8tcjt.xwdBP2tR7s5ULVHvTXPewGOGAsRomc4JMn_6fTBaKEE8uuiQEqhiReTIbRhjE0XoGE_n39QH5X_1T3YI',
    '__cuid': 'bf12c34ecc1046a2885fd83cb7d845bf',
    'external_referer': 'padhuUp37zjgzgv1mFWxJ12Ozwit7owX|0|8e8t2xd8A2w=',
}

async def search_twitter(keyword: str, count: int = 20, headless: bool = True):
    """Search tweets using Playwright browser automation"""
    
    print(f"🔍 Searching for: '{keyword}'")
    print(f"   Target: {count} tweets\n")
    
    tweets = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Add all cookies
        cookies_list = []
        for name, value in COOKIES_DICT.items():
            # Add for both domains to be safe
            cookies_list.append({'name': name, 'value': value, 'domain': '.twitter.com', 'path': '/'})
            cookies_list.append({'name': name, 'value': value, 'domain': '.x.com', 'path': '/'})
            
        await context.add_cookies(cookies_list)

        
        page = await context.new_page()
        
        try:
            # Go to Twitter search
            search_url = f'https://x.com/search?q={keyword}&src=typed_query&f=live'
            print(f"📡 Loading search page...")
            
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check if logged in
            if 'login' in page.url.lower():
                print("⚠️ Not logged in, attempting login...")
                # Try login
                await page.goto('https://x.com/login', wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # Enter username
                username_input = page.locator('input[autocomplete="username"]')
                await username_input.fill(USERNAME)
                
                # Click next
                next_button = page.locator('text=Next')
                await next_button.click()
                await page.wait_for_timeout(2000)
                
                # Enter password
                password_input = page.locator('input[type="password"]')
                await password_input.fill(PASSWORD)
                
                # Click login
                login_button = page.locator('text=Log in')
                await login_button.click()
                await page.wait_for_timeout(5000)
                
                # Go to search again
                await page.goto(search_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
            
            # Scroll and collect tweets
            print("📜 Scrolling and collecting tweets...")
            
            scroll_count = 0
            max_scrolls = count // 5 + 5
            
            while len(tweets) < count and scroll_count < max_scrolls:
                # Find tweet articles
                tweet_elements = await page.locator('article[data-testid="tweet"]').all()
                
                for element in tweet_elements:
                    if len(tweets) >= count:
                        break
                    
                    try:
                        # Extract tweet data
                        text_el = element.locator('div[data-testid="tweetText"]')
                        text = await text_el.inner_text() if await text_el.count() > 0 else ''
                        
                        user_el = element.locator('div[data-testid="User-Name"] a')
                        username = ''
                        if await user_el.count() > 0:
                            href = await user_el.first.get_attribute('href')
                            if href:
                                username = href.replace('/', '')
                        
                        # Get metrics
                        metrics = {}
                        for metric in ['reply', 'retweet', 'like']:
                            metric_el = element.locator(f'button[data-testid="{metric}"]')
                            if await metric_el.count() > 0:
                                metric_text = await metric_el.inner_text()
                                try:
                                    metrics[metric] = int(metric_text.replace(',', '').replace('K', '000').replace('M', '000000') or 0)
                                except:
                                    metrics[metric] = 0
                        
                        tweet = {
                            'text': text,
                            'username': username,
                            'like_count': metrics.get('like', 0),
                            'retweet_count': metrics.get('retweet', 0),
                            'reply_count': metrics.get('reply', 0),
                            'scraped_at': datetime.now().isoformat()
                        }
                        
                        # Avoid duplicates
                        if not any(t['text'] == text for t in tweets):
                            tweets.append(tweet)
                            if len(tweets) % 5 == 0:
                                print(f"   Progress: {len(tweets)} tweets...")
                    
                    except Exception as e:
                        continue
                
                # Scroll down
                await page.evaluate('window.scrollBy(0, 1000)')
                await page.wait_for_timeout(1500)
                scroll_count += 1
            
            print(f"\n✅ Fetched {len(tweets)} tweets")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            await browser.close()
    
    return tweets


def export_json(tweets, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"📁 Exported to {filename}")


def print_summary(tweets):
    if not tweets:
        print("\n⚠️ No tweets found")
        return
    
    print("\n📊 Summary:")
    print(f"   Total: {len(tweets)} tweets")
    
    total_likes = sum(t.get('like_count', 0) for t in tweets)
    print(f"   Total Likes: {total_likes:,}")
    
    if tweets:
        top = max(tweets, key=lambda t: t.get('like_count', 0))
        print(f"\n   🔥 Top Tweet by @{top['username']}:")
        print(f"      \"{top['text'][:60]}...\"")
        print(f"      ❤️ {top['like_count']}")


async def main():
    parser = argparse.ArgumentParser(description="🐦 Twitter Scraper (Playwright)")
    parser.add_argument('-k', '--keyword', required=True, help='Search keyword')
    parser.add_argument('-c', '--count', type=int, default=20, help='Number of tweets')
    parser.add_argument('--visible', action='store_true', help='Show browser window')
    parser.add_argument('-o', '--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    print("🐦 Twitter/X Scraper (Playwright Browser)\n")
    
    tweets = await search_twitter(
        args.keyword, 
        args.count, 
        headless=not args.visible
    )
    
    print_summary(tweets)
    
    if tweets:
        filename = args.output or f"tweets_{args.keyword.replace(' ', '_')[:20]}.json"
        export_json(tweets, filename)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())

