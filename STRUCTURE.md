# Project Structure Summary

## Repository: A3-PS012-TC113
Authorised DNS Resolver Exposure Assessment Tool for AIORI-3 Hackathon

### Directory Layout

```
A3-PS012-TC113/
├── README.md                      # Project overview
├── Makefile                       # Build automation
├── pyproject.toml                 # Python dependencies & configuration
├── DEVELOPMENT.md                 # Development workflow guide
├── STRUCTURE.md                   # This file
├── .gitignore                     # Git ignore patterns
├── .gitattributes                 # Git attributes
├── .github/
│   └── workflows/
│       └── test.yml              # GitHub Actions CI/CD
├── configs/
│   ├── targets.yaml              # Allowlisted targets (9 servers)
│   └── settings.yaml             # Rate limits, probe configuration
├── lab/                           # Docker lab environment
│   ├── docker-compose.yml        # Orchestration with fixed IPs
│   ├── bind-open/
│   │   ├── named.conf           # Open recursive resolver config
│   │   └── lab.test.zone        # Lab zone file
│   ├── bind-acl-refused/
│   │   ├── named.conf           # ACL-restricted BIND config
│   │   └── lab.test.zone
│   ├── bind-auth-only/          # Placeholder
│   ├── unbound-open/            # Placeholder
│   ├── unbound-refuse/          # Placeholder
│   ├── upstream-auth/           # Authoritative for ext.lab
│   │   ├── named.conf
│   │   ├── ext.lab.zone
│   │   └── query.log            # Query logging (generated)
│   ├── blackhole/               # Placeholder
│   ├── flaky/                   # Placeholder
│   ├── ra-misleading/           # Placeholder
│   └── client/                  # Client container (vantage point)
├── src/dnsprobe/
│   ├── __init__.py              # Package init
│   ├── cli.py                   # CLI: validate, scan, evaluate, report
│   ├── config.py                # Config models, guard rails validation
│   ├── models.py                # Data models (DNSClass, ProbeEvidence, ScanResult)
│   ├── ratelimit.py             # Token bucket rate limiter
│   ├── probes.py                # DNS probe engine (UDP, TCP, retries)
│   ├── classifier.py            # Classification logic (pure functions)
│   ├── groundtruth.py           # Evaluation & confusion matrix
│   ├── runner.py                # Scan orchestration
│   └── report.py                # Report generation (JSON, CSV, MD, HTML)
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py       # Unit tests for classifier
│   ├── test_config_guards.py    # Unit tests for guard rails
│   ├── test_ratelimit.py        # Unit tests for rate limiter
│   ├── test_groundtruth.py      # Unit tests for evaluation
│   └── integration/
│       ├── __init__.py
│       └── test_lab.py          # Integration tests (requires Docker)
├── reports/                      # Generated scan reports (gitignored)
│   └── (sample reports - to be committed)
└── docs/
    ├── architecture.md           # System design, data flow, module breakdown
    ├── pseudocode.md            # Simplified pseudocode (<40 lines)
    ├── methodology.md           # Probe design, classification rules, RFC 5358
    ├── ethics.md                # Scope, authorized use, legal considerations
    ├── false-inconclusive-analysis.md  # Debugging guide, root cause analysis
    └── A3-PS012-TC113_Report.pdf   # (Placeholder for hackathon report)
```

## Key Files by Responsibility

### Configuration & Validation
- `config.py`: Pydantic models, guard rails (max 20 targets, allowlist, IP ranges, rate caps)
- `configs/targets.yaml`: 9 test servers with ground truth
- `configs/settings.yaml`: Rate limits, probe timeouts, expected answers

### Probe Engine
- `probes.py`: DNS query construction, UDP/TCP sending, TC bit handling, retries
- `ratelimit.py`: Token bucket, per-server limiting, global budget

### Classification
- `classifier.py`: Pure functions mapping evidence → RECURSIVE/AUTHORITATIVE_ONLY/REFUSED/INCONCLUSIVE
- `models.py`: ProbeEvidence, ScanResult, DNSClass, ReasonCode data classes

### Execution & Evaluation
- `runner.py`: Orchestration, deterministic ordering, repeat runs
- `groundtruth.py`: Confusion matrix, precision/recall, mismatch analysis

### Output
- `report.py`: JSON, CSV, Markdown, HTML report generation
- `cli.py`: Typer CLI with 4 commands: validate, scan, evaluate, report

