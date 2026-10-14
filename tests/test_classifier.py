"""Unit tests for classifier module."""

import pytest
from datetime import datetime
from dnsprobe.models import ProbeEvidence, DNSClass, ReasonCode
from dnsprobe.classifier import Classifier


class TestClassifier:
    """Table-driven tests for classification logic."""

    @pytest.fixture
    def dummy_evidence(self):
        """Create dummy probe evidence."""
        return ProbeEvidence(
            probe_name="A",
            query_name="www.lab.test",
            query_type="A",
            rd_bit=True,
            timestamp=datetime.now(),
        )

    def test_recursive_classification(self, dummy_evidence):
        """Test RECURSIVE classification."""
        probe_a = dummy_evidence
        probe_a.probe_name = "A"
        probe_a.rcode = "NOERROR"
        probe_a.aa_flag = False

        probe_b = dummy_evidence
        probe_b.probe_name = "B"
        probe_b.rcode = "NOERROR"
        probe_b.ra_flag = True
        probe_b.answer_section = ["probe.ext.lab. 300 IN A 10.10.0.99"]

        probe_c = dummy_evidence
        probe_c.probe_name = "C"
        probe_c.rd_bit = False

        classification, reason, explanation = Classifier.classify(probe_a, probe_b, probe_c)
        assert classification == DNSClass.RECURSIVE

    def test_refused_classification(self, dummy_evidence):
        """Test REFUSED classification."""
        probe_a = dummy_evidence
        probe_a.rcode = "REFUSED"

        probe_b = dummy_evidence
        probe_b.probe_name = "B"
        probe_b.rcode = "REFUSED"

        probe_c = dummy_evidence

        classification, reason, explanation = Classifier.classify(probe_a, probe_b, probe_c)
        assert classification == DNSClass.REFUSED

    def test_authoritative_only_classification(self, dummy_evidence):
        """Test AUTHORITATIVE_ONLY classification."""
        probe_a = dummy_evidence
        probe_a.rcode = "NOERROR"
        probe_a.aa_flag = True
        probe_a.answer_section = ["www.lab.test. 300 IN A 10.10.0.10"]

        probe_b = dummy_evidence
        probe_b.probe_name = "B"
        probe_b.ra_flag = False

        probe_c = dummy_evidence

        classification, reason, explanation = Classifier.classify(probe_a, probe_b, probe_c)
        assert classification == DNSClass.AUTHORITATIVE_ONLY

    def test_inconclusive_timeout(self, dummy_evidence):
        """Test INCONCLUSIVE with TIMEOUT reason."""
        probe_a = dummy_evidence
        probe_b = dummy_evidence
        probe_b.probe_name = "B"
        probe_b.error_type = "TIMEOUT"
        probe_c = dummy_evidence

        classification, reason, explanation = Classifier.classify(probe_a, probe_b, probe_c)
        assert classification == DNSClass.INCONCLUSIVE
        assert reason == ReasonCode.TIMEOUT

    def test_has_expected_answer(self):
        """Test answer section parsing."""
        evidence = ProbeEvidence(
            probe_name="B",
            query_name="test.lab",
            query_type="A",
            rd_bit=True,
            answer_section=["test.lab. 300 IN A 10.10.0.99"],
        )
        assert Classifier._has_expected_answer(evidence, "10.10.0.99")

    def test_no_expected_answer(self):
        """Test missing expected answer."""
        evidence = ProbeEvidence(
            probe_name="B",
            query_name="test.lab",
            query_type="A",
            rd_bit=True,
            answer_section=["test.lab. 300 IN A 1.2.3.4"],
        )
        assert not Classifier._has_expected_answer(evidence, "10.10.0.99")
