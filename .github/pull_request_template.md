<!-- markdownlint-disable-file MD041 -->
<!-- A pull-request template is a body fragment, not a document: a top-level H1 would
     render as an oversized heading in every PR. Every other rule stays enforced. -->

## What changed and why

<!-- One paragraph. If this adds or changes a skill, state the routing decision it improves:
     which user request should now reach which skill, and what it does differently. -->

## Type

- [ ] New skill
- [ ] Skill improvement (content, description, evals)
- [ ] Gate / tooling change (`scripts/`)
- [ ] CI / security / repo infrastructure
- [ ] Documentation only

## Required gates

All of these must pass locally before review. Paste the summary lines.

```text
make check     # validate-skills --check-sync --strict · run-evals --min-pass-rate 95 ·
               # compliance-check · audit-workflows · sync-all --check · generate-docs --check
make lint      # markdownlint-cli2 + prettier + ruff — blocking in CI
```

<details><summary>Gate output</summary>

```text
paste here
```

</details>

## For a new or changed skill

- [ ] `name` matches the directory name
- [ ] `description` is third person, names the concrete tools, and carries explicit `Use when …`
      triggers phrased the way a user would type them
- [ ] `## When to Use This Skill` block has **Triggers** and **Route elsewhere**
- [ ] `evals/evals.json` has ≥ 3 should-trigger + 2 should-not-trigger cases and `must_cover` anchors
- [ ] Body is under 500 lines (ideally under 200); depth pushed to `references/`
- [ ] Every recommendation carries its anti-pattern
- [ ] Bundled scripts are stdlib-only and default to dry-run for destructive operations
- [ ] Generated targets regenerated (`scripts/sync-all.py`), not hand-edited
- [ ] `README.md` index row matches the frontmatter verbatim (checked by `--check-sync`)
- [ ] `CHANGELOG.md` updated

## Agent-safety review (required for skill content)

- [ ] No instruction that would redirect an agent (exfiltration, "ignore previous instructions",
      disabling safety checks)
- [ ] No unguarded destructive command presented as routine guidance
- [ ] No real credentials, tokens, or private keys — placeholders only
- [ ] Any residual eval failure is recorded as a `known_residual` **with justification**, not
      worked around by keyword-stuffing a description

## For a tooling or CI change

- [ ] Any new action is pinned to a full commit SHA **and** the SHA was verified to resolve to the
      version in its trailing comment
- [ ] No tool version is hardcoded in a `run:` block — pins live in `package.json`, `RUFF_VERSION`,
      or `requirements-dev.txt` (checked by W13)
- [ ] `make check` and `make lint` both pass, and CI runs the same entrypoints

## Anything left undone

<!-- Be explicit. Unverified steps (marketplace install, LLM-graded evals, Tessl) belong here. -->
