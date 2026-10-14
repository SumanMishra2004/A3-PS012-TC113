"""
Scan orchestration and execution.

Manages probe execution order, rate limiting, retries, repeat runs,
and reproducibility.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any
import random

from .models import ScanResult, DNSClass, ReasonCode, ScanRun
from .probes import ProbeExecutor, ProbeRequest, ProbeGenerator
from .classifier import Classifier
from .ratelimit import RateLimiter
from .config import Target, SettingsConfig


class ScanRunner:
    """Execute a complete DNS probe scan."""

    def __init__(
        self,
        targets: List[Target],
        settings: SettingsConfig,
        seed: int = 42,
    ):
        """Initialize scan runner."""
        self.targets = targets
        self.settings = settings
        self.seed = seed
        self.rate_limiter = RateLimiter(
            global_qps=settings.rate_control.global_qps,
            per_server_qps=settings.rate_control.per_server_qps,
            max_inflight=settings.rate_control.max_inflight,
            global_query_budget=settings.rate_control.global_query_budget,
        )
        random.seed(seed)

    def run_single_scan(self) -> List[ScanResult]:
        """
        Execute a single scan against all targets.
        
        Returns list of ScanResult objects.
        """
        results = []

        # Deterministic target order
        ordered_targets = sorted(self.targets, key=lambda t: t.ip)

        for idx, target in enumerate(ordered_targets):
            # Rate limit gate
            try:
                self.rate_limiter.acquire(target.ip)
            except RuntimeError as e:
                # Budget exhausted; return partial results
                print(f"Warning: {e}")
                break

            result = self._probe_single_target(target, idx)
            results.append(result)
            self.rate_limiter.release()

        return results

    def _probe_single_target(self, target: Target, iteration: int) -> ScanResult:
        """Probe a single target with all three probes."""
        # Generate nonce for this iteration
        nonce = ProbeGenerator.generate_nonce(self.seed, iteration)

        # Probe A: Authoritative check
        probe_a = ProbeExecutor.send_probe(
            ProbeRequest(
                probe_name="A",
                query_name=self.settings.probe_design["probe_a_qname"],
                query_type=self.settings.probe_design["probe_a_qtype"],
                rd_bit=self.settings.probe_design["probe_a_rd"],
                timeout=self.settings.probe.timeout_seconds,
                server_ip=target.ip,
                server_port=target.port,
            ),
            max_retries=self.settings.probe.max_retries,
            backoff_base=self.settings.probe.backoff_base,
            jitter_fraction=self.settings.probe.jitter_fraction,
        )

        # Probe B: Recursion check
        probe_b_qname = f"{nonce}.{self.settings.probe_design['probe_b_domain']}"
        probe_b = ProbeExecutor.send_probe(
            ProbeRequest(
                probe_name="B",
                query_name=probe_b_qname,
                query_type=self.settings.probe_design["probe_b_qtype"],
                rd_bit=self.settings.probe_design["probe_b_rd"],
                timeout=self.settings.probe.timeout_seconds,
                server_ip=target.ip,
                server_port=target.port,
            ),
            max_retries=self.settings.probe.max_retries,
            backoff_base=self.settings.probe.backoff_base,
            jitter_fraction=self.settings.probe.jitter_fraction,
        )

        # Probe C: Control (same as B but RD=0)
        probe_c = ProbeExecutor.send_probe(
            ProbeRequest(
                probe_name="C",
                query_name=probe_b_qname,
                query_type=self.settings.probe_design["probe_b_qtype"],
                rd_bit=self.settings.probe_design["probe_c_rd"],
                timeout=self.settings.probe.timeout_seconds,
                server_ip=target.ip,
                server_port=target.port,
            ),
            max_retries=self.settings.probe.max_retries,
            backoff_base=self.settings.probe.backoff_base,
            jitter_fraction=self.settings.probe.jitter_fraction,
        )

        # Classify
        expected_answer = self.settings.expected_answers.get("probe_ext_lab", "10.10.0.99")
        classification, reason_code, explanation = Classifier.classify(
            probe_a, probe_b, probe_c, expected_answer
        )

        # Build result
        result = ScanResult(
            target_name=target.name,
            target_ip=target.ip,
            target_port=target.port,
            classification=classification,
            reason_code=reason_code,
            probe_evidence=[probe_a, probe_b, probe_c],
            expected_class=(
                DNSClass[target.expected_class]
                if target.expected_class
                else None
            ),
            timestamp=datetime.now(),
        )

        return result

    def run_repeat_scans(self, num_repeats: int = 3) -> List[ScanRun]:
        """
        Run multiple scans with the same seed for reproducibility.
        
        Returns list of ScanRun objects.
        """
        runs = []
        for i in range(num_repeats):
            run_id = f"run-{i+1}-{uuid.uuid4().hex[:8]}"
            results = self.run_single_scan()
            
            # Compute metrics
            metrics = {
                "iteration": i + 1,
                "results_count": len(results),
                "rate_limiter_stats": self.rate_limiter.stats(),
            }

            runs.append(
                ScanRun(
                    run_id=run_id,
                    timestamp=datetime.now(),
                    seed=self.seed,
                    results=results,
                    metrics=metrics,
                )
            )

            # Reset rate limiter for next run
            self.rate_limiter = RateLimiter(
                global_qps=self.settings.rate_control.global_qps,
                per_server_qps=self.settings.rate_control.per_server_qps,
                max_inflight=self.settings.rate_control.max_inflight,
                global_query_budget=self.settings.rate_control.global_query_budget,
            )

        return runs
