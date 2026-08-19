# Skill Production Pipeline

> Authoritative process document. Applies to every new skill, every skill improvement, and every
> deployment in this repository. `CONTRIBUTING.md` is the short contributor onboarding; this file
> is the normative pipeline, and `SKILL-AUTHORING-STANDARD.md` is the normative content standard.

```text
Intent → Research → Draft → Eval → Iterate → Compliance → Package → Deploy → Verify → Rollback-Ready
```

**Only POWERFUL ships.** Everything else goes back to iteration.

---

## Dependencies

| Tool | Required | Fallback when unavailable |
| --- | --- | --- |
| Python 3.10+ | Yes — every gate | None; gates are stdlib-only by design |
| Claude Code 2.1+ (or any agent runtime) | Yes — real-world verification | None |
| Tessl CLI | No | `scripts/compliance-check.py` implements the 8-point inspection deterministically |
| Node 18+ (`markdownlint-cli2`, `prettier`) | No | Markdown and JSON lint are advisory, not gates |
| ClawHub CLI | No | Skip OpenClaw publish; document it as unverified |

Every blocking gate runs offline, needs no model, and installs nothing.

## Iteration limits

- **Maximum 5 iterations** per skill before escalation.
- If a gate cannot pass without gaming it, **stop**. Record the residual with written justification
  (see [Documented residuals](#documented-residuals)) and escalate rather than lowering the bar.
- Overfitting a description to win one eval prompt is a pipeline failure, not a pass.

---

## Phase 1 — Intent & research

State, in the issue or PR description:

1. **What the skill enables** — the decision or artifact a practitioner walks away with.
2. **When it must trigger** — three realistic requests, in the words a user would actually type.
   These become the should-trigger eval cases verbatim.
3. **Why an existing skill cannot own it** — name the closest sibling and the boundary. A new skill
   that overlaps an existing one degrades routing for _both_; overlap is the most common reason to
   reject a proposal.
4. **The expert depth it carries** — the artifacts, trade-off tables, and anti-patterns that make it
   POWERFUL rather than a generic summary of vendor documentation.

## Phase 2 — Draft

```bash
cp -R templates/skill-template "skills/<domain>/<skill-name>"
```

```text
skills/<domain>/<skill-name>/
├── SKILL.md            # < 500 lines (target < 200); YAML frontmatter required
├── scripts/            # stdlib-only Python CLI tools
├── references/         # expert knowledge, loaded on demand
├── assets/             # templates, sample data, expected output
└── evals/evals.json    # test cases + must_cover anchors (templates/eval-schema.json)
```

Content rules are normative and live in **[SKILL-AUTHORING-STANDARD.md](SKILL-AUTHORING-STANDARD.md)**.

## Phase 3 — Eval

Author 3 should-trigger and 2 should-not-trigger cases plus `must_cover` anchors, then:

```bash
python3 scripts/run-evals.py --skill <name> --verbose
```

Two deterministic gates run, with no model and no network:

**1. Routing.** Every skill's `name + title + tags + description` is indexed as a routing document.
Each prompt is scored tf-idf against all 38 skills. A should-trigger case passes only when its own
skill ranks #1; a should-not-trigger case passes only when it does not. This reproduces what an
agent does when choosing a skill — if a description cannot win its own prompts, no runtime will
route to it.

**2. Content coverage.** Every `must_cover` anchor must appear in the body. A miss means the skill
cannot satisfy its own assertions no matter how a grader phrases them.

**Quality gate: pass rate ≥ 95%.**

LLM-graded with-skill vs baseline benchmarking (pass rate ≥ 85% with-skill, delta ≥ +30% on key
assertions, variance < 20%) requires a model runner. The offline gate is the mandatory pre-flight
that must pass **before** spending those tokens — not a substitute for them.

### Documented residuals

A case may fail for a defensible reason — typically a genuine near-tie with a sibling skill that
shares vocabulary. Add a `known_residual` string to that case explaining why. The case is then
reported on every run but does not fail the gate.

This is a reviewable admission, not an escape hatch. It is always better than keyword-stuffing a
description, and always worse than a real fix. **Reviewers must reject a residual that hides a weak
description.**

## Phase 4 — Iterate

Read what the evals show, and fix the right layer:

| Symptom | Fix |
| --- | --- |
| Routing miss (a sibling wins the prompt) | The **description** — add the symptom vocabulary users actually type |
| Routing false positive (this skill wins a sibling's prompt) | The **description** — sharpen the boundary; add the sibling to _Route elsewhere_ |
| Coverage miss (`must_cover` anchor absent) | The **body** — write the missing content |
| Compliance point 3 (description advertises what the body lacks) | The **body**, not the description — cover it, or the promise was false |

Generalise from feedback. Never add a term to a description solely to win one prompt.

## Phase 5 — Description optimisation

Re-run the routing gate after every description change; it is the offline equivalent of a trigger
eval sweep and is cheap enough for every commit. Track the aggregate — this library went from
41.6% to 100% through this loop alone.

## Phase 6 — Compliance (mandatory)

```bash
python3 scripts/compliance-check.py --verbose
```

Deterministic 8-point inspection, **minimum score 85 (POWERFUL)**:

| # | Check | Severity of a hit |
| --- | --- | --- |
| 1 | Malware, exploit code, destructive commands as routine, **or agent-directed harm** | blocker |
| 2 | Hardcoded secrets or credentials | blocker |
| 3 | Description accuracy — the body covers every tool the description advertises | major |
| 4 | Bundled scripts are stdlib-only | blocker |
| 5 | YAML frontmatter valid; `name` matches directory | blocker |
| 6 | Every bundled reference and relative link resolves | major |
| 7 | `SKILL.md` under 500 lines, or carries `<!-- line-budget-justified: … -->` | major |
| 8 | Evals present with ≥ 2 should-trigger cases, negative cases, assertions, `must_cover` | blocker |

**Point 1 is the one unique to skill libraries.** A skill is an instruction an agent executes with
the operator's credentials, so an injected directive outranks any dependency CVE. The gate detects
prompt-injection patterns (overriding prior instructions, concealing actions from the operator,
bypassing confirmation, disabling safety checks, permission-bypass flags) and exfiltration paths
(collaborator sinks, `env | curl`, credential files piped to the network, credential env vars
POSTed, base64-then-transmit). A skill that must quote an attack string to teach detection marks it
`<!-- agent-safety-justified: reason -->`, which downgrades the hit to a reviewed note.

Where Tessl is available, also run `tessl skill review <skill-path>` and require ≥ 85%.

If the change touches `.github/`:

```bash
python3 scripts/audit-workflows.py
```

CI is the highest-privilege automation in the repository. W01–W13 enforce least-privilege
`permissions`, per-job `timeout-minutes`, SHA-pinned actions, no untrusted-trigger checkout of fork
code, no `${{ github.event.* }}` interpolation inside `run:`, `concurrency` groups,
`persist-credentials: false`, artifact retention, the **expiry, ownership and staleness** of pin
exceptions in `.github/actions-allowlist.txt`, and — W13 — that no workflow hardcodes a tool version
that already has a canonical pin elsewhere.

**One pin per tool.** A version copied into a `run:` block drifts from the real pin, and CI then
lints with a different version than a developer does, which makes "lint is clean" meaningless.
Node lint tools are pinned in `package.json` and invoked via `npm ci` + `npm run`; `ruff` is pinned
by `RUFF_VERSION` in the `Makefile` and invoked via `make lint-py`; the docs toolchain is pinned in
`requirements-dev.txt`. CI runs `make lint`, so there is no second copy to keep in step.

## Phase 7 — Package

```bash
python3 scripts/sync-all.py            # regenerate every runtime target
python3 scripts/sync-all.py --check    # CI: fail if anything is stale
```

| Target | Path | Consumed by |
| --- | --- | --- |
| Claude Code skills | `.claude/skills/<name>/` | Claude Code, Claude Desktop |
| Agent skills | `.agents/skills/<name>/` | Antigravity, Gemini CLI, agentic IDEs |
| Cursor rules | `.cursor/rules/00-index.mdc` + `.cursor/rules/skills/*.mdc` | Cursor |
| Copilot instructions | `.github/copilot-instructions.md` | GitHub Copilot |
| AGENTS.md | `AGENTS.md`, `.agents/rules/AGENTS.md` | Codex, OpenClaw, Amp, Jules |
| Claude entrypoint | `CLAUDE.md` | Claude Code |
| Plugin manifests | `skills/<domain>/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude Code marketplace |
| Documentation site | `docs/`, `mkdocs.yml` (via `scripts/generate-docs.py`) | GitHub Pages |

**Generated context files carry an index — never full skill bodies.** Injecting the library into
always-on context defeats progressive disclosure and is the most common way a skill library
degrades the agent it was meant to help. `plugin.json` carries only the strict field set: `name`,
`description`, `version`, `author`, `homepage`, `repository`, `license`, `skills`.

## Phase 8 — Deploy

Feature branch → PR to `dev` → merge → PR to `main`. Conventional commits:
`feat(04-cloud-aws): add aws-network-firewall skill`.

Version bumps are mechanical — never hand-edit a manifest:

```bash
python3 scripts/check-release.py --bump 1.0.1     # every domain plugin.json
# update VERSION in scripts/sync-all.py to match
python3 scripts/sync-all.py
python3 scripts/check-release.py --version 1.0.1  # tag == manifests == marketplace == CHANGELOG
```

Tagging `v1.0.1` triggers `.github/workflows/release.yml`: re-runs every gate, uploads a 90-day
release-evidence artifact (benchmark, compliance, workflow audit, and a skill manifest with
per-skill sha256), and publishes the release from the CHANGELOG section.

| Change | Bump |
| --- | --- |
| Skill improvement (description tuning, content, gate fixes) | patch |
| New skills, scripts, agents, commands | minor |
| Restructure, removed skills, changed frontmatter contract | major |

## Phase 9 — Real-world verification (never skip)

Local gates cannot prove installation works. Verify by hand and record the result in `CHANGELOG.md`
under `### Verified`:

- **Claude Code** — `/plugin marketplace add`, `/plugin install <domain>`, `/plugin list`, reload
  without errors; then 3 should-trigger and 2 should-not prompts behave correctly.
- **Gemini CLI / Antigravity** — `bash scripts/gemini-install.sh --global`, then activate a skill.
- **Codex CLI / OpenClaw** — load `AGENTS.md`, run a test prompt, confirm the routing table is used.
- **Cursor** — confirm `00-index.mdc` applies and a per-skill rule is fetched on request only.

Every bug found is fixed immediately — no "known issues" parking. Then re-run the full gate suite
**and** the install check.

Anything that could not be verified goes in `CHANGELOG.md` under `### Not verified`, explicitly.
Silence about an unverified step reads as a passed step.

## Rollback

1. `git revert <commit>` on `dev`, fast-merge to `main`.
2. Consumers re-install from `main`; the marketplace resolves automatically.
3. `clawhub unpublish <skill>@<broken-version>` if it was published there.
4. Add a `### Reverted` section to `CHANGELOG.md`.
5. Record the post-mortem in the affected skill's `evals/` — a regression that shipped is a missing
   eval case, so add it.

---

## Quality tiers

| Tier | Score | Meaning |
| --- | --- | --- |
| **POWERFUL** | ≥ 85 | Expert-level, evals pass, real utility — ships |
| SOLID | 70–84 | Useful but shallow — back to iteration |
| GENERIC | 55–69 | Too general, needs domain depth |
| WEAK | < 55 | Reject or rewrite |

## The gate suite

```bash
make check     # everything below, in order
```

| Gate | Command | Blocks merge on |
| --- | --- | --- |
| Structure | `validate-skills.py --check-sync --strict` | Any failure or warning |
| Evals | `run-evals.py --min-pass-rate 95` | Pass rate < 95% |
| Compliance | `compliance-check.py` | Score < 85 or any blocker |
| CI security | `audit-workflows.py` | Any blocker or major |
| Packaging | `sync-all.py --check` | Any stale generated target |
| Documentation | `generate-docs.py --check` | Any stale doc |
| Release | `check-release.py --version X.Y.Z` | Version disagreement |

`make hooks` installs these as pre-commit hooks so failures surface before the push.

---

## Per-skill checklist

### Required — blocks merge

```text
[ ] SKILL.md drafted (< 500 lines, valid frontmatter, trigger-bearing description)
[ ] Routing block present: Triggers + Route elsewhere
[ ] evals/evals.json: 3 should-trigger + 2 should-not-trigger + assertions + must_cover
[ ] Bundled scripts stdlib-only, destructive operations default to dry-run
[ ] Compliance ≥ 85 (POWERFUL), zero blockers
[ ] Eval pass rate ≥ 95%, every residual justified in writing
[ ] Generated targets regenerated, not hand-edited
[ ] CHANGELOG.md updated, including a "Not verified" entry for anything unproven
[ ] PR opened against dev with a conventional commit title
```

### Recommended

```text
[ ] references/ for depth beyond the body
[ ] scripts/ for anything the reader would otherwise do by hand
[ ] assets/ sample data and expected output
[ ] agents/cs-<role>.md and commands/<action>.md entry points
[ ] LLM-graded benchmark vs baseline (pass ≥ 85%, delta ≥ +30%)
[ ] Cross-platform load check on at least one non-Claude runtime
```
