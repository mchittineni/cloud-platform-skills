# Skill Authoring Standard

> Normative content standard for every `SKILL.md` in this repository. The process around it lives in
> [SKILL_PIPELINE.md](SKILL_PIPELINE.md); the agent-facing version of this standard is
> [`skills/productivity/write-a-skill/SKILL.md`](skills/productivity/write-a-skill/SKILL.md).
>
> Rules marked **[gated]** are machine-enforced — a violation fails a gate, not a review comment.

---

## 1. The three laws

1. **The description is the product.** It is the only text an agent reads when deciding whether to
   load the skill. A perfect body behind a vague description is dead weight; nothing routes to it.
2. **Progressive disclosure is not a style preference.** A skill is loaded into a finite context
   alongside the user's actual problem. Depth belongs in `references/`, loaded on demand.
3. **A skill is an instruction someone's agent will execute with real credentials.** Write it the
   way you would write a change you are about to apply to production yourself.

---

## 2. Frontmatter contract

```yaml
---
name: aws-eks-enterprise-patterns
description: Enterprise AWS EKS architecture: VPC CNI prefix delegation and IP planning, Karpenter NodePool/EC2NodeClass autoscaling, IRSA and EKS Pod Identity, add-on lifecycle, and upgrade strategy. Use when designing, scaling, hardening, or upgrading an EKS cluster, or fixing pod IP exhaustion and node-scaling problems.
level: senior
tags: [aws, eks, karpenter, irsa, kubernetes, cloud]
compatible_runtimes: [antigravity, claude, codex, copilot, cursor, gemini]
---
```

| Field | Rule |
| --- | --- |
| `name` | kebab-case, ≤ 64 chars, **must equal the directory name** — every runtime addresses a skill by directory **[gated]** |
| `description` | 120–700 characters, third person, single line **[gated]** |
| `level` | one of `junior`, `mid`, `senior`, `staff`, `principal`, `all` **[gated]** |
| `tags` | inline list, 3–8 entries, kebab-case **[gated]** |
| `compatible_runtimes` | inline list from `antigravity`, `claude`, `codex`, `copilot`, `cursor`, `gemini` **[gated]** |

### Writing the description

A description is a **routing decision**, structured as _capability, then triggers_:

```text
<what it covers, naming the concrete tools/APIs/patterns>. Use when <symptom 1>, when <symptom 2>,
or when <symptom 3>.
```

Rules:

- **Name the real tooling.** "Karpenter NodePool/EC2NodeClass, IRSA, VPC CNI prefix delegation"
  routes; "Kubernetes best practices" does not.
- **Write triggers as symptoms, in the user's words.** Users type _"df says there is space but
  writes fail"_, not _"filesystem inode management"_. Symptom vocabulary is what actually wins the
  routing match — this library moved 41.6% → 100% on that change alone.
- **Third person. No `You …`** **[gated]**
- **No seniority prefix.** "Mid-level Terraform …" wastes routing budget and duplicates `level`
  **[gated]**
- **Never advertise what the body does not cover** **[gated: compliance point 3]**. If the
  description says "Locust", the body teaches Locust — or the word comes out.

<details>
<summary>Before and after</summary>

```text
BAD   Mid-level CI/CD pipeline automation patterns, matrix testing, caching, security gating.
      → leaks seniority, no triggers, no symptom vocabulary, nothing to route on

GOOD  CI/CD pipeline architecture for GitHub Actions and GitLab CI: matrix testing, dependency
      caching, OIDC keyless cloud authentication, security gating, artifact provenance. Use when a
      pipeline is slow because every job reinstalls dependencies, when long-lived AWS access keys
      stored as CI secrets must be removed, or when building and gating a build-test-deploy workflow.
```

</details>

---

## 3. Body structure

### 3.1 Required opening **[gated]**

Exactly one H1, immediately followed by the routing block:

