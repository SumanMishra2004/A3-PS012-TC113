# Methodology & Probe Design

## Objective

Determine whether designated LAB DNS servers provide recursion to an authorised external lab client, classify each as RECURSIVE, AUTHORITATIVE_ONLY, REFUSED, or INCONCLUSIVE, and evaluate against ground truth.

## Scope

- **Lab-only assessment**: Targets are in explicit allowlist (configs/targets.yaml)
- **No Internet-wide scanning**: No CIDR sweeps or target discovery
- **Defensive assessment**: Testing our own infrastructure for misconfiguration
- **Ethical**: No spoofed traffic, no amplification, no stress testing

## Probe Design

### Three-Probe Strategy

#### Probe A: Authoritative Check
- **Query**: `www.lab.test A RD=1`
- **Purpose**: Verify server can answer authoritative zone queries
- **Expected Answer**: `10.10.0.10`
- **Classification Signal**: AA flag, NOERROR response
- **Why**: Establishes baseline capability and identifies servers under our control

#### Probe B: Recursion Check
- **Query**: `<nonce>.probe.ext.lab A RD=1`
- **Purpose**: Determine if server recursively resolves external zone
- **Expected Answer**: `10.10.0.99` (from upstream-auth via recursive lookup)
- **Nonce Strategy**: Prevents caching; unique per probe iteration (e.g., `a1b2c3.probe.ext.lab`)
- **Classification Signal**: RA flag, NOERROR response with expected answer
- **Why**: True indicator of recursion; nonce defeats cache hits

#### Probe C: Control (Non-Recursive)
- **Query**: `<nonce>.probe.ext.lab A RD=0`
- **Purpose**: Distinguish cached/authoritative answers from true recursion
- **Expected Answer**: None (server not authoritative for ext.lab without RD)
- **Classification Signal**: No RA flag, no answer
- **Why**: Separates recursion from caching or misleading AA flags

### Evidence Collection

Each probe captures:
1. **Response Code (RCODE)**: NOERROR, REFUSED, SERVFAIL, etc.
2. **Flags**: AA (Authoritative), RA (Recursive), TC (Truncated)
3. **Answer Section**: Actual records returned
4. **Latency**: Response time in milliseconds
5. **Error Type**: Timeout, socket error, malformed response
6. **Retry Count**: Number of attempts before success

### Query Sequence

1. Try **UDP first** (RFC 1035)
   - If TC bit set → Retry with **TCP** (RFC 1035 §4.2.1)
2. **Retries**: Exponential backoff with seeded jitter
   - Base: 1.5x
   - Max retries: 3
   - Jitter: ±10% of backoff time
3. **Timeout**: 5 seconds per query (configurable)

## Classification Rules

### RECURSIVE
**Criteria**:
- Probe B: RCODE=NOERROR
- Probe B: RA flag set
- Probe B: Contains expected answer (10.10.0.99)

**Evidence Strength**:
- **Confirmed**: If upstream-auth query log shows the nonce (proof of actual recursion)
- **Flag-based**: If only RA flag and answer present (implies recursion)

**False Positive Traps**:
- Server claims RA but returns wrong answer → Caught by expected answer check
- Cached answer with RA flag → Nonce defeats cache

### REFUSED
**Criteria**:
- Probe A: RCODE=REFUSED
- Probe B: RCODE=REFUSED

**Interpretation**: Server explicitly refuses recursion/queries from this client

### AUTHORITATIVE_ONLY
**Criteria**:
- Probe A: AA flag set + NOERROR + answer for lab.test
- Probe B: RA flag NOT set (or no valid recursive answer)

**Interpretation**: Server is authoritative for lab.test, does not recurse to external zones

### INCONCLUSIVE
**Criteria**: Everything else, with reason codes:

1. **TIMEOUT**: No response within 5 seconds
   - Likely cause: Server down, firewall drop, rate limiting

2. **SERVFAIL**: Server returned RCODE=SERVFAIL
   - Likely cause: Internal resolver error, upstream unreachable

3. **RA_SET_NO_ANSWER**: RA flag set but RCODE ≠ NOERROR or no answer section
   - Likely cause: Misleading RA flag, misconfiguration

4. **CONTRADICTORY**: Probe A and B give conflicting recursion indicators
   - Likely cause: Flaky server, complex ruleset

5. **MALFORMED**: Response parsing failed
   - Likely cause: Corrupted response, attacker interference

6. **TCP_FAIL**: UDP succeeded but TCP fallback failed
   - Likely cause: Asymmetric rate limiting, firewall rules

7. **RATE_LIMITED**: Server rate limited or refused (RCODE 9)
   - Likely cause: Our QPS too high, server throttling

8. **NETWORK_ERROR**: Socket error, connection refused, etc.
   - Likely cause: Network misconfiguration, firewall

## Rate Control

**Mandatory** (cannot be disabled):
- Global QPS: 5 (hard cap 20)
- Per-server QPS: 1 (hard cap 5)
- Max concurrent queries: 4 (hard cap 10)
- Global query budget: 1000 queries per run

**Implementation**: Token bucket algorithm with per-server buckets

**Why**: Prevents overwhelming lab infrastructure, respects RFC 5358 principles

## Reproducibility

- **Deterministic target order**: Sorted by IP
- **Seeded nonce generation**: `sha256(seed:iteration)[:12]`
- **Seeded jitter**: Reproducible backoff with given seed
- **`--seed 42`**: Same seed → Same nonce sequence → Consistent results
- **`--repeat N`**: Multiple runs with same seed for consistency analysis

## False Positive / Inconclusive Analysis

### When Classification ≠ Expected

1. **False Positive (RECURSIVE when not)**:
   - Check: Does upstream-auth log show nonce?
   - Check: Was expected answer actually correct?
   - Check: Any RA flag tricks or spoofing?

2. **False Negative (not RECURSIVE when is)**:
   - Check: Rate limiting hit?
   - Check: Nonce collision with cache?
   - Check: Network issues during probe?

3. **Inconclusive**:
   - See reason code in result
   - Examine raw probe evidence
   - Review timing and retry counts

### Remediation (RFC 5358)

**For RECURSIVE servers**:
- Restrict recursion to authorized clients (ACLs)
- Move resolver to separate IP/server
- Update firewall rules

**For AUTHORITATIVE_ONLY servers**:
- Correct; no remediation needed

**For REFUSED servers**:
- Verify ACLs are correct
- Check if intentional (should be AUTHORITATIVE_ONLY instead)

## Limitations

1. **No Spoofing Detection**: Cannot verify source-IP validation without raw sockets
2. **DNS Sec**: DNSSEC validation out of scope
3. **Cache Poisoning**: Limited detection; mitigation is nonce strategy
4. **Timing Attacks**: Not analyzed
5. **External Zones**: Only test against ext.lab; real Internet zones excluded

## References

- RFC 1035: DNS Format & Concepts
- RFC 5358: Preventing Use of Recursive Nameservers in Reflector Attacks
- RFC 2308: DNS NCACHE (Negative Caching)
