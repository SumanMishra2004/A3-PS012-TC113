# Ethics & Scope Statement

## Authorized Assessment Scope

This tool is designed for **defensive assessment of authorized lab infrastructure only**.

### What This Tool Is For

✅ Testing your own DNS servers in controlled lab environments  
✅ Identifying misconfigured recursive resolvers within your infrastructure  
✅ Verifying RFC 5358 compliance (access controls on recursive resolvers)  
✅ Educational purposes: understanding DNS recursion and security  
✅ Authorized penetration testing of owned infrastructure  

### What This Tool Must NOT Be Used For

❌ Scanning Internet-wide or unauthorized networks  
❌ Discovering open resolvers on systems you don't own  
❌ DDoS amplification attacks or reflector abuse  
❌ Unauthorized network reconnaissance  
❌ Circumventing intentional access controls  

## Security-by-Design Features

### 1. Explicit Allowlist Only
- Targets must be listed in `configs/targets.yaml`
- No automatic discovery, no CIDR sweeps, no subnet scanning
- Each target explicitly authorized before probing

### 2. Private/Loopback IP Preference
- By default, only accepts 10/8, 172.16/12, 192.168/16, 127/8 ranges
- Public IPs require explicit `--allow-public` flag + confirmation warning
- Prevents accidental scanning of Internet-facing infrastructure

### 3. No Spoofing or Raw Sockets
- Standard UDP/TCP sockets only (via dnspython)
- No packet forging, source IP manipulation, or raw socket access
- Traceable to legitimate DNS client

### 4. No Amplification or Stress Testing
- Fixed, small query set (Probe A, B, C per target)
- No ANY queries, no flood patterns, no large responses
- Respects RFC 5358 principles

### 5. Rate Control is Mandatory
- Cannot be disabled; hard caps enforced
- Default: 5 global QPS, 1 per-server QPS (well below reflection attack speeds)
- Budget tracking prevents accidental runaway

### 6. Controlled Test Zones
- All probes target lab.test and ext.lab (internal only)
- No external zone queries; no interference with real-world DNS
- Upstream-auth isolation prevents information leakage

## Responsible Disclosure

### Before Running This Tool

1. **Verify Authorization**
   - Ensure you own or have explicit permission to test the targets
   - Get written approval from infrastructure owner/security team
   - Document authorization

2. **Notify Stakeholders**
   - Inform DNS operations team
   - Explain testing objectives and scope
   - Agree on timing and rate limits

3. **Review Constraints**
   - Confirm rate limits won't impact production
   - Verify target list is accurate
   - Test in staging first if possible

### After Scanning

1. **Secure Results**
   - Results contain infrastructure details (IPs, resolver types)
   - Treat as sensitive security information
   - Restrict access to authorized personnel

2. **Remediation**
   - Share findings only with authorized operators
   - Provide clear remediation steps per RFC 5358
   - Set timeline for fixes

3. **Re-Test**
   - After fixes, re-run scan to verify improvements
   - Document before/after comparison

## Legal Considerations

### Use Restrictions

This tool is provided for **authorized testing only**. Unauthorized access to computer networks is illegal in most jurisdictions:

- **CFAA (US)**: Computer Fraud and Abuse Act (18 USC §1030)
- **GDPR (EU)**: General Data Protection Regulation (unauthorized scanning = processing)
- **Similar laws**: Exist in most countries

### User Responsibility

By using this tool, you acknowledge:

1. You have explicit authorization to test all targets
2. You understand and accept legal risks
3. You will not use this for unauthorized scanning
4. You will not use results for malicious purposes
5. You will follow responsible disclosure practices

### Warranty Disclaimer

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY.
Misuse is solely the responsibility of the user.

## Ethical Principles

1. **Respect Boundaries**: Only test what you own or have permission for
2. **Minimize Impact**: Rate limits, small queries, scheduled scanning
3. **Transparency**: Document authorization, objectives, and findings
4. **Remediation**: Help fix issues, don't just report them
5. **Confidentiality**: Treat results as sensitive security data

## Acceptable Use Examples

✅ **Scenario 1**: Company testing their own DNS infrastructure  
"We run our DNS servers in a private lab. We want to audit them for RFC 5358 compliance before production deployment."

✅ **Scenario 2**: University penetration testing lab  
"Students use this tool to understand DNS security in controlled lab environment with explicit instructor approval."

✅ **Scenario 3**: Authorized security assessment  
"Our client hired us to audit their DNS configuration. We have written authorization from CISO."

## Unacceptable Use Examples

❌ **Scenario 1**: Scanning the Internet  
"Let's find all open resolvers on the Internet and test them."

❌ **Scenario 2**: Unauthorized testing  
"Let's scan our competitor's DNS servers to see if they're vulnerable."

❌ **Scenario 3**: Preparation for attack  
"We'll use this to discover open resolvers to use in a DDoS amplification attack."

## Questions?

If you have questions about authorization or scope:

1. Consult with your security/legal team
2. Document the use case
3. Review this ethics statement with stakeholders
4. Get explicit written approval before scanning

---

**Remember**: With great tools come great responsibility.
Use ethically. Use legally. Use to improve security, not to harm.
