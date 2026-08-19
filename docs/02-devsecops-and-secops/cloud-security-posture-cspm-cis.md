# Cloud Security Posture Management (CSPM) & CIS Benchmarks

!!! info "Skill metadata"
    **Name** `cloud-security-posture-cspm-cis` · **Level** `senior` · **Tags** `cspm` `prowler` `cis-benchmark` `cloud-security` `iam` `secops`

    "Cloud Security Posture Management: Prowler and ScoutSuite multi-cloud audits, CIS Benchmark baselines for AWS, Azure and GCP, over-permissive IAM discovery, and exception workflow. Use when auditing an account or organization's security posture, finding unused and over-permissive permissions across hundreds of roles, preparing for a CIS or compliance review, or triaging misconfiguration findings."

    Source: [`skills/02-devsecops-and-secops/cloud-security-posture-cspm-cis/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/02-devsecops-and-secops/cloud-security-posture-cspm-cis/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A cloud account or organization needs a posture audit against CIS benchmarks
- Findings must be triaged, prioritized, and tracked to remediation
- Compliance evidence for control coverage is required

**Route elsewhere when:**

- Preventive policy gates before deploy -> `enterprise-iac-governance-terragrunt`
- Identity policy authoring -> `aws-iam-zero-trust-policies`
- Active intrusion response -> `secops-incident-triage-forensics`

## 1. Automated Multi-Cloud Audit with Prowler

```bash
# Run AWS CIS Foundation Benchmark audit
prowler aws --compliance cis_2.0_aws -M json,csv,html -o /tmp/prowler-output

# Run Azure CIS Benchmark audit
prowler azure --compliance cis_2.0_azure

# Run GCP CIS Benchmark audit
prowler gcp --compliance cis_2.0_gcp
```

---

## 2. Top CIS Benchmark Critical Baselines

### AWS CIS Hardening Checklist

- [ ] Root account MFA enabled and access keys deleted.
- [ ] AWS CloudTrail enabled in all regions with log file validation and KMS encryption.
- [ ] Default VPC security groups restrict all inbound and outbound traffic.
- [ ] AWS GuardDuty and Security Hub enabled organization-wide.

### Azure CIS Hardening Checklist

- [ ] Microsoft Defender for Cloud enabled on all subscriptions.
- [ ] Storage accounts require secure transfer (`https`) and TLS 1.2+.
- [ ] Disable public blob access across all storage accounts.

### GCP CIS Hardening Checklist

- [ ] OS Login enabled across all Compute Engine instances.
- [ ] Disallow default service account assignment to VMs with full API access.
- [ ] Uniform bucket-level access enabled on all Cloud Storage buckets.

---

## 3. Finding Triage, Least Privilege & Exceptions

A raw scanner report is not a plan. Rank every finding by **exploitability × blast radius**:

| Rank | Shape of the finding | Action window |
| --- | --- | --- |
| P0 | Internet-reachable + credential/data exposure (public bucket with PII, `0.0.0.0/0` to a database) | Same day |
| P1 | Privilege escalation path (`iam:PassRole` + wildcard, admin role without MFA) | 1 week |
| P2 | Detection/logging gaps (CloudTrail off in a region, no flow logs) | 1 sprint |
| P3 | Hygiene (missing tags, unused keys, weak password policy) | Backlog |

**Least privilege as a measurable target.** Read access-analyzer/policy-simulator output and
compare granted actions against actions actually used in the last 90 days; drive the unused
share toward zero rather than chasing a "no wildcards" rule that teams will route around.

**Exception register.** Every accepted risk is a record with: finding ID, business
justification, compensating control, named owner, and an **expiry date** that reopens the
finding automatically. An exception without an expiry is a silent policy change.

---

## 4. Choosing the Scanner

| Tool | Strength | Use it for |
| --- | --- | --- |
| **Prowler** | Broadest CIS/NIST/PCI check library across AWS, Azure, GCP, Kubernetes; machine-readable output | The recurring, pipeline-run compliance audit |
| **ScoutSuite** | Multi-cloud, produces a browsable HTML attack-surface report with rich context | Point-in-time review and handing findings to non-specialists |
| Cloud-native (Security Hub, Defender for Cloud, SCC) | Continuous, no scanning infrastructure to run | Always-on drift detection and alert routing |

```bash
scout aws --report-dir ./scout-report --no-browser   # then review the HTML attack surface
scout gcp --organization-id 123456789012
```

Run one continuous native service **and** one independent scanner: native services score their
own provider's defaults generously, and an independent tool catches what the provider's checks
omit. Feed both into one findings register so the same misconfiguration is not tracked twice.

---

## 5. Anti-Patterns

| Anti-pattern | Why it fails in production |
| --- | --- |
| Reporting the raw finding count as the security metric | The number is dominated by low-severity hygiene items; it moves when the scanner updates its rule pack, not when risk changes. Track time-to-remediate for P0/P1 instead. |
| Enabling every check on day one and paging on all of them | The first week produces thousands of findings, the channel gets muted, and the programme is dead. Start with the P0 class (internet-reachable + data or credential exposure), then widen. |
| Treating a passing CIS score as "we are secure" | CIS covers configuration baselines only. It says nothing about a valid credential in an attacker's hands, a vulnerable application, or an over-broad but _technically compliant_ IAM policy. |
| Auto-remediating findings without an owner | Auto-closing a public S3 bucket that fronts a static site causes the outage the team remembers, and auto-remediation gets switched off permanently. Auto-remediate only classes that are provably safe, and notify the owner either way. |
| Silent, permanent exceptions | An exception with no expiry is a policy change nobody approved. Every accepted risk carries a justification, a compensating control, a named owner, and a date that reopens it. |
| Running only the cloud provider's native scanner | Native services grade their own provider's defaults generously. Pair one continuous native service with one independent scanner, and merge findings into a single register. |
