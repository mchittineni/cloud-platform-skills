# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately — **do not open a public issue**.

- Preferred: [GitHub private vulnerability reporting](https://github.com/mchittineni/cloud-platform-skills/security/advisories/new)
- Alternative: open a minimal issue titled `security: request contact` with no technical detail, and a maintainer will arrange a private channel.

Include the affected file(s), the impact you believe is achievable, and reproduction steps.

| Stage | Target |
| --- | --- |
| Acknowledgement | 3 business days |
| Triage and severity decision | 7 business days |
| Fix for Critical / High | 14 days (Critical: as fast as a fix can be validated) |
| Fix for Medium / Low | Next release cycle |
| Public disclosure | After a fix ships, coordinated with the reporter |

Only the latest `main` is supported. There are no maintained release branches.

## What this repository ships — and the threat that follows from it

This repository ships **no runtime service and no application dependencies**. It ships
_instructions that AI agents execute_, plus stdlib-only Python tooling. That inverts the usual
threat model: the highest-severity vulnerability here is not a CVE in a dependency, it is a
**malicious or careless instruction in a skill body that an agent then acts on with the operator's
credentials**.

Threats we actively gate against, in severity order:

| # | Threat | Control |
| --- | --- | --- |
| 1 | **Agent hijacking** — a skill contains instructions that redirect the agent (exfiltrate environment variables, POST secrets to an external host, "ignore previous instructions", disable safety checks) | `scripts/compliance-check.py` scans every skill for agent-directed-harm and exfiltration patterns; any hit is a blocker |
| 2 | **Destructive command as routine guidance** — `rm -rf /`, raw-device `dd`, `mkfs`, `chmod 777 /`, firewall teardown, pipe-remote-script-to-shell | Pattern-scanned as blockers by `compliance-check.py`; reviewers reject unguarded destructive examples |
| 3 | **Credential leakage** — a real key, token, private key or JWT pasted into an example | `compliance-check.py` credential patterns + `gitleaks` in CI + `detect-secrets` pre-commit hook |
| 4 | **Supply-chain tampering via CI** — a compromised third-party action reading repository secrets or writing to the repo | Least-privilege `permissions:` per job, every action pinned to a full commit SHA whose tag comment is verified, `persist-credentials: false`, no `pull_request_target`, no secrets in PR-triggered jobs, owned and expiring pin exceptions (W01–W12) |
| 5 | **Toolchain substitution** — CI silently running a different lint or scan version than a reviewer ran, so a green local check hides what CI would catch (or vice versa) | One pin per tool, each with a single home; W13 fails any workflow that hardcodes a second copy, and CI invokes the same `make lint` a developer does |
| 6 | **Dependency CVEs** — limited to the docs toolchain (`requirements-dev.txt`) and the lint toolchain (`package.json`); no runtime dependencies exist | Dependabot on `github-actions`, `pip` and `npm`, dependency review on PRs |
| 7 | **Misleading guidance** — a description promising expertise the body does not contain, routing an operator to a skill that cannot help them | Description-accuracy check (compliance point 3) and the routing eval gate |

## Trust boundary for consumers

When you install these skills into an agent, you grant the agent's tool permissions to whatever
these instructions tell it to do. Treat that as running third-party code:

- **Read a skill before relying on it** for anything that touches production or credentials.
- **Run agents with least privilege.** Prefer short-lived OIDC-federated credentials with a scoped
  role over long-lived keys, so a bad instruction has a bounded blast radius and a revocation path.
- **Keep destructive operations behind human confirmation.** Every script in this repository
  defaults to dry-run for that reason; hold agent-invoked tooling to the same standard.
- **Verify what you installed.** `git log` the skill you depend on, and pin to a commit rather than
  tracking `main` if you deploy these into an automated pipeline.

## Security controls in this repository

```bash
python3 scripts/compliance-check.py --verbose   # destructive commands, credentials, agent hijacking
python3 scripts/audit-workflows.py             # CI least-privilege, pinning, injection surface
python3 scripts/validate-skills.py --strict    # structure and reference integrity
```

CI additionally runs `gitleaks` (full history on schedule), CodeQL on the Python tooling, and
dependency review on pull requests. Bundled skill scripts are enforced stdlib-only, so no skill
can pull an external package into a consumer's environment.

**On verifying pins.** A SHA pin is only as good as the review behind it. Both halves are checked:
the SHA must be 40 hex characters (W04), and the version in the trailing comment must actually
resolve to that commit. A comment naming one version while the SHA points elsewhere is worse than no
comment — it presents a reviewed pin that was never reviewed. The same applies to a pin on a retired
major version, which stops receiving fixes while still looking current.

## Out of scope

- Vulnerabilities in the third-party tools the skills _document_ (Terraform, Istio, Falco, …).
  Report those upstream; if a skill teaches an insecure pattern, that **is** in scope — report it.
- Findings from automated scanners with no demonstrated impact on this repository.
- The documentation site's dependency tree beyond what Dependabot already tracks.
