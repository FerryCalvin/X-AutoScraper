"""
Configuration for Twitter Scraper
"""

from typing import List
from dataclasses import dataclass, field


@dataclass
class ScraperConfig:
    """Scraper configuration with sensible defaults"""
    
    # Rate limiting
    requests_per_window: int = 50  # Max requests per time window
    window_seconds: int = 900  # 15 minutes
    min_delay: float = 1.0  # Minimum delay between requests (seconds)
    max_delay: float = 3.0  # Maximum delay between requests (seconds)
    
    # Retry settings
    max_retries: int = 3
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    
    # Request settings
    timeout: int = 30
    max_tweets_per_request: int = 20  # Twitter returns ~20 per page
    
    # Browser impersonation options
    browser_versions: List[str] = field(default_factory=lambda: [
        "chrome120",
        "chrome119", 
        "chrome116",
        "edge120",
        "safari17_0",
    ])


# Twitter API endpoints
TWITTER_ENDPOINTS = {
    "guest_token": "https://api.twitter.com/1.1/guest/activate.json",
    "search_adaptive": "https://twitter.com/i/api/2/search/adaptive.json",
    "search_graphql": "https://twitter.com/i/api/graphql/SearchTimeline",
}

# Bearer token (public, used by Twitter web app)
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

# Default headers template
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors", 
    "Sec-Fetch-Site": "same-origin",
    "X-Twitter-Active-User": "yes",
    "X-Twitter-Client-Language": "en",
}
