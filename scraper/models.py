"""
Data models for Twitter Scraper
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class User(BaseModel):
    """Twitter user model"""
    id: str
    username: str
    display_name: str
    followers_count: int = 0
    following_count: int = 0
    verified: bool = False
    profile_image_url: Optional[str] = None
    
    
class Tweet(BaseModel):
    """Tweet data model"""
    id: str
    text: str
    created_at: datetime
    user: User
    
    # Engagement metrics
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    
    # Additional data
    language: Optional[str] = None
    source: Optional[str] = None
    conversation_id: Optional[str] = None
    
    # For retweets/quotes
    is_retweet: bool = False
    is_quote: bool = False
    quoted_tweet_id: Optional[str] = None
    
    # Media
    has_media: bool = False
    media_urls: List[str] = Field(default_factory=list)
    
    # URLs in tweet
    urls: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Search result container"""
    keyword: str
    tweets: List[Tweet] = Field(default_factory=list)
    total_fetched: int = 0
    cursor: Optional[str] = None
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def add_tweet(self, tweet: Tweet):
        """Add a tweet to results"""
        self.tweets.append(tweet)
        self.total_fetched = len(self.tweets)
        
    def to_dict_list(self) -> List[dict]:
        """Convert tweets to list of dicts for export"""
        return [tweet.model_dump() for tweet in self.tweets]
