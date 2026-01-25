"""
EntitySpine API Security Module

Provides:
- API Key authentication
- Rate limiting
- Request logging
"""

import os
import time
import logging
from collections import defaultdict
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

API_KEY = os.environ.get("API_KEY", "")  # Empty = no auth required
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_ENABLED = RATE_LIMIT_PER_MINUTE > 0

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


# =============================================================================
# Rate Limiting (in-memory, simple sliding window)
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed, remaining_requests)
        """
        if self.requests_per_minute <= 0:
            return True, 999
        
        now = time.time()
        window_start = now - self.window_size
        
        # Clean old requests
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] 
            if ts > window_start
        ]
        
        current_count = len(self._requests[client_id])
        remaining = max(0, self.requests_per_minute - current_count)
        
        if current_count >= self.requests_per_minute:
            return False, 0
        
        # Record this request
        self._requests[client_id].append(now)
        return True, remaining - 1
    
    def get_reset_time(self, client_id: str) -> int:
        """Get seconds until rate limit resets."""
        if not self._requests[client_id]:
            return 0
        oldest = min(self._requests[client_id])
        return max(0, int(self.window_size - (time.time() - oldest)))


# Global rate limiter
rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)


# =============================================================================
# Dependencies
# =============================================================================

def get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting."""
    # Use API key if provided, otherwise use IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def verify_api_key(
    request: Request,
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[str]:
    """
    Verify API key from header or query parameter.
    
    If API_KEY env var is not set, authentication is disabled.
    """
    # If no API key configured, allow all requests
    if not API_KEY:
        return None
    
    # Check header first, then query param
    provided_key = api_key_header or api_key_query
    
    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if provided_key != API_KEY:
        logger.warning(f"Invalid API key attempt from {get_client_id(request)}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )
    
    return provided_key


async def check_rate_limit(request: Request) -> None:
    """Check rate limit for the client."""
    if not RATE_LIMIT_ENABLED:
        return
    
    client_id = get_client_id(request)
    allowed, remaining = rate_limiter.is_allowed(client_id)
    
    # Add rate limit headers
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_limit = RATE_LIMIT_PER_MINUTE
    
    if not allowed:
        reset_time = rate_limiter.get_reset_time(client_id)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {reset_time} seconds.",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time),
            },
        )


# =============================================================================
# Middleware
# =============================================================================

async def security_middleware(request: Request, call_next):
    """
    Security middleware that handles:
    - Rate limiting
    - Response headers
    """
    # Skip security for health checks
    if request.url.path in ["/health", "/", "/openapi.json", "/docs"]:
        return await call_next(request)
    
    # Check rate limit
    await check_rate_limit(request)
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    
    return response