### Documentation
- `README.md`: Quick start, features, requirements
- `DEVELOPMENT.md`: Setup, testing, troubleshooting
- `architecture.md`: System design, data flow, module responsibilities
- `methodology.md`: Probe design, classification rules, RFC 5358 alignment
- `pseudocode.md`: Simplified algorithmic reference (<40 lines)
- `ethics.md`: Scope, authorized use, legal considerations, responsible disclosure

## Data Flow

```
targets.yaml + settings.yaml
    ↓
[Load & Guard Rails Validation]
    ↓
[Rate Limiter Gate]
    ↓
[Probe Phase: Probes A, B, C per target]
    ↓
[Classify: Evidence → Class + Reason]
    ↓
[Ground Truth Comparison]
    ↓
[Aggregate Metrics (confusion matrix, accuracy)]
    ↓
[Report Generation: JSON, CSV, MD, HTML]
```

## Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| config.py | test_config_guards.py | 10 unit tests |
| ratelimit.py | test_ratelimit.py | 5 unit tests |
| classifier.py | test_classifier.py | 8 unit tests |
| groundtruth.py | test_groundtruth.py | 4 unit tests |
| integration | test_lab.py | Docker lab tests |

## CLI Commands

```bash
# Validate configurations
dnsprobe validate-config

# Run scans with reproducibility
dnsprobe scan --targets configs/targets.yaml --settings configs/settings.yaml \
  --seed 42 --repeat 3 --out reports/run1

# Evaluate results
dnsprobe evaluate --results reports/run1/results.json --targets configs/targets.yaml

# Generate reports
dnsprobe report --results reports/run1/results.json --format html,md,json,csv
```

## Docker Lab Network

```
Fixed Network: 10.10.0.0/24
- 10.10.0.50   : Client (probe vantage point)
- 10.10.0.101  : bind-open (RECURSIVE)
- 10.10.0.102  : bind-acl-refused (REFUSED)
- 10.10.0.103  : bind-auth-only (AUTHORITATIVE_ONLY)
- 10.10.0.104  : unbound-open (RECURSIVE)
- 10.10.0.105  : unbound-refuse (REFUSED)
- 10.10.0.106  : blackhole (INCONCLUSIVE - TIMEOUT)
- 10.10.0.107  : flaky (INCONCLUSIVE - CONTRADICTORY)
- 10.10.0.108  : ra-misleading (INCONCLUSIVE - RA_SET_NO_ANSWER)
- 10.10.0.200  : upstream-auth (ext.lab authoritative server)
```

## Hard Constraints Enforced

1. **Max 20 targets** (hard limit in TargetsConfig)
2. **Explicit allowlist only** (targets.yaml, no discovery)
3. **Private/loopback IPs default** (10/8, 172.16/12, 192.168/16, 127/8)
4. **No Internet-wide scanning** (no CIDR, no target discovery)
5. **No spoofed traffic** (standard UDP/TCP sockets)
6. **No amplification** (no ANY queries, fixed probe count)
7. **Rate control mandatory** (hard caps: 20 global QPS, 5 per-server QPS, 10 max inflight)

## Testing Commands

```bash
make validate          # Check configuration
make lab-up           # Start Docker lab
make lab-down         # Stop Docker lab
make test             # Run unit + integration tests
make lint             # Code quality checks
make scan             # Run example scan
make evaluate         # Evaluate results
make report           # Generate reports
make demo             # Full end-to-end
make clean            # Clean artifacts
```

## Implementation Status

- [x] Configuration & models (config.py, models.py)
- [x] Guard rails & validation (config.py::GuardRails)
- [x] Rate limiting (ratelimit.py)
- [x] Probe engine (probes.py)
- [x] Classifier (classifier.py)
- [x] Runner & orchestration (runner.py)
- [x] Ground truth evaluation (groundtruth.py)
- [x] Report generation (report.py)
- [x] CLI (cli.py)
- [x] Unit tests (test_*.py)
- [x] Documentation (docs/*.md)
- [x] Docker lab skeleton (lab/)
- [ ] Lab server implementations (work in progress)
- [ ] Integration tests (test_lab.py)
- [ ] Sample report
- [ ] Final verification

## Notes

- This is a **dummy/skeleton** structure demonstrating best practices
- Placeholder server configurations ready for BIND/Unbound setup
- Test suite framework in place; implementations are stubs
- All hard constraints and guard rails enforced at code level
- Reproducible with seed-based randomization
- Designed for ethical, authorized lab testing only
