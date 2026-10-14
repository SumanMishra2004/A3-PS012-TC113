# Pseudocode for Mentor Demo

## Main Scan Loop (Simplified)

```pseudo
FUNCTION scanTargets(targets, settings, seed):
    
    // Initialize
    rateLimiter ← new RateLimiter(settings.globalQPS, settings.perServerQPS)
    results ← empty list
    
    // Deterministic ordering
    sortedTargets ← sort(targets, by: IP)
    
    FOR EACH target IN sortedTargets:
        
        // Rate limit gate (mandatory)
        waitTime ← rateLimiter.acquire(target.ip)
        
        IF rateLimiter.budgetExhausted():
            BREAK  // Stop gracefully
        
        // Probe phase
        nonce ← generateDeterministicNonce(seed, targetIndex)
        
        probeA ← sendProbe(target, "www.lab.test", RD=true)
        probeB ← sendProbe(target, nonce + ".probe.ext.lab", RD=true)
        probeC ← sendProbe(target, nonce + ".probe.ext.lab", RD=false)
        
        // Classification
        classification, reason ← classify(probeA, probeB, probeC)
        
        // Ground truth comparison
        match ← (classification == target.expectedClass)
        
        // Store result
        results.append({
            target, 
            classification, 
            reason, 
            match,
            evidence: [probeA, probeB, probeC]
        })
        
        rateLimiter.release()
    
    RETURN results

END FUNCTION
```

## Classification Logic (Simplified)

```pseudo
FUNCTION classify(probeA, probeB, probeC):
    
    // Check for RECURSIVE
    IF probeB.rcode == NOERROR 
       AND probeB.raFlag == true 
       AND hasExpectedAnswer(probeB):
        RETURN (RECURSIVE, null, "...")
    
    // Check for REFUSED
    IF probeA.rcode == REFUSED 
       AND probeB.rcode == REFUSED:
        RETURN (REFUSED, null, "...")
    
    // Check for AUTHORITATIVE_ONLY
    IF probeA.aaFlag == true 
       AND probeA.rcode == NOERROR 
       AND probeB.raFlag == false:
        RETURN (AUTHORITATIVE_ONLY, null, "...")
    
    // INCONCLUSIVE with reason
    reason ← determineReason(probeA, probeB, probeC)
    RETURN (INCONCLUSIVE, reason, "...")

END FUNCTION
```

## Rate Limiter (Token Bucket)

```pseudo
CLASS RateLimiter:
    
    FUNCTION acquire(serverId):
        
        // Global rate limit
        WHILE NOT globalBucket.consume(1):
            SLEEP(1ms)
        
        // Per-server rate limit
        WHILE NOT perServerBucket[serverId].consume(1):
            SLEEP(1ms)
        
        // Check global budget
        IF totalQueries >= globalBudget:
            RAISE BudgetExhausted
        
        totalQueries ← totalQueries + 1

    FUNCTION tokenBucket.refill():
        elapsed ← currentTime - lastRefillTime
        tokens ← min(capacity, tokens + elapsed * refillRate)

END CLASS
```

## Guard Rails (Hard Constraints)

```pseudo
FUNCTION validateConfig(targets, allowPublic):
    
    // Constraint 1: Max 20 targets
    IF targets.length > 20:
        RAISE Error("Max 20 targets")
    
    // Constraint 2: Explicit allowlist only
    FOR EACH target IN targets:
        IF NOT inAllowlist(target.ip):
            RAISE Error("Target not in allowlist")
    
    // Constraint 3: IP range check
    FOR EACH target IN targets:
        IF isPublicIP(target.ip) AND NOT allowPublic:
            RAISE Error("Public IP requires --allow-public")
    
    // Constraint 4: Rate control caps
    IF settings.globalQPS > 20:
        RAISE Error("Global QPS hard cap is 20")
    IF settings.perServerQPS > 5:
        RAISE Error("Per-server QPS hard cap is 5")
    IF settings.maxInflight > 10:
        RAISE Error("Max inflight hard cap is 10")

END FUNCTION
```

**Total Lines**: ~35 (under 40-line limit)
