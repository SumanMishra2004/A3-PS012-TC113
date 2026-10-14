"""
Rate limiting implementation.

Token bucket algorithm with per-server limits and global concurrency cap.
Rate control is mandatory and cannot be disabled.
"""

import time
import asyncio
from typing import Optional, Dict
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    refill_rate: float
    tokens: float = field(default_factory=float)
    last_refill_time: float = field(default_factory=time.time)

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill_time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_refill_time = now

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if successful."""
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_for_tokens(self, tokens: int = 1) -> float:
        """
        Wait until tokens are available.
        Returns the time waited in seconds.
        """
        start = time.time()
        while not self.consume(tokens):
            time.sleep(0.001)  # 1ms sleep to avoid busy-wait
        return time.time() - start


class RateLimiter:
    """
    Rate limiting coordinator.
    
    Enforces:
    - Global QPS limit
    - Per-server QPS limit
    - Max concurrent queries
    - Global query budget
    """

    def __init__(
        self,
        global_qps: int,
        per_server_qps: int,
        max_inflight: int,
        global_query_budget: int,
    ):
        """Initialize rate limiter with config values."""
        self.global_qps = global_qps
        self.per_server_qps = per_server_qps
        self.max_inflight = max_inflight
        self.global_query_budget = global_query_budget
        self.global_bucket = TokenBucket(
            capacity=max_inflight,
            refill_rate=global_qps
        )
        self.per_server_buckets: Dict[str, TokenBucket] = {}
        self.inflight_count = 0
        self.total_queries = 0

    def get_per_server_bucket(self, server_id: str) -> TokenBucket:
        """Get or create per-server token bucket."""
        if server_id not in self.per_server_buckets:
            self.per_server_buckets[server_id] = TokenBucket(
                capacity=5,  # Small buffer for per-server
                refill_rate=self.per_server_qps
            )
        return self.per_server_buckets[server_id]

    def acquire(self, server_id: str) -> float:
        """
        Acquire permission to send a query.
        
        Waits if necessary. Returns wait time in seconds.
        Raises RuntimeError if global budget exceeded.
        """
        if self.total_queries >= self.global_query_budget:
            raise RuntimeError(
                f"Global query budget ({self.global_query_budget}) exceeded"
            )

        # Wait for global rate limit
        global_wait = self.global_bucket.wait_for_tokens(1)

        # Wait for per-server rate limit
        per_server_bucket = self.get_per_server_bucket(server_id)
        server_wait = per_server_bucket.wait_for_tokens(1)

        # Update counters
        self.inflight_count += 1
        self.total_queries += 1

        return max(global_wait, server_wait)

    def release(self) -> None:
        """Release a query slot."""
        if self.inflight_count > 0:
            self.inflight_count -= 1

    def budget_remaining(self) -> int:
        """Queries remaining in global budget."""
        return self.global_query_budget - self.total_queries

    def is_budget_exhausted(self) -> bool:
        """Check if global budget exceeded."""
        return self.total_queries >= self.global_query_budget

    def stats(self) -> Dict[str, int]:
        """Get rate limiter statistics."""
        return {
            "total_queries_sent": self.total_queries,
            "queries_budget_remaining": self.budget_remaining(),
            "inflight_queries": self.inflight_count,
            "max_inflight": self.max_inflight,
        }


class AsyncRateLimiter:
    """Async version of rate limiter for concurrent operations."""

    def __init__(
        self,
        global_qps: int,
        per_server_qps: int,
        max_inflight: int,
        global_query_budget: int,
    ):
        """Initialize async rate limiter."""
        self.limiter = RateLimiter(
            global_qps,
            per_server_qps,
            max_inflight,
            global_query_budget
        )
        self.semaphore = asyncio.Semaphore(max_inflight)

    async def acquire(self, server_id: str) -> float:
        """Acquire permission asynchronously."""
        async with self.semaphore:
            return self.limiter.acquire(server_id)

    async def release(self) -> None:
        """Release a query slot asynchronously."""
        self.limiter.release()

    def stats(self) -> Dict[str, int]:
        """Get statistics."""
        return self.limiter.stats()
