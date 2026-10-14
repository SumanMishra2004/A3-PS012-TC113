"""
Ground truth comparison and evaluation metrics.

Compares probe results against expected classes, computes confusion matrix,
precision/recall, and analyzes mismatches.
"""

from typing import List, Dict, Any
from collections import defaultdict
from .models import ScanResult, DNSClass, ConfusionMatrix


class GroundTruthEvaluator:
    """Evaluate results against ground truth."""

    @staticmethod
    def evaluate(
        results: List[ScanResult],
        strict: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate results against ground truth.
        
        Returns:
            Dictionary with metrics, confusion matrix, mismatches, etc.
        """
        # Check for missing expected classes
        missing_expected = [
            r for r in results if r.expected_class is None
        ]
        if missing_expected and strict:
            raise ValueError(
                f"Missing expected_class for {len(missing_expected)} results"
            )

        # Mark matches
        for result in results:
            if result.expected_class is not None:
                result.match = result.classification == result.expected_class

        # Compute confusion matrix
        confusion = GroundTruthEvaluator._build_confusion_matrix(results)

        # Find mismatches
        mismatches = [r for r in results if r.match is False]
        inconclusive = [r for r in results if r.classification == DNSClass.INCONCLUSIVE]

        # Compute metrics
        metrics = {
            "total_targets": len(results),
            "matches": sum(1 for r in results if r.match is True),
            "mismatches": len(mismatches),
            "inconclusive_count": len(inconclusive),
            "accuracy": confusion.accuracy(),
            "per_class_metrics": {
                cls.value: {
                    "precision": confusion.precision(cls),
                    "recall": confusion.recall(cls),
                    "f1": confusion.f1_score(cls),
                }
                for cls in DNSClass
            },
        }

        return {
            "metrics": metrics,
            "confusion_matrix": GroundTruthEvaluator._matrix_to_dict(confusion),
            "mismatches": [
                {
                    "target": m.target_name,
                    "ip": m.target_ip,
                    "expected": m.expected_class.value if m.expected_class else None,
                    "got": m.classification.value,
                    "reason": m.reason_code.value if m.reason_code else None,
                }
                for m in mismatches
            ],
            "inconclusive_cases": [
                {
                    "target": i.target_name,
                    "ip": i.target_ip,
                    "reason": i.reason_code.value if i.reason_code else None,
                    "expected": i.expected_class.value if i.expected_class else None,
                }
                for i in inconclusive
            ],
        }

    @staticmethod
    def _build_confusion_matrix(results: List[ScanResult]) -> ConfusionMatrix:
        """Build confusion matrix from results."""
        matrix = ConfusionMatrix()

        for result in results:
            if result.expected_class is None or result.match is None:
                continue

            predicted = result.classification
            actual = result.expected_class

            if result.match:
                # True positive/negative
                if predicted not in matrix.true_positives:
                    matrix.true_positives[predicted] = 0
                matrix.true_positives[predicted] += 1
            else:
                # False positive/negative
                if predicted not in matrix.false_positives:
                    matrix.false_positives[predicted] = 0
                matrix.false_positives[predicted] += 1

                if actual not in matrix.false_negatives:
                    matrix.false_negatives[actual] = 0
                matrix.false_negatives[actual] += 1

        return matrix

    @staticmethod
    def _matrix_to_dict(matrix: ConfusionMatrix) -> Dict[str, Any]:
        """Convert confusion matrix to dictionary."""
        return {
            "true_positives": {k.value: v for k, v in matrix.true_positives.items()},
            "false_positives": {k.value: v for k, v in matrix.false_positives.items()},
            "false_negatives": {k.value: v for k, v in matrix.false_negatives.items()},
            "true_negatives": {k.value: v for k, v in matrix.true_negatives.items()},
        }

    @staticmethod
    def analyze_false_positives(
        results: List[ScanResult],
    ) -> List[Dict[str, Any]]:
        """Analyze false positive cases."""
        analysis = []
        for result in results:
            if result.match is False and result.expected_class is not None:
                if result.classification in [DNSClass.RECURSIVE, DNSClass.AUTHORITATIVE_ONLY]:
                    analysis.append({
                        "target": result.target_name,
                        "got": result.classification.value,
                        "expected": result.expected_class.value,
                        "likely_cause": GroundTruthEvaluator._likely_false_positive_cause(result),
                    })
        return analysis

    @staticmethod
    def _likely_false_positive_cause(result: ScanResult) -> str:
        """Determine likely cause of false positive."""
        if result.reason_code:
            return f"Reason code: {result.reason_code.value}"

        if result.classification == DNSClass.RECURSIVE:
            return "RA flag set with answer; possible false recursive answer"

        if result.classification == DNSClass.AUTHORITATIVE_ONLY:
            return "AA flag set; possible misleading authority indication"

        return "Unknown cause; see raw probe evidence"


class RepeatabilityAnalyzer:
    """Analyze consistency across repeated runs."""

    @staticmethod
    def analyze_repeatability(
        runs: List[List[ScanResult]],
    ) -> Dict[str, Any]:
        """
        Compare multiple runs for consistency.
        
        Args:
            runs: List of results from multiple runs
            
        Returns:
            Consistency metrics
        """
        if len(runs) < 2:
            return {"error": "Need at least 2 runs for repeatability analysis"}

        # Group results by target
        by_target: Dict[str, List[DNSClass]] = defaultdict(list)
        for run in runs:
            for result in run:
                by_target[result.target_name].append(result.classification)

        # Compute consistency per target
        consistency = {}
        all_consistent = True
        for target, classifications in by_target.items():
            unique_classes = set(classifications)
            is_consistent = len(unique_classes) == 1
            consistency[target] = {
                "consistent": is_consistent,
                "classifications": [c.value for c in classifications],
            }
            if not is_consistent:
                all_consistent = False

        return {
            "all_consistent": all_consistent,
            "per_target_consistency": consistency,
            "num_runs": len(runs),
        }
