"""
Report generation.

Generates JSON, CSV, Markdown, and HTML reports with charts and analysis.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template

from .models import ScanResult, ScanRun, DNSClass
from .groundtruth import GroundTruthEvaluator


class ReportGenerator:
    """Generate reports in multiple formats."""

    @staticmethod
    def generate_json_report(
        run: ScanRun,
        evaluation: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Generate JSON report."""
        report_data = {
            "scan_run": run.to_dict(),
            "evaluation": evaluation,
            "generated_at": datetime.now().isoformat(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    @staticmethod
    def generate_csv_report(
        results: List[ScanResult],
        output_path: Path,
    ) -> None:
        """Generate CSV report."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "target_name",
                    "target_ip",
                    "classification",
                    "expected_class",
                    "match",
                    "reason_code",
                    "confidence",
                    "probe_a_rcode",
                    "probe_b_rcode",
                    "probe_c_rcode",
                    "ra_flag",
                    "timestamp",
                ],
            )
            writer.writeheader()

            for result in results:
                probe_a = result.probe_evidence[0] if result.probe_evidence else None
                probe_b = result.probe_evidence[1] if len(result.probe_evidence) > 1 else None
                probe_c = result.probe_evidence[2] if len(result.probe_evidence) > 2 else None

                writer.writerow({
                    "target_name": result.target_name,
                    "target_ip": result.target_ip,
                    "classification": result.classification.value,
                    "expected_class": result.expected_class.value if result.expected_class else "",
                    "match": result.match,
                    "reason_code": result.reason_code.value if result.reason_code else "",
                    "confidence": result.confidence,
                    "probe_a_rcode": probe_a.rcode if probe_a else "",
                    "probe_b_rcode": probe_b.rcode if probe_b else "",
                    "probe_c_rcode": probe_c.rcode if probe_c else "",
                    "ra_flag": probe_b.ra_flag if probe_b else "",
                    "timestamp": result.timestamp.isoformat(),
                })

    @staticmethod
    def generate_markdown_report(
        run: ScanRun,
        evaluation: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Generate Markdown report."""
        md_content = f"""# DNS Resolver Exposure Assessment Report

**Run ID:** {run.run_id}  
**Timestamp:** {run.timestamp.isoformat()}  
**Seed:** {run.seed}

## Executive Summary

This assessment evaluated {len(run.results)} DNS servers for recursion exposure.

- **Total Targets:** {evaluation['metrics']['total_targets']}
- **Matches (Correct):** {evaluation['metrics']['matches']}
- **Mismatches (Incorrect):** {evaluation['metrics']['mismatches']}
- **Inconclusive:** {evaluation['metrics']['inconclusive_count']}
- **Overall Accuracy:** {evaluation['metrics']['accuracy']:.2%}

## Per-Class Metrics

"""
        for cls, metrics in evaluation['metrics']['per_class_metrics'].items():
            md_content += f"""
### {cls}
- Precision: {metrics['precision']:.2%}
- Recall: {metrics['recall']:.2%}
- F1 Score: {metrics['f1']:.2%}
"""

        md_content += """
## Per-Server Findings

| Target | IP | Classification | Expected | Match | Reason |
|--------|----|----|---------|--------|--------|
"""

        for result in run.results:
            md_content += f"| {result.target_name} | {result.target_ip} | {result.classification.value} | "
            md_content += f"{result.expected_class.value if result.expected_class else 'N/A'} | "
            md_content += f"{result.match if result.match is not None else 'N/A'} | "
            md_content += f"{result.reason_code.value if result.reason_code else 'N/A'} |\n"

        if evaluation['mismatches']:
            md_content += """
## Mismatches

"""
            for mismatch in evaluation['mismatches']:
                md_content += f"- **{mismatch['target']} ({mismatch['ip']})**: "
                md_content += f"Expected {mismatch['expected']}, got {mismatch['got']}\n"

        if evaluation['inconclusive_cases']:
            md_content += """
## Inconclusive Cases

"""
            for case in evaluation['inconclusive_cases']:
                md_content += f"- **{case['target']} ({case['ip']})**: "
                md_content += f"Reason: {case['reason']}\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    @staticmethod
    def generate_html_report(
        run: ScanRun,
        evaluation: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Generate HTML report."""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DNS Exposure Assessment Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .metric { display: inline-block; margin: 10px 20px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .recursive { background-color: #ffebee; }
        .authoritative { background-color: #e8f5e9; }
        .refused { background-color: #fff3e0; }
        .inconclusive { background-color: #f3e5f5; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DNS Resolver Exposure Assessment Report</h1>
        
        <p><strong>Run ID:</strong> {{ run_id }}</p>
        <p><strong>Timestamp:</strong> {{ timestamp }}</p>
        
        <h2>Summary</h2>
        <div>
            <div class="metric">
                <div>Total Targets</div>
                <div class="metric-value">{{ total_targets }}</div>
            </div>
            <div class="metric">
                <div>Accuracy</div>
                <div class="metric-value">{{ accuracy_pct }}%</div>
            </div>
            <div class="metric">
                <div>Matches</div>
                <div class="metric-value">{{ matches }}</div>
            </div>
            <div class="metric">
                <div>Inconclusive</div>
                <div class="metric-value">{{ inconclusive }}</div>
            </div>
        </div>
        
        <h2>Results by Server</h2>
        <table>
            <tr>
                <th>Target</th>
                <th>IP</th>
                <th>Classification</th>
                <th>Expected</th>
                <th>Match</th>
                <th>Reason</th>
            </tr>
            {% for result in results %}
            <tr class="{{ result.classification | lower }}">
                <td>{{ result.target_name }}</td>
                <td>{{ result.target_ip }}</td>
                <td>{{ result.classification }}</td>
                <td>{{ result.expected or 'N/A' }}</td>
                <td>{{ result.match or 'N/A' }}</td>
                <td>{{ result.reason or '-' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

        template = Template(html_template)
        results_data = [
            {
                "target_name": r.target_name,
                "target_ip": r.target_ip,
                "classification": r.classification.value,
                "expected": r.expected_class.value if r.expected_class else None,
                "match": r.match,
                "reason": r.reason_code.value if r.reason_code else None,
            }
            for r in run.results
        ]

        html_content = template.render(
            run_id=run.run_id,
            timestamp=run.timestamp.isoformat(),
            total_targets=len(run.results),
            accuracy_pct=f"{evaluation['metrics']['accuracy']*100:.1f}",
            matches=evaluation['metrics']['matches'],
            inconclusive=evaluation['metrics']['inconclusive_count'],
            results=results_data,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
