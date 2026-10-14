# Architecture & Design

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DNS Probe Scanner                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐     ┌──────────────┐  │
│  │ Config Load  │ ──→  │ Guard Rails  │ ──→ │  Rate Limit  │  │
│  │              │      │  Validation  │     │   Enforcer   │  │
│  └──────────────┘      └──────────────┘     └──────────────┘  │
│                                                    │             │
│                                                    ▼             │
│  ┌──────────────┐      ┌──────────────┐     ┌──────────────┐  │
│  │   Targets    │      │  Probe Engine│ ◄── │   Per-Server │  │
│  │  (Allowlist) │ ──→  │              │     │   Rate Limiter   │  │
│  └──────────────┘      └──────────────┘     └──────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Probe A (Authoritative)                                │  │
│  │  Probe B (Recursion with nonce)                         │  │
│  │  Probe C (Control, RD=0)                                │  │
│  │  → Evidence collection (RCODE, flags, answers, latency) │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Classifier (Pure Functions)                            │  │
│  │  → RECURSIVE / AUTHORITATIVE_ONLY / REFUSED /           │  │
│  │    INCONCLUSIVE with reason codes                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Ground Truth Comparison                                │  │
│  │  → Confusion matrix, accuracy, precision/recall         │  │
│  │  → Mismatch & inconclusive analysis                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Report Generation                                      │  │
│  │  → JSON, CSV, Markdown, HTML + Charts                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Module Breakdown

### `config.py`
- Pydantic models for type-safe configuration
- Guard rails enforcement:
  - Max 20 targets (hard limit)
  - Explicit allowlist validation
  - Private/loopback IP check
  - Rate control cap enforcement

### `ratelimit.py`
- Token bucket algorithm
- Per-server token buckets
- Global query budget tracking
- Mandatory, non-disableable

### `probes.py`
- DNS probe construction (A, B, C)
- UDP send with TCP fallback on TC bit
- Exponential backoff with jitter
- Raw evidence collection

### `classifier.py`
- Pure classification functions
- Evidence → class mapping
- Reason code generation
- Edge case handling (RA without answer, etc.)

### `runner.py`
- Orchestration logic
- Deterministic target ordering
- Repeat run management
- Reproducibility with seed

### `groundtruth.py`
- Confusion matrix computation
- Precision/recall/F1 metrics
- Mismatch identification
- Repeatability analysis

### `report.py`
- Multi-format reporting (JSON, CSV, MD, HTML)
- Chart generation (matplotlib)
- Template rendering (Jinja2)

### `cli.py`
- Typer-based CLI
- Commands: validate, scan, evaluate, report
- Rich table display

## Data Flow

```
targets.yaml + settings.yaml
    ↓
[Load & Validate]
    ↓
[Guard Rails Check]
    ↓
[Rate Limiter Gate]
    ↓
[For each Target]
  └─ [Probe A, B, C]
      └─ [Collect Evidence]
          └─ [Classify]
              └─ [Compare vs Ground Truth]
    ↓
[Aggregate Metrics]
    ↓
[Generate Reports]
```

## Probe Design

### Probe A (Authoritative Check)
- Query: `www.lab.test A RD=1`
- Expected answer: `10.10.0.10`
- Purpose: Verify server can answer authoritative zone

### Probe B (Recursion Check)
- Query: `<nonce>.probe.ext.lab A RD=1`
- Expected answer: `10.10.0.99` (from upstream-auth via recursion)
- Purpose: Determine if server recurses

### Probe C (Control)
- Query: `<nonce>.probe.ext.lab A RD=0`
- Purpose: Distinguish cache/recursion from authoritative answers

## Classification Decision Tree

```
if Probe B returns NOERROR with expected answer and RA=1:
    → RECURSIVE
elif Probe A and Probe B both REFUSED:
    → REFUSED
elif Probe A has AA=1 with answer AND Probe B RA=0:
    → AUTHORITATIVE_ONLY
else:
    → INCONCLUSIVE (with reason code: TIMEOUT, SERVFAIL, etc.)
```

## Hard Constraints Enforced

1. **Target Count**: Max 20 per run (validated at config load)
2. **Allowlist**: No targets outside explicit targets.yaml
3. **IP Ranges**: Private by default, public requires `--allow-public`
4. **No Scanning**: No CIDR sweeps, target discovery, or Internet-wide probes
5. **No Spoofing**: Standard UDP/TCP sockets, no raw packets
6. **No Amplification**: No ANY queries, no flooding, fixed probe count
7. **Rate Control**: Mandatory, hard caps on global/per-server QPS

## Test Coverage

- **Unit Tests** (test_classifier.py, test_config_guards.py, test_ratelimit.py, test_groundtruth.py)
  - Table-driven classification tests
  - Guard rail validation
  - Rate limiter behavior
  - Metric calculations

- **Integration Tests** (tests/integration/test_lab.py)
  - Docker lab startup
  - End-to-end scanning
  - Repeatability with seed

## Reproducibility

- Deterministic target order (sorted by IP)
- Seeded nonce generation
- Seeded jitter
- `--seed 42` flag for deterministic runs
- `--repeat N` for consistency verification
