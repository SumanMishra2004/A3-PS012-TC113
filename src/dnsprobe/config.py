"""
Configuration loading, validation, and guard rails.

Enforces hard constraints:
- Max 20 targets
- Explicit allowlist only
- Private/loopback ranges by default
- Rate control caps
- No spoofing or amplification flags
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import ipaddress
import yaml
from pydantic import BaseModel, field_validator, ConfigDict


class Target(BaseModel):
    """Single DNS target definition."""
    name: str
    ip: str
    port: int = 53
    expected_class: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {v}") from e
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port out of range: {v}")
        return v


class TargetsConfig(BaseModel):
    """Allowlist of targets."""
    targets: List[Target]

    model_config = ConfigDict(extra="forbid")

    @field_validator("targets")
    @classmethod
    def validate_target_count(cls, v: List[Target]) -> List[Target]:
        """Hard constraint: max 20 targets."""
        if len(v) > 20:
            raise ValueError(f"Target count {len(v)} exceeds hard limit of 20")
        return v

    @field_validator("targets")
    @classmethod
    def validate_unique_targets(cls, v: List[Target]) -> List[Target]:
        """Ensure unique target IPs."""
        ips = [t.ip for t in v]
        if len(ips) != len(set(ips)):
            raise ValueError("Duplicate target IPs detected")
        return v


class RateControlConfig(BaseModel):
    """Rate control limits."""
    global_qps: int = 5
    per_server_qps: int = 1
    max_inflight: int = 4
    global_query_budget: int = 1000

    model_config = ConfigDict(extra="forbid")

    @field_validator("global_qps")
    @classmethod
    def validate_global_qps(cls, v: int) -> int:
        """Hard cap: global QPS <= 20."""
        if v > 20:
            raise ValueError(f"global_qps {v} exceeds hard cap of 20")
        if v < 1:
            raise ValueError(f"global_qps must be >= 1")
        return v

    @field_validator("per_server_qps")
    @classmethod
    def validate_per_server_qps(cls, v: int) -> int:
        """Hard cap: per-server QPS <= 5."""
        if v > 5:
            raise ValueError(f"per_server_qps {v} exceeds hard cap of 5")
        if v < 1:
            raise ValueError(f"per_server_qps must be >= 1")
        return v

    @field_validator("max_inflight")
    @classmethod
    def validate_max_inflight(cls, v: int) -> int:
        """Hard cap: max inflight <= 10."""
        if v > 10:
            raise ValueError(f"max_inflight {v} exceeds hard cap of 10")
        if v < 1:
            raise ValueError(f"max_inflight must be >= 1")
        return v


class ProbeConfig(BaseModel):
    """Probe configuration."""
    timeout_seconds: float = 5
    max_retries: int = 3
    backoff_base: float = 1.5
    jitter_fraction: float = 0.1

    model_config = ConfigDict(extra="forbid")


class SettingsConfig(BaseModel):
    """Global settings."""
    rate_control: RateControlConfig
    probe: ProbeConfig
    probe_design: Dict[str, Any]
    expected_answers: Dict[str, str]
    network: Dict[str, Any]
    reproducibility: Dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class GuardRails:
    """Guard rails for secure, ethical DNS probing."""

    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ]

    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """Check if IP is in private/loopback ranges."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in GuardRails.PRIVATE_RANGES:
                if ip in network:
                    return True
            return False
        except ValueError:
            return False

    @staticmethod
    def validate_targets(targets: List[Target], allow_public: bool = False) -> None:
        """
        Enforce hard constraints on targets.
        
        Raises ValueError if constraints violated.
        """
        if len(targets) > 20:
            raise ValueError(f"Target count {len(targets)} exceeds hard limit of 20")

        for target in targets:
            if not GuardRails.is_private_ip(target.ip) and not allow_public:
                raise ValueError(
                    f"Public IP {target.ip} not allowed without --allow-public flag"
                )


def load_targets(path: Path) -> TargetsConfig:
    """Load and validate targets configuration."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TargetsConfig(**data)


def load_settings(path: Path) -> SettingsConfig:
    """Load and validate settings configuration."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SettingsConfig(**data)
