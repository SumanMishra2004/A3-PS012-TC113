"""Unit tests for ground truth evaluation."""

import pytest
from datetime import datetime
from dnsprobe.models import ScanResult, DNSClass, ConfusionMatrix
from dnsprobe.groundtruth import GroundTruthEvaluator


class TestConfusionMatrix:
    """Tests for confusion matrix metrics."""

    def test_accuracy_calculation(self):
        """Test accuracy metric."""
        matrix = ConfusionMatrix()
        matrix.true_positives[DNSClass.RECURSIVE] = 8
        matrix.true_negatives[DNSClass.RECURSIVE] = 2
        matrix.false_positives[DNSClass.RECURSIVE] = 0
        matrix.false_negatives[DNSClass.RECURSIVE] = 0

        assert matrix.accuracy() == 1.0

    def test_precision_calculation(self):
        """Test precision metric."""
        matrix = ConfusionMatrix()
        matrix.true_positives[DNSClass.RECURSIVE] = 8
        matrix.false_positives[DNSClass.RECURSIVE] = 2

        precision = matrix.precision(DNSClass.RECURSIVE)
        assert precision == 0.8

    def test_recall_calculation(self):
        """Test recall metric."""
        matrix = ConfusionMatrix()
        matrix.true_positives[DNSClass.RECURSIVE] = 8
        matrix.false_negatives[DNSClass.RECURSIVE] = 2

        recall = matrix.recall(DNSClass.RECURSIVE)
        assert recall == 0.8

    def test_f1_score(self):
        """Test F1 score calculation."""
        matrix = ConfusionMatrix()
        matrix.true_positives[DNSClass.RECURSIVE] = 8
        matrix.false_positives[DNSClass.RECURSIVE] = 2
        matrix.false_negatives[DNSClass.RECURSIVE] = 2

        f1 = matrix.f1_score(DNSClass.RECURSIVE)
        precision = 8 / 10
        recall = 8 / 10
        expected_f1 = 2 * (precision * recall) / (precision + recall)
        assert abs(f1 - expected_f1) < 0.001


class TestGroundTruthEvaluator:
    """Tests for evaluation logic."""

    def test_evaluate_with_ground_truth(self):
        """Test evaluation against ground truth."""
        results = [
            ScanResult(
                target_name="srv1",
                target_ip="10.10.0.1",
                target_port=53,
                classification=DNSClass.RECURSIVE,
                expected_class=DNSClass.RECURSIVE,
                timestamp=datetime.now(),
            ),
            ScanResult(
                target_name="srv2",
                target_ip="10.10.0.2",
                target_port=53,
                classification=DNSClass.REFUSED,
                expected_class=DNSClass.REFUSED,
                timestamp=datetime.now(),
            ),
        ]

        evaluation = GroundTruthEvaluator.evaluate(results)
        assert evaluation["metrics"]["accuracy"] == 1.0
        assert evaluation["metrics"]["matches"] == 2
        assert evaluation["metrics"]["mismatches"] == 0

    def test_evaluate_with_mismatches(self):
        """Test evaluation with mismatches."""
        results = [
            ScanResult(
                target_name="srv1",
                target_ip="10.10.0.1",
                target_port=53,
                classification=DNSClass.RECURSIVE,
                expected_class=DNSClass.AUTHORITATIVE_ONLY,
                timestamp=datetime.now(),
            ),
        ]

        evaluation = GroundTruthEvaluator.evaluate(results)
        assert evaluation["metrics"]["accuracy"] == 0.0
        assert evaluation["metrics"]["mismatches"] == 1
        assert len(evaluation["mismatches"]) == 1
