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

Both must pass locally before review. Paste the summary lines — a claim that they passed is not the
same as the numbers.

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
- [ ] `description` is **double-quoted** — a description containing `": "` is a YAML mapping when
      left unquoted, and the skill silently fails to load in any runtime using a real YAML parser
- [ ] `description` is third person, names the concrete tools, and carries explicit `Use when …`
      triggers phrased the way a user would type them
- [ ] **Every trigger and every tool named in the description is actually covered by the body.**
      Compliance point 3 compares the two loosely, so check it trigger by trigger — advertising a
      capability the body lacks routes an agent to a skill that cannot help it
- [ ] `## When to Use This Skill` block has **Triggers** and **Route elsewhere**
- [ ] `evals/evals.json` has ≥ 3 should-trigger + 2 should-not-trigger cases
- [ ] **`must_cover` anchors are discriminating.** Pick the terms that make the answer correct
      (`MessageGroupId`, `mutateDigest`), not a single generic word — a one-word anchor can be
      satisfied by an incidental sentence and will certify a topic the skill does not teach
- [ ] Body is under 400 lines (200 is the comfort budget); depth pushed to `references/`
- [ ] Every recommendation carries its anti-pattern
- [ ] Bundled scripts are stdlib-only and default to dry-run for destructive operations
- [ ] Generated targets regenerated (`scripts/sync-all.py`), not hand-edited
- [ ] `README.md` index row matches the frontmatter verbatim (checked by `--check-sync`)
- [ ] `CHANGELOG.md` updated

### Routing, when a skill is added or its description changes

- [ ] **Full eval suite re-run, not just this skill.** Adding a skill changes the tf-idf weights for
      every other one, so a new skill can push a sibling's own trigger to the wrong place. Confirm
      the overall pass rate, not the new skill's
- [ ] If this overlaps an existing skill, the boundary is **stated in both descriptions** and both
      carry a `Route elsewhere` pointer at the other — divide the territory rather than competing
      for it
- [ ] Any remaining miss is fixed by improving the description or the body, never by keyword-stuffing
      to win one prompt; a defensible near-tie is recorded as a `known_residual` with written
      justification
- [ ] Five iterations maximum. Past that, escalate rather than lowering the bar

## Agent-safety review (required for skill content)

- [ ] No instruction that would redirect an agent — exfiltration, overriding earlier instructions,
      concealing activity from the operator, or disabling a safety check
- [ ] No unguarded destructive command presented as routine guidance
- [ ] No real credentials, tokens, or private keys — placeholders only
- [ ] If the skill legitimately has to name attack shapes because it **teaches detection of them**,
      it carries a `<!-- agent-safety-justified: reason -->` marker. Keep it on **one line** — the
      matcher is not `DOTALL`, so a wrapped marker fails silently and the finding stays a blocker

## For a tooling or CI change

- [ ] Any new action is pinned to a full commit SHA **and** the SHA was verified to resolve to the
      version in its trailing comment
- [ ] No tool version is hardcoded in a `run:` block — pins live in `package.json`, `RUFF_VERSION`,
      or `requirements-dev.txt` (checked by W13)
- [ ] A new gate is regression-tested by reintroducing the defect it detects, and the test is
      described here — an unexercised gate is an assumption
- [ ] `make check` and `make lint` both pass, and CI runs the same entrypoints

## Anything left undone

<!-- Be explicit. Unverified steps (marketplace install, LLM-graded evals, Tessl) belong here.
     "Known issues" parked for later are not acceptable; either fix them or say why they are
     out of scope for this change. -->
