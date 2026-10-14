"""Unit tests for rate limiting."""

import pytest
import time
from dnsprobe.ratelimit import TokenBucket, RateLimiter


class TestTokenBucket:
    """Tests for token bucket algorithm."""

    def test_bucket_refill(self):
        """Test token bucket refills over time."""
        bucket = TokenBucket(capacity=10, refill_rate=1)
        bucket.tokens = 0
        assert not bucket.consume(1)

        time.sleep(1.1)  # Wait for tokens to refill
        assert bucket.consume(1)

    def test_bucket_capacity_limit(self):
        """Test bucket capacity limit."""
        bucket = TokenBucket(capacity=5, refill_rate=100)
        time.sleep(0.1)
        assert bucket.tokens <= 5

    def test_multiple_consume(self):
        """Test consuming multiple tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=100)
        time.sleep(0.1)
        assert bucket.consume(5)
        assert bucket.consume(4)
        assert not bucket.consume(2)


class TestRateLimiter:
    """Tests for rate limiter."""

    def test_rate_limiter_global_qps(self):
        """Test global QPS limiting."""
        limiter = RateLimiter(
            global_qps=2,
            per_server_qps=10,
            max_inflight=10,
            global_query_budget=100
        )

        start = time.time()
        for _ in range(3):
            limiter.acquire("server1")
        elapsed = time.time() - start

        # With 2 QPS, 3 queries should take ~1.5 seconds
        assert elapsed >= 1.0

    def test_rate_limiter_budget(self):
        """Test global query budget."""
        limiter = RateLimiter(
            global_qps=100,
            per_server_qps=100,
            max_inflight=10,
            global_query_budget=5
        )

        for _ in range(5):
            limiter.acquire("server1")

        with pytest.raises(RuntimeError, match="budget"):
            limiter.acquire("server1")

    def test_rate_limiter_stats(self):
        """Test rate limiter statistics."""
        limiter = RateLimiter(
            global_qps=10,
            per_server_qps=10,
            max_inflight=10,
            global_query_budget=100
        )

        limiter.acquire("server1")
        stats = limiter.stats()

        assert stats["total_queries_sent"] == 1
        assert stats["queries_budget_remaining"] == 99