```markdown
# Enterprise AWS EKS Architecture & Karpenter Node Autoscaling

## When to Use This Skill

**Triggers — load this skill when:**
- An EKS cluster needs node autoscaling, IP planning, or add-on decisions
- Pods need AWS API access via IRSA or Pod Identity instead of node roles
- Cluster or node-group upgrades must be planned safely

**Route elsewhere when:**
- Account-level guardrails and SCPs -> `aws-iam-zero-trust-policies`
- Workload packaging -> `helm-kubernetes-deployment`
- Node cost optimization -> `finops-framework-inform-optimize-operate`
```

**"Route elsewhere" is the half that is usually missing and matters most.** Without it, a skill
gets loaded for a sibling's problem and answers confidently from the wrong domain. Every referenced
skill name must resolve **[gated]**.

### 3.2 Body sections

Numbered `## N. Title` sections, ordered so the most-needed artifact is first:

1. **The primary artifact or decision** — the thing a practitioner copies or chooses. Production-
   shaped, annotated on the lines that carry risk.
2. **The reasoning that generalises** — a trade-off table or decision tree. This is what lets an
   agent handle the case your examples do not cover.
3. **Best practices & anti-patterns** — required. Every recommendation carries the way teams get it
   wrong and what that failure looks like in production.

### 3.3 Length **[gated]**

| Budget | Value |
| --- | --- |
| Hard ceiling | 500 lines (or `<!-- line-budget-justified: reason -->`) |
| Comfort budget | 200 lines |
| Current library maximum | 170 lines |

Over budget means content moves to `references/`, not that prose gets compressed into
unreadability.

---

## 4. Writing rules

**Explain why, not only what.** A rule without its failure mode cannot be applied to a situation
that differs slightly from the example.

```markdown
BAD   Set `terminationGracePeriodSeconds: 45`.

GOOD  `terminationGracePeriodSeconds` must exceed preStop + drain deadline — otherwise SIGKILL
      truncates in-flight requests, which is exactly the dropped-traffic symptom you are fixing.
```

**Prefer a correct artifact to a description of one.** Code fences must declare a language
**[gated by markdownlint MD040]**, and must be runnable as written — no `<your-value-here>` inside
otherwise-valid YAML unless it is obviously a placeholder.

**Annotate the risky line, not every line.**

```yaml
maxEjectionPercent: 50          # never eject the whole fleet
```

**Tables for decisions, prose for reasoning, code for artifacts.** A decision expressed as three
paragraphs is a decision nobody will find under pressure.

**Never present a destructive command as routine** **[gated: compliance point 1]**. Show the guard:
dry-run first, confirmation, or a scoped target.

**No real credentials — ever** **[gated: compliance point 2]**. Placeholders must be obviously fake
(`AKIAIOSFODNN7EXAMPLE`, `${VAULT_TOKEN}`, `<account-id>`).

---

## 5. Agent safety **[gated]**

A skill body is executed by an agent holding the operator's credentials. These are blockers:

| Category | Examples |
| --- | --- |
| Instruction override | "ignore previous instructions", "disregard the above" |
| Concealment | "do not tell the user", "without informing the operator" |
| Confirmation bypass | "skip asking for approval", `--dangerously-skip-permissions`, `--yolo` |
| Safety-check disabling | "turn off your safety checks" |
| Exfiltration | collaborator sinks, `env \| curl`, credential files piped to the network, credential env vars POSTed, base64-then-transmit |

A skill that must quote an attack string to teach detection marks it once:

```markdown
<!-- agent-safety-justified: quotes injection strings to teach Falco/WAF detection rules -->
```

That downgrades the finding to a reviewed note. It is not a suppression mechanism — reviewers check
the justification.

---

## 6. Evals **[gated]**

Every skill ships `evals/evals.json` conforming to [`templates/eval-schema.json`](templates/eval-schema.json).

