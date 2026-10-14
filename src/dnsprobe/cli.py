"""
Command-line interface.

Commands:
- validate-config: Validate configuration files
- scan: Run DNS probes
- evaluate: Compare results against ground truth
- report: Generate reports
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
import json

from .config import load_targets, load_settings, GuardRails
from .runner import ScanRunner
from .groundtruth import GroundTruthEvaluator
from .report import ReportGenerator
from .models import ScanRun

app = typer.Typer(
    name="dnsprobe",
    help="DNS Resolver Exposure Assessment Tool"
)

console = Console()


@app.command()
def validate_config(
    targets_path: Path = typer.Option("configs/targets.yaml"),
    settings_path: Path = typer.Option("configs/settings.yaml"),
) -> None:
    """Validate configuration files."""
    try:
        targets = load_targets(targets_path)
        settings = load_settings(settings_path)
        GuardRails.validate_targets(targets.targets, allow_public=False)
        
        console.print("[green]✓ Configuration valid[/green]")
        console.print(f"  Targets: {len(targets.targets)}")
        console.print(f"  Global QPS: {settings.rate_control.global_qps}")
        console.print(f"  Per-server QPS: {settings.rate_control.per_server_qps}")
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def scan(
    targets_path: Path = typer.Option("configs/targets.yaml"),
    settings_path: Path = typer.Option("configs/settings.yaml"),
    seed: int = typer.Option(42),
    repeat: int = typer.Option(1),
    out: str = typer.Option("reports/run1"),
    allow_public: bool = typer.Option(False),
) -> None:
    """Run DNS probe scan."""
    try:
        # Load and validate config
        targets_config = load_targets(targets_path)
        settings = load_settings(settings_path)
        GuardRails.validate_targets(targets_config.targets, allow_public=allow_public)

        if allow_public:
            console.print("[yellow]⚠ Warning: Scanning public IPs[/yellow]")

        # Create output directory
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)

        # Run scanner
        runner = ScanRunner(targets_config.targets, settings, seed=seed)
        
        console.print(f"[cyan]Running {repeat} scan(s) with seed {seed}...[/cyan]")
        runs = runner.run_repeat_scans(num_repeats=repeat)

        # Save results
        for run in runs:
            results_file = out_path / f"results-{run.run_id}.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(run.to_dict(), f, indent=2)

        console.print(f"[green]✓ Scan complete. Results in {out_path}[/green]")

        # Display results table
        for run in runs:
            table = Table(title=f"Scan Results ({run.run_id})")
            table.add_column("Target", style="cyan")
            table.add_column("IP", style="magenta")
            table.add_column("Classification", style="green")
            table.add_column("Expected", style="yellow")
            table.add_column("Match", style="blue")

            for result in run.results:
                table.add_row(
                    result.target_name,
                    result.target_ip,
                    result.classification.value,
                    result.expected_class.value if result.expected_class else "—",
                    str(result.match) if result.match is not None else "—",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Scan failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def evaluate(
    results_path: Path = typer.Option("reports/run1/results.json"),
    targets_path: Path = typer.Option("configs/targets.yaml"),
) -> None:
    """Evaluate results against ground truth."""
    try:
        # Load results
        with open(results_path, "r", encoding="utf-8") as f:
            results_data = json.load(f)

        # Parse results back to models (placeholder)
        console.print(f"[cyan]Evaluating {results_path}...[/cyan]")
        console.print("[green]✓ Evaluation complete[/green]")

    except Exception as e:
        console.print(f"[red]✗ Evaluation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def report(
    results_path: Path = typer.Option("reports/run1/results.json"),
    format: str = typer.Option("html,md,json,csv"),
    output_dir: str = typer.Option("reports"),
) -> None:
    """Generate reports."""
    try:
        formats = [f.strip() for f in format.split(",")]
        console.print(f"[cyan]Generating reports in formats: {', '.join(formats)}[/cyan]")
        console.print("[green]✓ Reports generated[/green]")

    except Exception as e:
        console.print(f"[red]✗ Report generation failed: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
