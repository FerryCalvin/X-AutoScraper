"""
Twitter/X Scraper using Twikit with FULL COOKIES
"""

import asyncio
import json
import sys
from datetime import datetime

# Handle Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    from twikit import Client
except ImportError:
    import os
    os.system('pip install twikit')
    from twikit import Client

# Full cookies from user
COOKIES = {
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
    'AMP_8f1ede8e9c': 'JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjIwYjNlMjhiOC03NjFiLTQyMWEtOGMyOC05NzQxYmM5M2FhODYlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzY4MzEyMzAxNjkyJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2ODMxMjMwMTg0OSU3RA==',
    'AMP_MKTG_8f1ede8e9c': 'JTdCJTIycmVmZXJyZXIlMjIlM0ElMjJodHRwcyUzQSUyRiUyRnd3dy5nb29nbGUuY29tJTJGJTIyJTJDJTIycmVmZXJyaW5nX2RvbWFpbiUyMiUzQSUyMnd3dy5nb29nbGUuY29tJTIyJTdE'
}

async def main():
    print("🐦 Twitter/X Scraper (Full Cookie Auth)\n")
    
    # Initialize client
    client = Client('en-US')
    
    # Set cookies directly to the http session
    print("🍪 Setting cookies...")
    client.http.cookies.clear() # Clear existing first
    
    for name, value in COOKIES.items():
        client.http.cookies.set(name, value, domain='.twitter.com')
        
    # Manually set the CSRF token which is crucial
    client._token = COOKIES['ct0']
    
    # Verify login
    try:
        print("🔐 Verifying authentication...")
        user = await client.user()
        print(f"✅ Logged in as: @{user.screen_name} ({user.name})")
        print(f"   Followers: {user.followers_count}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        # If verification fails, search will likely fail too, but let's try


    # Search
    keyword = "indonesia"
    print(f"\n🔍 Searching for: '{keyword}'")
    
    try:
        tweets = await client.search_tweet(keyword, 'Latest', count=20)
        
        print(f"✅ Found {len(tweets)} tweets!\n")
        
        for i, tweet in enumerate(tweets, 1):
            print(f"{i}. @{tweet.user.screen_name}: {tweet.text.replace(chr(10), ' ')[:80]}...")
            print(f"   ❤️ {tweet.favorite_count} | 🔄 {tweet.retweet_count}")
            print("-" * 50)
            
    except Exception as e:
        print(f"\n❌ Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
