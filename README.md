<<<<<<< HEAD
# AIORI-3-HACKATHON-PROJECTS
This repository will contain the code and resources for the AIORI-3 hackathon that will be developed during the AIORI-3
=======
# A3-PS012-TC113: Authorised DNS Resolver Exposure Assessment Tool

**AIORI-3 Hackathon | Category: Cybersecurity | Problem Statement PS-012**

Reference: RFC 5358 (Preventing Use of Recursive Nameservers in Reflector Attacks)

## Overview

A reproducible, ethical DNS probing tool that determines whether designated LAB DNS servers provide recursion to an authorised external lab client. The tool classifies each server and produces an exposure assessment report.

## Quick Start

```bash
# Validate configuration
make validate

# Run the lab environment
make lab-up

# Execute scan
make scan

# View report
make report

# Full demo (lab up → scan → evaluate → report)
make demo
```

## Features

- **Classification**: RECURSIVE, AUTHORITATIVE_ONLY, REFUSED, INCONCLUSIVE
- **Rate Control**: Configurable QPS, per-server limits, mandatory rate limiting
- **Ground Truth Comparison**: Confusion matrix, precision/recall, false/inconclusive analysis
- **Multi-Format Reports**: JSON, CSV, Markdown, HTML with charts
- **Reproducibility**: Deterministic seed, repeat runs, consistency metrics

## Requirements

- Python 3.11+
- Docker & docker-compose
- dnspython, PyYAML, pydantic, typer, rich, Jinja2, matplotlib, pytest

## Project Structure

```
A3-PS012-TC113/
├── README.md
├── Makefile
├── pyproject.toml
├── configs/
│   ├── targets.yaml
│   └── settings.yaml
├── lab/
│   ├── docker-compose.yml
│   ├── bind-open/
│   ├── bind-acl-refused/
│   ├── bind-auth-only/
│   ├── unbound-open/
│   ├── unbound-refuse/
│   ├── blackhole/
│   ├── flaky/
│   ├── ra-misleading/
│   ├── upstream-auth/
│   └── client/
├── src/dnsprobe/
│   ├── cli.py
│   ├── config.py
│   ├── ratelimit.py
│   ├── probes.py
│   ├── classifier.py
│   ├── groundtruth.py
│   ├── runner.py
│   ├── report.py
│   └── models.py
├── tests/
│   ├── test_classifier.py
│   ├── test_ratelimit.py
│   ├── test_config_guards.py
│   ├── test_groundtruth.py
│   └── integration/test_lab.py
├── reports/
└── docs/
    ├── architecture.md
    ├── pseudocode.md
    ├── methodology.md
    ├── false-inconclusive-analysis.md
    ├── ethics.md
    └── A3-PS012-TC113_Report.pdf
```

## Documentation

- [Architecture & Design](docs/architecture.md)
- [Methodology](docs/methodology.md)
- [Ethics & Scope](docs/ethics.md)
- [Pseudocode](docs/pseudocode.md)

## Hard Constraints

1. Max 20 target servers per run (hard limit)
2. Targets only from explicit allowlist
3. Private/loopback ranges only by default; `--allow-public` flag required for others
4. No Internet-wide scanning or CIDR sweeps
5. No spoofed traffic; standard sockets only
6. No amplification or stress testing
7. Rate control mandatory and cannot be disabled

## References

- RFC 5358: Preventing Use of Recursive Nameservers in Reflector Attacks
- dnspython: https://www.dnspython.org/
- Pydantic: https://docs.pydantic.dev/

---

**Status**: Specification Phase | **Version**: 0.1.0
>>>>>>> 768768a (first commit)
