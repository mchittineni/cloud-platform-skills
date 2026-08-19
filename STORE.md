# Marketplace listing — cloud-platform-skills

> 38 evaluated, compliance-gated engineering skills for Cloud, Platform, SRE, Security and FinOps.
> Portable across Claude Code, Antigravity/Gemini CLI, Codex, Cursor and GitHub Copilot.

## Install

### Claude Code

```text
/plugin marketplace add mchittineni/cloud-platform-skills
/plugin install 04-cloud-aws@cloud-platform-skills
/plugin list
```

Install only the domains you need — each is a separate plugin, so a Kubernetes team does not
carry the FinOps or Azure catalogue in context.

| Plugin | Skills | Covers |
| --- | --- | --- |
| `01-devops-core` | 15 | Linux, Git, Docker, CI/CD, Terraform, Helm, GitOps, progressive delivery, DR, DORA, load testing |
| `02-devsecops-and-secops` | 5 | SAST/SCA/SBOM, Vault & KMS, Falco runtime detection, CSPM/CIS, incident forensics |
| `03-sre-slo-sla-observability` | 4 | SLI/SLO/error budgets, OpenTelemetry, host monitoring, incident command |
| `04-cloud-aws` | 4 | EKS, IAM zero-trust, migration 6Rs, scalability & HA |
| `05-cloud-azure` | 2 | AKS landing zones, CAF platform architecture |
| `06-cloud-gcp` | 2 | Org hierarchy & keyless CI, GKE multi-tenancy |
| `07-platform-engineering` | 4 | Service mesh, 12-factor services, Backstage IDP, serverless/event-driven |
| `08-finops-cloud-economics` | 1 | FinOps lifecycle, allocation, commitments, unit economics |
| `productivity` | 1 | Skill authoring meta-skill |

### Other runtimes

```bash
git clone https://github.com/mchittineni/cloud-platform-skills
cd cloud-platform-skills

bash scripts/gemini-install.sh --global   # Gemini CLI / Antigravity
# Codex CLI / OpenClaw / Amp / Jules: AGENTS.md is read automatically
# Cursor: .cursor/rules/ is picked up automatically
# Copilot: .github/copilot-instructions.md is picked up automatically
```

## What makes these different

- **Evaluated, not asserted.** 190 eval cases; a skill only ships if its own description wins its
  own trigger prompts against all 37 siblings.
- **Compliance-gated.** Every skill passes an 8-point inspection covering destructive commands,
  credential leakage, description accuracy, and **agent-directed harm** — the risk that matters
  when an agent executes instructions with your credentials.
- **Progressive disclosure.** Every `SKILL.md` is under 200 lines and declares when to route
  elsewhere, so an agent loads one skill instead of a library.
- **Anti-patterns included.** Every recommendation states what fails in production and why.

## Verify before you trust

These skills instruct an agent that holds your credentials. Read `SECURITY.md`, pin to a commit
rather than tracking `main` in automated pipelines, and run agents with short-lived scoped
credentials.

## Support

- Issues: <https://github.com/mchittineni/cloud-platform-skills/issues>
- Security: private reporting per [SECURITY.md](SECURITY.md)
- Licence: MIT
