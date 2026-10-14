# Development Guide

## Project Setup

### Prerequisites
- Python 3.11+
- Docker & docker-compose
- git

### Installation

```bash
# Clone repository
git clone https://github.com/aiori-hackathon/A3-PS012-TC113.git
cd A3-PS012-TC113

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Verification

```bash
# Validate configuration
make validate

# Run unit tests
make test

# Check linters
make lint
```

## Development Workflow

### Phase 1: Configuration & Guard Rails
- [x] Define pydantic models (config.py, models.py)
- [x] Implement guard rails (config.py::GuardRails)
- [ ] Write unit tests (test_config_guards.py)

### Phase 2: Docker Lab
- [ ] Create docker-compose.yml with fixed network
- [ ] Build BIND and Unbound configurations (bind-open, bind-acl-refused, etc.)
- [ ] Verify manual probing works: `dig @10.10.0.101 www.lab.test`

### Phase 3: Probe Engine
- [x] Implement probes.py (UDP, TCP fallback, retries)
- [x] Implement ratelimit.py (token bucket)
- [ ] Write unit tests (test_ratelimit.py)
- [ ] Test manual probe sending

### Phase 4: Classifier
- [x] Implement classifier.py (pure functions)
- [x] Define reason codes
- [ ] Write comprehensive unit tests (test_classifier.py)
- [ ] Table-driven test cases

### Phase 5: Runner & Ground Truth
- [x] Implement runner.py (orchestration)
- [x] Implement groundtruth.py (evaluation)
- [ ] Write unit tests (test_groundtruth.py)
- [ ] Test repeat runs

### Phase 6: Reporting
- [x] Implement report.py (JSON, CSV, MD, HTML)
- [ ] Generate sample report
- [ ] Test chart generation

### Phase 7: CLI
- [x] Implement cli.py (typer commands)
- [ ] Test all commands
- [ ] Live table display

### Phase 8: Integration & Docs
- [ ] Integration tests (tests/integration/test_lab.py)
- [ ] `make demo` end-to-end test
- [ ] Sample report committed to repo
- [ ] Final documentation review

## Testing

### Run All Tests
```bash
make test
```

### Run Specific Tests
```bash
# Unit tests only
pytest tests/ -m "not lab" -v

# Classifier tests
pytest tests/test_classifier.py -v

# Integration tests (requires Docker)
pytest tests/integration/ -v -m lab
```

### Coverage Report
```bash
pytest --cov=src/dnsprobe --cov-report=html
open htmlcov/index.html
```

## Code Quality

### Format Code
```bash
black src/dnsprobe tests
isort src/dnsprobe tests
```

### Lint
```bash
pylint src/dnsprobe
```

### Type Checking
```bash
mypy src/dnsprobe
```

### All Checks
```bash
make lint
```

## Docker Lab

### Start Lab
```bash
make lab-up
```

### Stop Lab
```bash
make lab-down
```

### Manual Testing
```bash
# Enter client container
docker exec -it a3ps012tc113-client-1 bash

# Test a resolver
dig @10.10.0.101 www.lab.test
dig @10.10.0.101 test.probe.ext.lab

# Check upstream logs
docker logs a3ps012tc113-upstream-auth-1 | grep test.probe
```

## Common Tasks

### Add New Dependency
```bash
# Edit pyproject.toml, then:
pip install -e ".[dev]"
```

### Create New Probe Type
1. Add to `probe_design` in settings.yaml
2. Implement in `runner.py::_probe_single_target()`
3. Update classifier rules

### Add New Report Format
1. Add method to `report.py::ReportGenerator`
2. Call from CLI command
3. Test output format

### Update Guard Rails
1. Modify `config.py::GuardRails.validate_targets()`
2. Add constraint check
3. Add unit test

## Debugging

### Enable Debug Logging
```python
# In cli.py or runner.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Raw Responses
```bash
# Enable in settings.yaml
debug:
  save_raw_responses: true
```

### Manual Probe Debugging
```python
from dnsprobe.probes import ProbeExecutor, ProbeRequest

req = ProbeRequest(
    probe_name="A",
    query_name="www.lab.test",
    server_ip="10.10.0.101",
)
evidence = ProbeExecutor.send_probe(req)
print(evidence)
```

## Git Workflow

### Commits
```bash
# Small, focused commits
git add src/dnsprobe/config.py tests/test_config.py
git commit -m "Add rate control hard cap validation"

# Reference spec tasks if applicable
git commit -m "Implement classifier (Phase 4 task #2)"
```

### Branches
```bash
# Feature branch
git checkout -b feature/phase-4-classifier

# Bug fix branch
git checkout -b fix/inconclusive-timeout

# Development tracking
git log --oneline --all  # View progress
```

## Performance Considerations

- Rate limiting is enforced; operations are throttled by design
- Per-server token buckets minimize per-target latency
- Global budget prevents runaway scans
- DNS queries cached by nonce strategy

## Security Considerations

- Never commit configs with real credentials
- Use `.env` for environment-specific settings (gitignored)
- Results contain infrastructure info; treat as sensitive
- No logging of full DNS responses in default mode

## References

- [RFC 1035 - DNS Format](https://tools.ietf.org/html/rfc1035)
- [RFC 5358 - Recursive Nameservers](https://tools.ietf.org/html/rfc5358)
- [dnspython Documentation](https://www.dnspython.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -e ".[dev]"` |
| DNS queries timeout | Check docker-compose is running, targets reachable |
| Tests fail on startup | Run `make validate` to check config |
| Rate limiter too strict | Lower QPS in settings.yaml |
| Container crashes | `docker logs <container>` for errors |

---

For questions or issues, check the docs/ directory or raise an issue.
