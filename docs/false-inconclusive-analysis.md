# False Positive / Inconclusive Result Analysis

## Overview

When probe results don't match expected ground truth or classification is INCONCLUSIVE, we need to diagnose why. This document provides decision trees and analysis strategies.

## False Positive Analysis

### Case 1: Classified as RECURSIVE, Expected AUTHORITATIVE_ONLY

**Possible Causes**:

1. **Misleading RA Flag**
   - Server sets RA flag but doesn't actually recurse
   - Check: Does Probe C (RD=0) also have RA flag?
   - Evidence: If Probe C RA=1 and Probe B RA=1, but B doesn't have upstream log entry → Flag-based false positive

2. **Cached Answer**
   - Server answered from cache with RA flag set
   - Check: Nonce uniqueness; is nonce collision possible?
   - Evidence: Multiple runs with same nonce get same answer (cache hit)
   - Solution: Increase nonce entropy, reduce cache TTL

3. **Recursive Zone Delegation**
   - Server is authoritative for lab.test but configured to recurse for other zones
   - Check: Is it supposed to be hybrid (auth + recursive)?
   - Evidence: Probe A returns AA=1, Probe B returns RA=1 with external answer

4. **ACL Misconfiguration**
   - Server should have denied us recursion but didn't
   - Check: Server config; verify ACL rules
   - Evidence: Recurses to us when it should refuse

**Remediation**:
- Disable recursion or restrict to authorized clients
- Set RA flag only when actually recursing
- Use separate IPs for auth and recursive servers

### Case 2: Classified as RECURSIVE, Expected REFUSED

**Possible Causes**:

1. **ACL Not Applied**
   - Server was supposed to have ACL denying us
   - Check: Server config file; is rule syntactically correct?
   - Evidence: `recurses to us` when should see RCODE=REFUSED

2. **Subnet Mismatch**
   - ACL targets wrong subnet/source IP
   - Check: What's our client's actual IP in the lab?
   - Evidence: Lab config vs actual container IPs

3. **Timing Window**
   - ACL changed between config commit and test
   - Check: Was config recently modified?
   - Evidence: Check server restart time vs scan time

**Remediation**:
- Review and fix ACL rules
- Verify subnet ranges
- Restart services to apply config
- Re-test

### Case 3: Classified as AUTHORITATIVE_ONLY, Expected RECURSIVE

**Possible Causes**:

1. **Recursion Disabled**
   - Recursion should be enabled but is disabled
   - Check: Server config; recursion setting
   - Evidence: All recursive probes get RCODE=REFUSED or RA=0

2. **Upstream Resolution Failed**
   - Server configured to recurse but can't reach upstream
   - Check: Can Probe B reach the upstream server?
   - Evidence: RCODE=SERVFAIL instead of expected answer

3. **Nonce Zone Not Configured**
   - Upstream-auth not reachable or configured as forward zone
   - Check: Resolver's stub zone or forward config for ext.lab
   - Evidence: RCODE=NXDOMAIN or REFUSED for nonce queries

**Remediation**:
- Enable recursion in server config
- Verify upstream server connectivity
- Configure forward/stub zones correctly
- Restart services

## Inconclusive Result Analysis

### TIMEOUT Reasons

**Most Likely**:
- Server is offline or container not running
- Firewall blocking queries
- Server rate-limiting us (dropping packets)

**Diagnostic Steps**:
```bash
# Check if server is reachable
ping <server_ip>

# Try a simple query manually
dig @<server_ip> www.lab.test

# Check for firewall rules
docker logs <container_name>

# Review rate limit settings
```

**Resolution**:
- Start container
- Fix firewall rules
- Increase server QPS limits
- Retry with lower rate

### SERVFAIL Reasons

**Most Likely**:
- Upstream server unreachable
- DNS FORWARDERS misconfigured
- Zone file missing
- DNSSEC validation failure

**Diagnostic Steps**:
```bash
# Check upstream connectivity
dig @<upstream_ip> <zone>

# Verify zone file
cat <zone_file_path>

# Check server logs
docker logs --tail 100 <container_name>
```

**Resolution**:
- Fix upstream address
- Reload zone files
- Disable DNSSEC if not needed
- Restart server

### RA_SET_NO_ANSWER Reasons

**Most Likely**:
- Server claims recursion but returns error
- RA flag set incorrectly in response template
- Upstream recursion refused

**Diagnostic Steps**:
```bash
# Compare Probe B response fields
dnsprobe scan | grep -A 10 <target>

# Check for RCODE
# If RA=1 but RCODE ≠ NOERROR → Problem

# Test upstream manually
dig @<upstream> <nonce>.probe.ext.lab
```

**Resolution**:
- Fix server template response
- Remove spurious RA flag
- Verify upstream allows recursion

### CONTRADICTORY Reasons

**Most Likely**:
- Server behaves inconsistently
- Flaky network or container
- Multiple server instances with different configs

**Diagnostic Steps**:
```bash
# Run same probe multiple times
for i in {1..5}; do
  dnsprobe scan --targets <target>
done

# Check consistency
# Review logs across runs
```

**Resolution**:
- Restart container
- Verify all instances have same config
- Fix flaky network issues
- Add network redundancy

### TCP_FAIL Reasons

**Most Likely**:
- Server handles UDP but not TCP
- Firewall asymmetric (UDP pass, TCP drop)
- TCP handler thread crashed

**Diagnostic Steps**:
```bash
# Test UDP directly
dig +short @<server_ip> <zone> +noall

# Test TCP explicitly
dig +tcp +short @<server_ip> <zone> +noall

# Check server logs
docker logs <container_name> | grep tcp
```

**Resolution**:
- Enable TCP in server config
- Fix firewall rules for TCP
- Restart DNS service
- Check for crashed processes

### RATE_LIMITED Reasons

**Most Likely**:
- Our QPS too high
- Server has rate limiting
- Query frequency triggered throttling

**Diagnostic Steps**:
```bash
# Check configured QPS
grep global_qps configs/settings.yaml
grep per_server_qps configs/settings.yaml

# Test with lower QPS manually
dnsprobe scan --settings configs/settings-slow.yaml
```

**Resolution**:
- Lower global or per-server QPS in settings
- Increase server rate limit
- Spread queries over longer time period

### NETWORK_ERROR Reasons

**Most Likely**:
- Host/container connectivity issue
- DNS port blocked
- Socket error (protocol issue)

**Diagnostic Steps**:
```bash
# Check network connectivity
ping <server_ip>

# Check port accessibility
nc -zv <server_ip> 53

# Review system logs
dmesg | tail

# Check Docker network
docker network inspect bridge
```

**Resolution**:
- Fix container networking
- Open DNS port (53)
- Check host firewall
- Verify Docker bridge configuration

## Systematic Debugging Workflow

1. **Categorize the Problem**
   - False positive/negative? Inconclusive?
   - Which classification? What was expected?

2. **Isolate the Evidence**
   - Pull raw probe data
   - Note RCODE, flags, answer section

3. **Form Hypothesis**
   - What behavior would cause this classification?
   - What's our assumption?

4. **Test Hypothesis**
   - Manual dig/nslookup query
   - Check server configuration
   - Review logs

5. **Verify Fix**
   - Re-run scan for that target
   - Confirm classification changed
   - Document root cause

## Logging for Debugging

Enable verbose logging:
```yaml
# settings.yaml
debug:
  log_level: DEBUG
  save_raw_responses: true
  upstream_log_parsing: true
```

This will:
- Save complete probe responses
- Parse upstream-auth logs
- Generate detailed classified reasons
