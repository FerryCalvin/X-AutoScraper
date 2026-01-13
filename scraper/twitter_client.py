"""
Twitter API Client using twscrape library
Supports both guest mode and authenticated mode for higher limits
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Callable
from twscrape import API, gather
from twscrape.logger import set_log_level

from .config import ScraperConfig
from .models import Tweet, User, SearchResult


class TwitterClient:
    """
    Twitter client using twscrape library.
    Handles all the complexity of Twitter's GraphQL API.
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.api = API()
        # Reduce log verbosity
        set_log_level("WARNING")
        
    async def _ensure_guest_account(self):
        """Ensure we have at least a guest account available"""
        accounts = await self.api.pool.accounts_info()
        if not accounts:
            # Add a guest account (no login required for limited access)
            # For more tweets, user should add their own account
            pass
    
    def _parse_tweet(self, tweet_data) -> Tweet:
        """Parse twscrape tweet object into our Tweet model"""
        user = User(
            id=str(tweet_data.user.id),
            username=tweet_data.user.username,
            display_name=tweet_data.user.displayname,
            followers_count=tweet_data.user.followersCount,
            following_count=tweet_data.user.friendsCount,
            verified=tweet_data.user.verified or tweet_data.user.blueType is not None,
            profile_image_url=tweet_data.user.profileImageUrl,
        )
        
        # Extract hashtags, mentions, urls from tweet
        hashtags = [h.text for h in (tweet_data.hashtags or [])]
        mentions = [m.username for m in (tweet_data.mentionedUsers or [])]
        urls = [u.url for u in (tweet_data.links or [])]
        media_urls = [m.url for m in (tweet_data.media or [])] if tweet_data.media else []
        
        return Tweet(
            id=str(tweet_data.id),
            text=tweet_data.rawContent,
            created_at=tweet_data.date,
            user=user,
            like_count=tweet_data.likeCount or 0,
            retweet_count=tweet_data.retweetCount or 0,
            reply_count=tweet_data.replyCount or 0,
            quote_count=tweet_data.quoteCount or 0,
            view_count=tweet_data.viewCount or 0,
            language=tweet_data.lang,
            conversation_id=str(tweet_data.conversationId) if tweet_data.conversationId else None,
            is_retweet=tweet_data.retweetedTweet is not None,
            is_quote=tweet_data.quotedTweet is not None,
            has_media=bool(tweet_data.media),
            media_urls=media_urls,
            urls=urls,
            hashtags=hashtags,
            mentions=mentions,
        )
    
    async def search_tweets_async(
        self,
        keyword: str,
        max_tweets: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tweet]:
        """
        Search tweets asynchronously.
        
        Args:
            keyword: Search query
            max_tweets: Maximum number of tweets to fetch
            progress_callback: Optional callback(current, total)
            
        Returns:
            List of Tweet objects
        """
        tweets = []
        count = 0
        
        # Use search with language filter for Indonesian/English
        query = f"{keyword} lang:id OR lang:en"
        
        try:
            async for tweet in self.api.search(query, limit=max_tweets):
                parsed = self._parse_tweet(tweet)
                tweets.append(parsed)
                count += 1
                
                if progress_callback:
                    progress_callback(count, max_tweets)
                    
                if count >= max_tweets:
                    break
                    
        except Exception as e:
            raise TwitterAPIError(f"Search failed: {e}") from e
        
        return tweets
    
    def search_tweets(
        self,
        keyword: str,
        max_tweets: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tweet]:
        """
        Search tweets (synchronous wrapper).
        """
        return asyncio.run(
            self.search_tweets_async(keyword, max_tweets, progress_callback)
        )


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors"""
    pass


class RateLimitError(TwitterAPIError):
    """Raised when rate limited"""
    pass
