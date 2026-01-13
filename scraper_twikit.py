"""
Twitter/X Scraper using Twikit
WORKING in 2024! Uses Twitter's internal API with account login.

Built by Friday for skripsi project
"""

import asyncio
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

try:
    from twikit import Client
except ImportError:
    print("Please install twikit: pip install twikit")
    sys.exit(1)


# Twitter credentials
USERNAME = 'feiscrap'
PASSWORD = '@Fairnanda049#'
EMAIL = 'feiscrap@gmail.com'  # or your email

# Cookies file for persistent login
COOKIES_FILE = 'cookies.json'


async def login(client: Client):
    """Login to Twitter or use saved cookies"""
    cookies_path = Path(COOKIES_FILE)
    
    if cookies_path.exists():
        print("📂 Loading saved cookies...")
        client.load_cookies(COOKIES_FILE)
        print("✅ Logged in with saved cookies!")
        return True
    
    print("🔑 Logging in to Twitter...")
    try:
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD
        )
        client.save_cookies(COOKIES_FILE)
        print("✅ Login successful! Cookies saved.")
        return True
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False


async def search_tweets(client: Client, keyword: str, count: int = 100):
    """Search tweets by keyword"""
    print(f"\n🔍 Searching for: '{keyword}'")
    print(f"   Target: {count} tweets\n")
    
    tweets = []
    
    try:
        # Search tweets
        search_result = await client.search_tweet(keyword, 'Latest', count=count)
        
        for tweet in search_result:
            tweets.append({
                'id': tweet.id,
                'text': tweet.text,
                'created_at': str(tweet.created_at) if tweet.created_at else None,
                'language': tweet.lang,
                'like_count': tweet.favorite_count or 0,
                'retweet_count': tweet.retweet_count or 0,
                'reply_count': tweet.reply_count or 0,
                'view_count': tweet.view_count or 0,
                'user': {
                    'id': tweet.user.id if tweet.user else None,
                    'username': tweet.user.screen_name if tweet.user else None,
                    'display_name': tweet.user.name if tweet.user else None,
                    'followers_count': tweet.user.followers_count if tweet.user else 0,
                    'verified': tweet.user.is_blue_verified if tweet.user else False,
                },
                'hashtags': [h.get('text', '') for h in (tweet.hashtags or [])],
            })
            
            if len(tweets) % 10 == 0:
                print(f"   Progress: {len(tweets)} tweets...")
        
        # Get more tweets if needed (pagination)
        while len(tweets) < count and search_result:
            try:
                search_result = await search_result.next()
                if not search_result:
                    break
                    
                for tweet in search_result:
                    if len(tweets) >= count:
                        break
                    tweets.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': str(tweet.created_at) if tweet.created_at else None,
                        'language': tweet.lang,
                        'like_count': tweet.favorite_count or 0,
                        'retweet_count': tweet.retweet_count or 0,
                        'reply_count': tweet.reply_count or 0,
                        'view_count': tweet.view_count or 0,
                        'user': {
                            'id': tweet.user.id if tweet.user else None,
                            'username': tweet.user.screen_name if tweet.user else None,
                            'display_name': tweet.user.name if tweet.user else None,
                            'followers_count': tweet.user.followers_count if tweet.user else 0,
                        },
                        'hashtags': [h.get('text', '') for h in (tweet.hashtags or [])],
                    })
                    
                    if len(tweets) % 20 == 0:
                        print(f"   Progress: {len(tweets)} tweets...")
                        
            except Exception as e:
                print(f"   Pagination stopped: {e}")
                break
        
        print(f"\n✅ Fetched {len(tweets)} tweets")
        return tweets
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return tweets


def export_json(tweets, filename):
    """Export tweets to JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2, default=str)
    print(f"📁 Exported to {filename}")


def export_csv(tweets, filename):
    """Export tweets to CSV"""
    if not tweets:
        return
        
    fieldnames = [
        'id', 'text', 'created_at', 'language',
        'like_count', 'retweet_count', 'reply_count', 'view_count',
        'username', 'display_name', 'followers_count', 'hashtags'
    ]
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for t in tweets:
            writer.writerow({
                'id': t['id'],
                'text': t['text'].replace('\n', ' ') if t['text'] else '',
                'created_at': t['created_at'],
                'language': t['language'],
                'like_count': t['like_count'],
                'retweet_count': t['retweet_count'],
                'reply_count': t['reply_count'],
                'view_count': t['view_count'],
                'username': t['user']['username'],
                'display_name': t['user']['display_name'],
                'followers_count': t['user']['followers_count'],
                'hashtags': ','.join(t['hashtags']),
            })
    
    print(f"📁 Exported to {filename}")


def print_summary(tweets):
    """Print summary of scraped tweets"""
    if not tweets:
        print("\n⚠️ No tweets found")
        return
        
    print("\n📊 Summary:")
    print(f"   Total tweets: {len(tweets)}")
    
    # Language distribution
    langs = {}
    for t in tweets:
        lang = t.get('language') or 'unknown'
        langs[lang] = langs.get(lang, 0) + 1
    
    print("   Languages:")
    for lang, count in sorted(langs.items(), key=lambda x: -x[1])[:5]:
        print(f"     - {lang}: {count}")
    
    # Engagement
    total_likes = sum(t.get('like_count', 0) for t in tweets)
    total_retweets = sum(t.get('retweet_count', 0) for t in tweets)
    total_views = sum(t.get('view_count', 0) for t in tweets)
    
    print(f"   Total Likes: {total_likes:,}")
    print(f"   Total Retweets: {total_retweets:,}")
    print(f"   Total Views: {total_views:,}")
    
    # Top tweet
    top = max(tweets, key=lambda t: t.get('like_count', 0))
    print(f"\n   🔥 Top Tweet by @{top['user']['username']}:")
    text_preview = (top.get('text') or '')[:80]
    print(f"      \"{text_preview}...\"")
    print(f"      ❤️ {top['like_count']} | 🔄 {top['retweet_count']} | 👁️ {top['view_count']}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🐦 Twitter/X Scraper using Twikit (WORKING 2024!)"
    )
    parser.add_argument('-k', '--keyword', required=True, help='Search keyword')
    parser.add_argument('-c', '--count', type=int, default=100, help='Number of tweets')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('--csv', help='Also export to CSV')
    
    args = parser.parse_args()
    
    print("🐦 Twitter/X Scraper (Twikit)\n")
    
    # Create client
    client = Client('en-US')
    
    # Login
    if not await login(client):
        return
    
    # Search tweets
    tweets = await search_tweets(client, args.keyword, args.count)
    
    # Print summary
    print_summary(tweets)
    
    # Export
    if tweets:
        filename = args.output or f"tweets_{args.keyword.replace(' ', '_')[:20]}"
        export_json(tweets, f"{filename}.json")
        
        if args.csv:
            export_csv(tweets, args.csv)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    # Handle Windows event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