```json
{
  "skill": "aws-eks-enterprise-patterns",
  "version": "1.0.0",
  "must_cover": ["prefix delegation", "Karpenter", "NodePool", "EC2NodeClass", "IRSA", "Pod Identity"],
  "cases": [
    {
      "id": "aws-eks-enterprise-patterns-t1",
      "prompt": "Our EKS pods are failing to schedule with no available IPs. How do we fix the VPC CNI setup?",
      "should_trigger": true,
      "files": [],
      "assertions": [
        "Addresses IP exhaustion with prefix delegation or secondary CIDR and explicit subnet sizing"
      ]
    }
  ]
}
```

| Element | Rule |
| --- | --- |
| should-trigger cases | ≥ 3, phrased as a real user utterance — not a topic label |
| should-not-trigger cases | ≥ 2, plausible near-misses that belong to a **named sibling** |
| `assertions` | behavioural statements about a correct answer; must discriminate against a no-skill baseline |
| `must_cover` | literal technical anchors (API fields, tool names, named patterns) the body must contain |

**Choosing `must_cover` anchors.** Pick the terms that make the answer _correct_, not the terms that
make it _sound_ correct: `MessageGroupId` and `redrive`, not "reliability" and "best practices".
Anchors are substring-matched against the body, so a missing anchor is an unambiguous content gap.

> Anchors are matched as literal substrings. Do not hard-wrap a line through the middle of one —
> this is why `MD013` is disabled in `.markdownlint-cli2.jsonc`.

---

## 7. Bundled assets

| Directory | Contents | Rule |
| --- | --- | --- |
| `references/` | Long-form depth: full control mappings, provider matrices, extended runbooks | Linked from the body with one line on **when to open it** |
| `scripts/` | Python CLI tools | **Stdlib only [gated]**; `--help` states the blast radius; destructive operations default to `--dry-run`; logs to stderr, data to stdout; exit codes 0/1/2 |
| `assets/` | Templates, fixtures, expected output | Referenced from eval `files` where a case depends on them |
| `evals/` | `evals.json` | See §6 |

Every referenced path must resolve **[gated: compliance point 6]**.

---

## 8. Review checklist

Copy into the PR:

```text
[ ] name == directory name
[ ] description: third person, 120-700 chars, names real tooling, symptom-phrased "Use when" triggers
[ ] description promises nothing the body does not cover
[ ] exactly one H1, followed by Triggers + Route elsewhere
[ ] every "Route elsewhere" target resolves to a real skill
[ ] body explains WHY; every recommendation carries its anti-pattern
[ ] code fences declare a language and are runnable as written
[ ] no destructive command without a guard; no real credentials
[ ] no agent-hijacking or exfiltration content
[ ] < 500 lines (target < 200); depth in references/
[ ] evals: 3 positive + 2 negative + assertions + must_cover anchors
[ ] bundled scripts stdlib-only, dry-run by default
[ ] make check passes; residuals justified in writing
```

## 9. The gates that enforce this

```bash
make check
```

| Rule area | Enforced by |
| --- | --- |
| Frontmatter, naming, structure, cross-references | `scripts/validate-skills.py` |
| Frontmatter is loadable by a strict YAML parser | `scripts/validate-skills.py` (plain-scalar check, plus a PyYAML cross-check when installed) |
| Routing quality, content coverage | `scripts/run-evals.py --min-pass-rate 95` |
| Agent safety, secrets, description accuracy, assets | `scripts/compliance-check.py` |
| Index tables agree with the frontmatter they describe | `scripts/validate-skills.py --check-sync` |
| Markdown structure, JSON/YAML formatting, Python lint | `make lint` (markdownlint-cli2 + prettier + ruff) — **blocking in CI** |

A rule that is not gated is a rule that erodes. If you add a rule to this document, add the check —
or say explicitly that it is advisory.

**Tool versions are pinned in exactly one place each**, and CI runs the same entrypoint you do
(`make lint`), so a locally green run means something: node tools in `package.json`, `ruff` as
`RUFF_VERSION` in the `Makefile`, the docs toolchain in `requirements-dev.txt`. Check W13 in
`scripts/audit-workflows.py` fails any workflow that hardcodes a second copy of one of those
versions.
