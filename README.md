# Cloud & Platform Engineering Skills (`cloud-platform-skills`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-38-blue.svg)](#skill-index)
[![Quality tier](https://img.shields.io/badge/Quality-POWERFUL%20100%2F100-brightgreen.svg)](#quality-gates)
[![Eval pass rate](https://img.shields.io/badge/Routing%20evals-100%25%20(2%20documented%20residuals)-brightgreen.svg)](#quality-gates)
[![Runtimes](https://img.shields.io/badge/Runtimes-Claude%20%7C%20Antigravity%20%7C%20Codex%20%7C%20Cursor%20%7C%20Copilot-purple.svg)](#use-it-in-your-agent)

38 production-grade, evaluated engineering skills for **Cloud, Platform, SRE, Security and
FinOps** work — portable across every major AI coding agent, and usable by humans as runbooks,
ADRs and SOPs.

Each skill is a routing decision plus an expert body: it declares the symptoms that should load
it, the sibling skill to use instead when the task is adjacent, production-shaped artifacts, and
the anti-patterns that cause incidents.

## Why this library is different

- **Every skill is evaluated, not just written.** 190 eval cases (3 should-trigger + 2
  should-not-trigger per skill) are scored by an offline harness that reproduces what an agent
  actually does when picking a skill. Routing pass rate: **100%**, with two near-ties between
  sibling security skills recorded as justified residuals in the eval files themselves rather than
  papered over by keyword-stuffing a description.
- **Every skill is compliance-gated.** A deterministic 8-point inspection covers destructive
  commands, credential leaks, description accuracy, stdlib-only scripts, frontmatter validity,
  reference resolution, line budget, and eval completeness. Average score: **100/100**, all
  38 at POWERFUL tier.
- **Progressive disclosure is enforced.** Generated context files carry an index, never full skill
  bodies. Every `SKILL.md` is under 200 lines with depth pushed into `references/`.
- **One source of truth.** `skills/` is authoritative; every runtime target is generated and
  CI-verified as fresh.

## Use it in your agent

| Runtime | How skills are discovered | Setup |
| --- | --- | --- |
| **Claude Code / Desktop** | `.claude/skills/<name>/SKILL.md`, auto-discovered | Clone the repo, or `/plugin marketplace add mchittineni/cloud-platform-skills` then `/plugin install <domain>` |
| **Google Antigravity / Gemini CLI** | `.agents/skills/`, `.agents/rules/GEMINI.md` | `bash scripts/gemini-install.sh --global` |
| **OpenAI Codex CLI** | `AGENTS.md` routing table | Clone the repo; Codex reads `AGENTS.md` automatically |
| **Cursor** | `.cursor/rules/00-index.mdc` (always applied) + `.cursor/rules/skills/*.mdc` (fetched on request) | Clone the repo |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Clone the repo |
| **OpenClaw / Amp / Jules** | `AGENTS.md` + YAML frontmatter triggers | Clone the repo |

Full per-runtime steps, verification prompts and uninstall instructions are in
[INSTALLATION.md](INSTALLATION.md). Regenerate every target after editing a skill:

```bash
python3 scripts/sync-all.py
```

**How an agent should use this library:** read the index, load **one** skill whose triggers match,
read its `## When to Use This Skill` block first, and follow the "Route elsewhere" pointers. Never
bulk-load the library — these skills are written for progressive disclosure and lose accuracy when
concatenated into always-on context.

## Skill index

### DevOps Core Progression (15)

| Skill | Level | Load when |
| --- | --- | --- |
| [`backup-and-disaster-recovery`](skills/01-devops-core/backup-and-disaster-recovery/SKILL.md) | senior | Use when designing a DR strategy, setting RPO/RTO targets, automating backups, or running a restore or failover exercise. |
| [`cicd-pipeline-design`](skills/01-devops-core/mid-level-automation/cicd-pipeline-design/SKILL.md) | mid | Use when a pipeline is slow because every job reinstalls dependencies, when long-lived AWS or cloud access keys stored as CI secrets must be removed, or when building, gating and speeding up a build-test-deploy workflow. |
| [`configuration-management-ansible`](skills/01-devops-core/configuration-management-ansible/SKILL.md) | mid | Use when applying a hardening or CIS baseline repeatably across many Ubuntu or RHEL hosts, refactoring a monolithic playbook into roles, or fixing a playbook that reports 'changed' on every run. |
| [`database-devops-lifecycle`](skills/01-devops-core/database-devops-lifecycle/SKILL.md) | senior | Use when adding, renaming or dropping a column on a large Postgres or MySQL table without downtime, running migrations from a deploy pipeline, or diagnosing read replicas lagging behind the primary and serving stale data. |
| [`devops-metrics-dora-kpis`](skills/01-devops-core/devops-metrics-dora-kpis/SKILL.md) | senior | Use when measuring delivery performance, building an engineering-metrics dashboard, or diagnosing why throughput or stability is poor. |
| [`docker-containerization-basics`](skills/01-devops-core/junior-foundation/docker-containerization-basics/SKILL.md) | junior | Use when writing or reviewing a Dockerfile, shrinking image size, fixing slow builds, or hardening containers before they reach a registry. |
| [`enterprise-iac-governance-terragrunt`](skills/01-devops-core/senior-staff-architect/enterprise-iac-governance-terragrunt/SKILL.md) | staff | Use when Terraform has been copy-pasted across many accounts or environments, or when non-compliant resources such as unencrypted or untagged S3 buckets must be blocked in CI before apply rather than found afterwards. |
| [`git-branching-merge-strategies`](skills/01-devops-core/junior-foundation/git-branching-merge-strategies/SKILL.md) | junior | Use when choosing a branching model, defining merge/rebase rules for a team, resolving conflicts, or recovering from a bad commit, push, or revert. |
| [`gitops-multi-cluster-argo-flux`](skills/01-devops-core/senior-staff-architect/gitops-multi-cluster-argo-flux/SKILL.md) | senior | Use when managing many clusters or environments declaratively, deciding how to structure repositories, branches and overlays to promote a release from staging to production, or debugging an Application stuck OutOfSync. |
| [`helm-kubernetes-deployment`](skills/01-devops-core/mid-level-automation/helm-kubernetes-deployment/SKILL.md) | mid | Use when authoring or reviewing a Helm chart, templating Kubernetes manifests, or debugging a failed or stuck Helm release. |
| [`linux-sysadmin-troubleshooting`](skills/01-devops-core/junior-foundation/linux-sysadmin-troubleshooting/SKILL.md) | junior | Use when a server or VM is degraded, crawling, or unresponsive and needs live hands-on diagnosis, when writes fail with 'No space left on device' despite free space, or when a stuck process must be traced. |
| [`performance-load-testing`](skills/01-devops-core/performance-load-testing/SKILL.md) | mid | Use when writing a k6 or Locust script, deciding whether an API can handle a peak traffic event, capacity planning before launch, or investigating why average latency looks fine while users report slowness. |
| [`scripting-and-automation`](skills/01-devops-core/scripting-and-automation/SKILL.md) | mid | Use when writing, reviewing, or hardening an operational script, cron job, or internal CLI tool. |
| [`terraform-iac-modules`](skills/01-devops-core/mid-level-automation/terraform-iac-modules/SKILL.md) | mid | Use when structuring or restructuring a Terraform repository across dev, staging and production environments, writing reusable modules, configuring a state backend, or investigating unexplained infrastructure drift. |
| [`zero-downtime-release-strategies`](skills/01-devops-core/senior-staff-architect/zero-downtime-release-strategies/SKILL.md) | senior | Use when releasing to a small percentage of traffic first while watching error rate and latency, when a bad deploy must roll back automatically without a human, or when choosing between canary, blue-green and rolling deployment. |

### DevSecOps & SecOps (9)

| Skill | Level | Load when |
| --- | --- | --- |
| [`ai-agent-security-llm-threats`](skills/02-devsecops-and-secops/ai-agent-security-llm-threats/SKILL.md) | senior | Use when an agent is given tools or credentials, when retrieved documents or repository files could carry injected instructions, or when reviewing an AI feature before it reaches production. |
| [`cloud-security-posture-cspm-cis`](skills/02-devsecops-and-secops/cloud-security-posture-cspm-cis/SKILL.md) | senior | Use when auditing an account or organization's security posture, finding unused and over-permissive permissions across hundreds of roles, preparing for a CIS or compliance review, or triaging misconfiguration findings. |
| [`container-runtime-security-falco`](skills/02-devsecops-and-secops/container-runtime-security-falco/SKILL.md) | senior | Use when alerting on attacker behaviour inside a running container such as an interactive shell being opened in production, writing or tuning a noisy Falco rule, or triaging a runtime alert. |
| [`detection-engineering-threat-hunting`](skills/02-devsecops-and-secops/detection-engineering-threat-hunting/SKILL.md) | senior | Use when security alerts are too noisy to act on, when deciding which detections to write and which telemetry to collect first, or when hunting for attacker activity nothing has alerted on. |
| [`policy-as-code-opa-kyverno`](skills/02-devsecops-and-secops/policy-as-code-opa-kyverno/SKILL.md) | senior | Use when privileged containers or pods without resource limits must be rejected at admission rather than reported, when admission policies need tests so a rule cannot silently stop matching, or when choosing between Kyverno and OPA Gatekeeper. |
| [`secops-incident-triage-forensics`](skills/02-devsecops-and-secops/secops-incident-triage-forensics/SKILL.md) | staff | Use when a host, container or cloud credential is suspected compromised, when a leaked access key found in a public repository has already been used, or when capturing evidence. |
| [`secrets-management-vault-kms`](skills/02-devsecops-and-secops/secrets-management-vault-kms/SKILL.md) | senior | Use when a database password or API key sits in a plain Kubernetes Secret or a manifest checked into Git, or when workloads need credential material injected at runtime without storing it. |
| [`shift-left-security-sast-sca`](skills/02-devsecops-and-secops/shift-left-security-sast-sca/SKILL.md) | mid | Use when adding code, dependency or image scanning to a CI pipeline, when a scanner reports hundreds of findings that developers now ignore and gates need tuning for false positives, or when a customer or auditor asks for an SBOM produced by the build. |
| [`supply-chain-security-slsa-sigstore`](skills/02-devsecops-and-secops/supply-chain-security-slsa-sigstore/SKILL.md) | senior | Use when release artifacts or container images need signing, provenance or attestation, when a customer or auditor asks which SLSA level a build meets, or when only trusted and verified images should be allowed to run in a cluster. |

### SRE, SLO/SLA & Observability (5)

| Skill | Level | Load when |
| --- | --- | --- |
| [`chaos-engineering-resilience-testing`](skills/03-sre-slo-sla-observability/chaos-engineering-resilience-testing/SKILL.md) | senior | Use when a failover or redundancy claim has never actually been tested, when planning a GameDay or resilience exercise, or when deciding whether it is safe to inject failure into production and how to bound it. |
| [`incident-management-and-postmortem`](skills/03-sre-slo-sla-observability/incident-management-and-postmortem/SKILL.md) | staff | Use when running or improving incident response, declaring severity, coordinating an active outage, or writing a post-mortem. |
| [`infrastructure-host-monitoring`](skills/03-sre-slo-sla-observability/infrastructure-host-monitoring/SKILL.md) | mid | Use when standing up monitoring or dashboards across a fleet of nodes, authoring or tuning infrastructure alert rules, or arranging to be paged before a filesystem fills rather than after it is already full. |
| [`prometheus-grafana-otel-tracing`](skills/03-sre-slo-sla-observability/prometheus-grafana-otel-tracing/SKILL.md) | senior | Use when instrumenting services so a latency spike can be followed to the exact trace and log line, building the metrics-logs-traces stack, or fixing missing telemetry and cardinality blowups. |
| [`sli-slo-error-budget-design`](skills/03-sre-slo-sla-observability/sli-slo-error-budget-design/SKILL.md) | senior | Use when defining reliability targets or an SLO target for a user-facing API or service, replacing noisy threshold alerts with burn-rate alerts, or governing releases against a spent budget. |

### AWS Cloud Architecture (4)

| Skill | Level | Load when |
| --- | --- | --- |
| [`aws-cloud-migration-strategies`](skills/04-cloud-aws/aws-cloud-migration-strategies/SKILL.md) | senior | Use when planning a datacenter exit or lease expiry, deciding whether a legacy monolith should be rehosted or refactored, or moving a large Oracle, SQL Server or Postgres database with minimal downtime. |
| [`aws-eks-enterprise-patterns`](skills/04-cloud-aws/aws-eks-enterprise-patterns/SKILL.md) | senior | Use when designing, scaling, hardening, or upgrading an EKS cluster, or fixing pod IP exhaustion and node-scaling problems. |
| [`aws-iam-zero-trust-policies`](skills/04-cloud-aws/aws-iam-zero-trust-policies/SKILL.md) | senior | Use when writing or reviewing an SCP or IAM policy, scoping down a role that has AdministratorAccess, or designing multi-account guardrails and federated access. |
| [`scalability-high-availability-patterns`](skills/04-cloud-aws/scalability-high-availability-patterns/SKILL.md) | senior | Use when a service must survive an availability zone failure, when it collapses under traffic spikes and drags downstream services with it, or when CPU is the wrong autoscaling signal. |

### Azure Cloud Architecture (2)

| Skill | Level | Load when |
| --- | --- | --- |
| [`azure-aks-enterprise-landing-zones`](skills/05-cloud-azure/azure-aks-enterprise-landing-zones/SKILL.md) | senior | Use when building or hardening AKS to an enterprise baseline, when AKS pods must authenticate to Key Vault or other Azure services without any stored secret, or when enforcing Kubernetes governance on Azure. |
| [`azure-cloud-engineering-patterns`](skills/05-cloud-azure/azure-cloud-engineering-patterns/SKILL.md) | senior | Use when designing an Azure landing zone or network topology, making Storage, SQL or other PaaS unreachable from the internet, or enforcing tagging and allowed regions across every subscription. |

### GCP Cloud Architecture (2)

| Skill | Level | Load when |
| --- | --- | --- |
| [`gcp-cloud-engineering-patterns`](skills/06-cloud-gcp/gcp-cloud-engineering-patterns/SKILL.md) | senior | Use when designing a Google Cloud resource hierarchy or network, letting GitHub Actions or another external CI deploy to GCP without a service account key, or building a data perimeter. |
| [`gcp-gke-autopilot-multi-tenant`](skills/06-cloud-gcp/gcp-gke-autopilot-multi-tenant/SKILL.md) | senior | Use when designing a multi-tenant GKE platform, isolating tenant workloads, or choosing between Autopilot and Standard. |

### Platform Engineering (4)

| Skill | Level | Load when |
| --- | --- | --- |
| [`api-gateway-service-mesh`](skills/07-platform-engineering/api-gateway-service-mesh/SKILL.md) | senior | Use when configuring ingress routing, enforcing zero-trust service-to-service traffic, or debugging mesh routing and mTLS failures. |
| [`cloud-native-microservices-patterns`](skills/07-platform-engineering/cloud-native-microservices-patterns/SKILL.md) | senior | Use when pods are killed during a deploy and drop in-flight requests, when Kubernetes restarts a container that is merely slow to start, or when refactoring a service to run correctly on Kubernetes. |
| [`internal-developer-portal-backstage`](skills/07-platform-engineering/internal-developer-portal-backstage/SKILL.md) | staff | Use when building self-service so developers can create a new production-ready service in one click, defining golden paths, onboarding services into a catalog, or measuring platform adoption. |
| [`serverless-event-driven-architecture`](skills/07-platform-engineering/serverless-event-driven-architecture/SKILL.md) | senior | Use when designing event-driven flows, choosing FIFO versus standard for per-customer ordering at high throughput, or when events are lost, duplicated or throttled. |

### FinOps & Cloud Economics (1)

| Skill | Level | Load when |
| --- | --- | --- |
| [`finops-framework-inform-optimize-operate`](skills/08-finops-cloud-economics/finops-framework-inform-optimize-operate/SKILL.md) | senior | Use when a cloud bill has jumped unexpectedly and the driver is unknown, when deciding whether to buy commitments, or when charging shared spend back to teams. |

### Productivity & Meta-Skills (1)

| Skill | Level | Load when |
| --- | --- | --- |
| [`write-a-skill`](skills/productivity/write-a-skill/SKILL.md) | staff | Use when creating, refactoring, auditing, or reviewing an AI agent skill in this repository or any skills library. |

## Quality gates

```bash
make check     # runs every gate below
make lint      # markdownlint + prettier + ruff (blocking in CI; installs its own pinned toolchain)

# or individually
python3 scripts/validate-skills.py --check-sync --strict   # structure, frontmatter, index and mirror sync
python3 scripts/run-evals.py --min-pass-rate 95            # routing + content-coverage evals
python3 scripts/compliance-check.py                        # 8-point compliance inspection
python3 scripts/audit-workflows.py                         # CI least-privilege, pinning, injection
python3 scripts/sync-all.py --check                        # generated targets are fresh
python3 scripts/generate-docs.py --check                   # documentation site is fresh
python3 scripts/check-release.py --version X.Y.Z           # release consistency
```

| Gate | Current result |
| --- | --- |
| Structure, frontmatter, mirror sync | 38 passed, 0 failed, 0 warnings |
| Compliance (8-point) | 38/38 POWERFUL, average **100.0**, 0 blockers |
| Routing + coverage evals | overall **100.0%** POWERFUL, 2 documented residuals |
| Workflow security audit | 0 blocker, 0 major, 0 minor across 4 workflows |
| Release consistency | tag, 9 plugin manifests, marketplace.json and CHANGELOG agree |
| Linters (`make lint`) | markdownlint 0 issues, prettier clean, ruff clean |

All gates are stdlib-only Python 3.10+, run offline, need no model or API key, and are enforced in CI
(`.github/workflows/skills-ci.yml`, `security.yml`, `release.yml`). Install them locally as
pre-commit hooks with `make hooks`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full production
pipeline and [CHANGELOG.md](CHANGELOG.md) for what has shipped.

Beyond content, the gates also hold the repository's own supply chain: every GitHub Action is pinned
to a commit SHA whose tag comment is verified, pin exceptions expire and are owned, and every lint
tool version has exactly one home (`package.json` for node, `RUFF_VERSION` in the `Makefile` for
ruff, `requirements-dev.txt` for the docs site) — a second copy inside a workflow fails check W13,
because a locally green lint run must mean the same thing CI means.

### Toolchain

| Tool | Version | Pinned in |
| --- | --- | --- |
| Python | 3.10+ (CI matrix: 3.10, 3.13) | `pyproject.toml`, workflow matrix |
| Node.js | 24+ | `package.json` `engines`, `NODE_VERSION` |
| `markdownlint-cli2` | 0.23.2 | `package.json` |
| `prettier` | 3.9.6 | `package.json` |
| `ruff` | 0.16.3 | `RUFF_VERSION` in the `Makefile` |
| `mkdocs-material` | 9.7.7 | `requirements-dev.txt` |

## Security

These skills are **instructions an agent executes with your credentials**, so the threat model is
not the usual dependency-CVE one. The highest-severity defect here is a malicious or careless
instruction — exfiltration, concealment from the operator, confirmation bypass, an unguarded
destructive command. `scripts/compliance-check.py` scans every skill for exactly that, and CI adds
gitleaks, CodeQL and dependency review.

Before trusting these skills in an automated pipeline: read [SECURITY.md](SECURITY.md), pin to a
commit rather than tracking `main`, and run agents with short-lived scoped credentials so a bad
instruction has a bounded blast radius.

## Repository layout

```text
cloud-platform-skills/
├── skills/<domain>/<skill-name>/     # SOURCE OF TRUTH
│   ├── SKILL.md                      # < 200 lines, frontmatter + routing block + expert body
│   ├── evals/evals.json              # 5 eval cases + must_cover anchors
│   ├── references/                   # depth loaded on demand
│   ├── scripts/                      # stdlib-only Python CLI tools
│   └── assets/                       # templates, fixtures, expected output
├── scripts/                          # validate · run-evals · compliance-check · sync-all · generate-docs
├── templates/                        # skill-template/ + eval-schema.json
├── Makefile                          # every gate and linter, with the ruff pin
├── docs/ + mkdocs.yml                # generated documentation site
├── AGENTS.md · CLAUDE.md             # generated agent entrypoints
├── .claude/skills/ · .agents/skills/ # generated runtime mirrors
├── .cursor/rules/ · .github/copilot-instructions.md
└── .claude-plugin/marketplace.json   # generated plugin packaging
```

Everything outside `skills/`, `scripts/`, `templates/` and the root markdown files is generated —
edit a skill, then run `scripts/sync-all.py`.

## Skill anatomy

1. **Frontmatter** — `name` (matching the directory), a third-person `description` with explicit
   `Use when …` triggers, `level`, `tags`, `compatible_runtimes`.
2. **When to Use This Skill** — triggers, plus "Route elsewhere" cross-links.
3. **Production artifacts** — working Terraform, Kubernetes, CI, policy and script snippets.
4. **The reasoning that generalises** — decision tables and trade-offs, not just recipes.
5. **Best practices & anti-patterns** — what not to do, and why it fails in production.

## Contributing & licence

| Document | What it covers |
| --- | --- |
| [INSTALLATION.md](INSTALLATION.md) | Per-runtime install, verification and uninstall |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute — start here |
| [SKILL_PIPELINE.md](SKILL_PIPELINE.md) | The normative 9-phase production pipeline, gates and tiers |
| [SKILL-AUTHORING-STANDARD.md](SKILL-AUTHORING-STANDARD.md) | The normative content standard for a `SKILL.md` |
| [SECURITY.md](SECURITY.md) | Threat model, reporting, and the consumer trust boundary |
| [CHANGELOG.md](CHANGELOG.md) | What shipped, and what is explicitly unverified |

New skills must pass all gates and ship at POWERFUL tier. Start from
`templates/skill-template/`. Licensed under the [MIT License](LICENSE).
