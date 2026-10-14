"""
Classification logic.

Pure functions mapping probe evidence to DNS class and reason codes.
Fully table-driven, testable, with explicit handling of edge cases.
"""

from typing import Tuple, Optional, List
from .models import ProbeEvidence, DNSClass, ReasonCode


class Classifier:
    """Classify DNS server behavior from probe evidence."""

    @staticmethod
    def classify(
        probe_a: ProbeEvidence,
        probe_b: ProbeEvidence,
        probe_c: ProbeEvidence,
        expected_recursive_answer: str = "10.10.0.99",
    ) -> Tuple[DNSClass, Optional[ReasonCode], str]:
        """
        Classify server based on probe evidence.
        
        Returns:
            (classification, reason_code, explanation)
        """

        # Check for critical errors
        if probe_a.error_type and probe_b.error_type:
            reason = Classifier._get_inconclusive_reason(
                probe_a, probe_b, probe_c
            )
            return (DNSClass.INCONCLUSIVE, reason, f"Both probes errored: {reason}")

        # RECURSIVE classification
        # Probe B returns expected answer with RA=1
        if (
            probe_b.rcode == "NOERROR"
            and probe_b.ra_flag is True
            and Classifier._has_expected_answer(probe_b, expected_recursive_answer)
        ):
            # Confidence is "confirmed" if we have upstream log evidence
            return (
                DNSClass.RECURSIVE,
                None,
                "Probe B returned expected answer with RA flag set (recursive resolver)"
            )

        # REFUSED classification
        # Both A and B return REFUSED
        if probe_a.rcode == "REFUSED" and probe_b.rcode == "REFUSED":
            return (
                DNSClass.REFUSED,
                None,
                "Both probes received REFUSED response"
            )

        # AUTHORITATIVE_ONLY classification
        # Probe A has AA=1 for lab.test, Probe B has no valid recursive answer, RA=0
        if (
            probe_a.aa_flag is True
            and probe_a.rcode == "NOERROR"
            and probe_b.ra_flag is False
        ):
            return (
                DNSClass.AUTHORITATIVE_ONLY,
                None,
                "Server is authoritative for lab.test (AA flag), does not recurse (RA=0)"
            )

        # INCONCLUSIVE cases
        reason = Classifier._get_inconclusive_reason(probe_a, probe_b, probe_c)
        explanation = Classifier._get_inconclusive_explanation(
            probe_a, probe_b, probe_c, reason
        )
        return (DNSClass.INCONCLUSIVE, reason, explanation)

    @staticmethod
    def _has_expected_answer(
        evidence: ProbeEvidence,
        expected_answer: str
    ) -> bool:
        """Check if evidence contains expected answer."""
        if not evidence.answer_section:
            return False
        for rr in evidence.answer_section:
            if expected_answer in str(rr):
                return True
        return False

    @staticmethod
    def _get_inconclusive_reason(
        probe_a: ProbeEvidence,
        probe_b: ProbeEvidence,
        probe_c: ProbeEvidence,
    ) -> ReasonCode:
        """Determine specific reason for INCONCLUSIVE classification."""

        # Timeout
        if "TIMEOUT" in str(probe_b.error_type):
            return ReasonCode.TIMEOUT

        # SERVFAIL response
        if probe_b.rcode == "SERVFAIL":
            return ReasonCode.SERVFAIL

        # RA set but no valid answer (false-positive trap)
        if probe_b.ra_flag is True and probe_b.rcode != "NOERROR":
            return ReasonCode.RA_SET_NO_ANSWER

        # Contradictory evidence
        if (
            probe_a.ra_flag is True
            and probe_b.ra_flag is False
            and probe_a.rcode == "NOERROR"
            and probe_b.rcode == "NOERROR"
        ):
            return ReasonCode.CONTRADICTORY

        # Malformed response
        if "MALFORMED" in str(probe_b.error_type):
            return ReasonCode.MALFORMED

        # TCP fallback failure
        if "TCP_FAIL" in str(probe_b.error_type):
            return ReasonCode.TCP_FAIL

        # Rate limited (RCODE 9 or specific error)
        if "429" in str(probe_b.error_type) or "RATE_LIMITED" in str(probe_b.error_type):
            return ReasonCode.RATE_LIMITED

        # Network error
        if probe_b.error_type and probe_b.error_type not in ["TIMEOUT", "MALFORMED"]:
            return ReasonCode.NETWORK_ERROR

        return ReasonCode.UNKNOWN

    @staticmethod
    def _get_inconclusive_explanation(
        probe_a: ProbeEvidence,
        probe_b: ProbeEvidence,
        probe_c: ProbeEvidence,
        reason: ReasonCode,
    ) -> str:
        """Generate explanation for INCONCLUSIVE classification."""

        explanations = {
            ReasonCode.TIMEOUT: "Probe timeout; server may be down or dropping packets",
            ReasonCode.SERVFAIL: "Server returned SERVFAIL; internal server error",
            ReasonCode.CONTRADICTORY: "Contradictory flags; recursion status unclear",
            ReasonCode.RA_SET_NO_ANSWER: "RA flag set but no valid answer provided",
            ReasonCode.MALFORMED: "Malformed response; possible corruption or attack",
            ReasonCode.TCP_FAIL: "UDP succeeded but TCP fallback failed",
            ReasonCode.RATE_LIMITED: "Possible rate limiting detected",
            ReasonCode.NETWORK_ERROR: f"Network error: {probe_b.error_type}",
            ReasonCode.UNKNOWN: "Unknown reason; see raw probe evidence",
        }

        return explanations.get(reason, "Unknown error")

    @staticmethod
    def mismatch_analysis(
        classification: DNSClass,
        expected: DNSClass,
        probe_evidence: List[ProbeEvidence],
    ) -> str:
        """
        Analyze why classification differs from expected.
        
        Useful for false positive/negative analysis.
        """
        if classification == expected:
            return "Match (no analysis needed)"

        if classification == DNSClass.RECURSIVE and expected != DNSClass.RECURSIVE:
            return "False positive: server detected as recursive but expected otherwise"

        if expected == DNSClass.RECURSIVE and classification != DNSClass.RECURSIVE:
            return "False negative: server expected to be recursive but classified otherwise"

        if classification == DNSClass.INCONCLUSIVE:
            return "Inconclusive result; see reason codes and raw evidence"

        return f"Mismatch: got {classification}, expected {expected}"
