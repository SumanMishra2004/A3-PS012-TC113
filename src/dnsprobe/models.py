"""
Data models for DNS probe results and configuration.

Defines Pydantic models for type-safe, validated configuration and results.
"""

from typing import Optional, Literal, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class DNSClass(str, Enum):
    """DNS resolver classification."""
    RECURSIVE = "RECURSIVE"
    AUTHORITATIVE_ONLY = "AUTHORITATIVE_ONLY"
    REFUSED = "REFUSED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ReasonCode(str, Enum):
    """Reason codes for INCONCLUSIVE classification."""
    TIMEOUT = "TIMEOUT"
    SERVFAIL = "SERVFAIL"
    CONTRADICTORY = "CONTRADICTORY"
    RA_SET_NO_ANSWER = "RA_SET_NO_ANSWER"
    MALFORMED = "MALFORMED"
    TCP_FAIL = "TCP_FAIL"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProbeEvidence:
    """Raw evidence from a single probe attempt."""
    probe_name: str  # "A", "B", or "C"
    query_name: str
    query_type: str
    rd_bit: bool
    rcode: Optional[str] = None
    aa_flag: Optional[bool] = None
    ra_flag: Optional[bool] = None
    answer_section: Optional[List[str]] = None
    latency_ms: Optional[float] = None
    retry_count: int = 0
    error_type: Optional[str] = None
    raw_response: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "probe_name": self.probe_name,
            "query_name": self.query_name,
            "query_type": self.query_type,
            "rd_bit": self.rd_bit,
            "rcode": self.rcode,
            "aa_flag": self.aa_flag,
            "ra_flag": self.ra_flag,
            "answer_section": self.answer_section,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ScanResult:
    """Result for a single target."""
    target_name: str
    target_ip: str
    target_port: int
    classification: DNSClass
    reason_code: Optional[ReasonCode] = None
    confidence: Literal["confirmed", "flag-based", "heuristic", "inconclusive"] = "heuristic"
    probe_evidence: List[ProbeEvidence] = field(default_factory=list)
    expected_class: Optional[DNSClass] = None
    match: Optional[bool] = None  # None until ground truth comparison
    upstream_query_log: Optional[List[str]] = None  # Evidence from upstream server logs
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_name": self.target_name,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
            "classification": self.classification.value,
            "reason_code": self.reason_code.value if self.reason_code else None,
            "confidence": self.confidence,
            "probe_evidence": [pe.to_dict() for pe in self.probe_evidence],
            "expected_class": self.expected_class.value if self.expected_class else None,
            "match": self.match,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ScanRun:
    """Complete scan run results."""
    run_id: str
    timestamp: datetime
    seed: int
    results: List[ScanResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "seed": self.seed,
            "results": [r.to_dict() for r in self.results],
            "metrics": self.metrics,
        }


@dataclass
class ConfusionMatrix:
    """Confusion matrix for evaluation."""
    true_positives: Dict[DNSClass, int] = field(default_factory=dict)
    false_positives: Dict[DNSClass, int] = field(default_factory=dict)
    false_negatives: Dict[DNSClass, int] = field(default_factory=dict)
    true_negatives: Dict[DNSClass, int] = field(default_factory=dict)

    def accuracy(self) -> float:
        """Overall accuracy."""
        total = sum(self.true_positives.values()) + sum(self.true_negatives.values()) + \
                sum(self.false_positives.values()) + sum(self.false_negatives.values())
        if total == 0:
            return 0.0
        correct = sum(self.true_positives.values()) + sum(self.true_negatives.values())
        return correct / total

    def precision(self, dns_class: DNSClass) -> float:
        """Per-class precision."""
        tp = self.true_positives.get(dns_class, 0)
        fp = self.false_positives.get(dns_class, 0)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    def recall(self, dns_class: DNSClass) -> float:
        """Per-class recall (sensitivity)."""
        tp = self.true_positives.get(dns_class, 0)
        fn = self.false_negatives.get(dns_class, 0)
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    def f1_score(self, dns_class: DNSClass) -> float:
        """Per-class F1 score."""
        p = self.precision(dns_class)
        r = self.recall(dns_class)
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
