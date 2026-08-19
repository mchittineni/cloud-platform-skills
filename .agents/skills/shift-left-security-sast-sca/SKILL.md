---
name: shift-left-security-sast-sca
description: "Shift-left security automation: Semgrep SAST, Trivy and Snyk dependency and image scanning, Gitleaks repository scans for committed credentials, and SBOM generation in CycloneDX or SPDX format. Use when adding code, dependency or image scanning to a CI pipeline, when a scanner reports hundreds of findings that developers now ignore and gates need tuning for false positives, or when a customer or auditor asks for an SBOM produced by the build."
level: mid
tags: [devsecops, sast, sca, sbom, semgrep, trivy, security]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Shift-Left Security: SAST, SCA, and SBOM Pipelines

## When to Use This Skill

**Triggers — load this skill when:**

- A pipeline needs SAST, SCA, secret, and image scanning wired in with clear gates
- Scanner noise or blocking thresholds need tuning to stay credible
- An SBOM is required for compliance or a customer

**Route elsewhere when:**

- Runtime container detection -> `container-runtime-security-falco`
- Cloud misconfiguration posture -> `cloud-security-posture-cspm-cis`
- Handling a confirmed live compromise -> `secops-incident-triage-forensics`
- Signing the artifact or attesting the SBOM to it -> `supply-chain-security-slsa-sigstore`

## 1. Automated Security Scanning Pipeline

```yaml
name: DevSecOps Gate

on: [push, pull_request]

jobs:
  sast-and-secrets:
    name: Semgrep SAST & Gitleaks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
        
      # Secrets Detection
      - name: Gitleaks Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # Static Analysis (SAST)
      - name: Semgrep SAST Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten

  sca-and-sbom:
    name: Trivy SCA & SBOM Generation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate CycloneDX SBOM
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'cyclonedx'
          output: 'sbom.cdx.json'
      
      - name: Scan Filesystem for CVEs
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          ignore-unfixed: true
```

---

## 2. DevSecOps Quality Gates

- **Zero Known Criticals Policy**: Fail builds if unmitigated `CRITICAL` CVEs exist with an available fix.
- **Pre-commit Secrets Prevention**: Install `gitleaks` or `trufflehog` pre-commit hooks on developer workstations to block credential commits locally.
- **SBOM Provenance**: Publish signed CycloneDX or SPDX Software Bill of Materials with every release container.

---

## 3. False-Positive Management

Developer trust is the scarce resource. A gate that blocks on a false positive is routed around
within a quarter, and then nothing is scanned at all. Budget for false positive triage as a
standing cost of the gate, not an exception.

**Adopt with a baseline, not a wall.** On day one, snapshot existing findings as accepted debt
and block only on _newly introduced_ issues:

```bash
semgrep scan --config auto --baseline-commit "$(git merge-base origin/main HEAD)" --error
trivy fs --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 .
```

**Gate on what is actionable:**

- `--ignore-unfixed`: a CVE with no released patch cannot be actioned by the PR author.
- Reachability/severity filters: block on HIGH+ in production dependencies; report the rest.
- Secrets are the exception — any verified live credential blocks unconditionally.

**Suppressions are code reviewed like code**, and never anonymous:

```python
# nosemgrep: python.lang.security.audit.subprocess-shell
# Justified: argv is a fixed literal list; reviewed by @sec-team 2026-03-07; expires 2026-09-07
```

Track two numbers per repo: the median age of open HIGH findings, and the ratio of suppressed
to fixed. A rising suppression ratio is the early signal that the gate has stopped working.

---

## 4. Snyk in the Same Gate

```yaml
- name: Snyk dependency + license gate
  run: |
    npx snyk test --severity-threshold=high --fail-on=upgradable       --policy-path=.snyk --sarif-file-output=snyk.sarif
    npx snyk monitor --project-name="$GITHUB_REPOSITORY"   # snapshot for drift alerts
  env: { SNYK_TOKEN: "${{ secrets.SNYK_TOKEN }}" }
- uses: github/codeql-action/upload-sarif@v3
  with: { sarif_file: snyk.sarif }
```

`--fail-on=upgradable` is the setting that keeps the gate honest: it blocks only where a fix
exists, matching Trivy's `--ignore-unfixed`. Snyk adds transitive-path explanation and license
policy that Trivy does not; Trivy is faster and needs no account for image and IaC scanning.
Running both is defensible only if their findings land in one deduplicated queue — otherwise
developers see the same CVE twice and trust both less.
