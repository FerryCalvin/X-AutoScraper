"""
Guest Token Manager for Twitter API access
"""

import time
from typing import Optional
from curl_cffi import requests
from .config import BEARER_TOKEN, TWITTER_ENDPOINTS
from .stealth import StealthManager


class GuestTokenManager:
    """Manages Twitter guest tokens with auto-refresh"""
    
    TOKEN_LIFETIME = 7200  # 2 hours (conservative estimate)
    
    def __init__(self, stealth: Optional[StealthManager] = None):
        self.stealth = stealth or StealthManager()
        self._token: Optional[str] = None
        self._token_created_at: float = 0
        
    @property
    def token(self) -> str:
        """Get current token, refreshing if needed"""
        if self._should_refresh():
            self._fetch_token()
        return self._token
    
    def _should_refresh(self) -> bool:
        """Check if token needs refresh"""
        if not self._token:
            return True
        age = time.time() - self._token_created_at
        return age >= self.TOKEN_LIFETIME
    
    def _fetch_token(self) -> str:
        """Fetch new guest token from Twitter"""
        headers = self.stealth.build_headers()
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
        
        try:
            response = requests.post(
                TWITTER_ENDPOINTS["guest_token"],
                headers=headers,
                impersonate=self.stealth.get_browser_version(),
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            self._token = data["guest_token"]
            self._token_created_at = time.time()
            
            return self._token
            
        except Exception as e:
            raise GuestTokenError(f"Failed to fetch guest token: {e}") from e
    
    def refresh(self) -> str:
        """Force refresh token"""
        self._token = None
        return self.token
    
    def invalidate(self):
        """Invalidate current token (call when rate limited)"""
        self._token = None
        self._token_created_at = 0


class GuestTokenError(Exception):
    """Raised when guest token operations fail"""
    pass
