"""Unit tests for configuration and guard rails."""

import pytest
from dnsprobe.config import Target, TargetsConfig, GuardRails, RateControlConfig
from dnsprobe.models import DNSClass


class TestGuardRails:
    """Tests for security guard rails."""

    def test_max_targets_hard_limit(self):
        """Test hard constraint: max 20 targets."""
        targets = [
            Target(name=f"srv{i}", ip=f"10.10.0.{i+1}", expected_class="RECURSIVE")
            for i in range(21)
        ]
        with pytest.raises(ValueError, match="exceeds hard limit"):
            TargetsConfig(targets=targets)

    def test_private_ip_allowed(self):
        """Test private IPs are allowed."""
        assert GuardRails.is_private_ip("10.0.0.1")
        assert GuardRails.is_private_ip("172.16.0.1")
        assert GuardRails.is_private_ip("192.168.0.1")
        assert GuardRails.is_private_ip("127.0.0.1")

    def test_public_ip_rejected_without_flag(self):
        """Test public IPs rejected without --allow-public."""
        targets = [Target(name="public", ip="8.8.8.8")]
        with pytest.raises(ValueError, match="Public IP"):
            GuardRails.validate_targets(targets, allow_public=False)

    def test_public_ip_allowed_with_flag(self):
        """Test public IPs allowed with flag."""
        targets = [Target(name="public", ip="8.8.8.8")]
        # Should not raise
        GuardRails.validate_targets(targets, allow_public=True)

    def test_rate_control_global_qps_hard_cap(self):
        """Test global QPS hard cap of 20."""
        with pytest.raises(ValueError, match="exceeds hard cap"):
            RateControlConfig(global_qps=21)

    def test_rate_control_per_server_qps_hard_cap(self):
        """Test per-server QPS hard cap of 5."""
        with pytest.raises(ValueError, match="exceeds hard cap"):
            RateControlConfig(per_server_qps=6)

    def test_rate_control_max_inflight_hard_cap(self):
        """Test max inflight hard cap of 10."""
        with pytest.raises(ValueError, match="exceeds hard cap"):
            RateControlConfig(max_inflight=11)

    def test_duplicate_target_ips_rejected(self):
        """Test duplicate target IPs are rejected."""
        targets = [
            Target(name="srv1", ip="10.10.0.1"),
            Target(name="srv2", ip="10.10.0.1"),  # Duplicate
        ]
        with pytest.raises(ValueError, match="Duplicate"):
            TargetsConfig(targets=targets)

    def test_invalid_ip_rejected(self):
        """Test invalid IP addresses are rejected."""
        with pytest.raises(ValueError, match="Invalid IP"):
            Target(name="bad", ip="999.999.999.999")

    def test_invalid_port_rejected(self):
        """Test invalid port numbers are rejected."""
        with pytest.raises(ValueError, match="Port out of range"):
            Target(name="bad", ip="10.10.0.1", port=99999)
