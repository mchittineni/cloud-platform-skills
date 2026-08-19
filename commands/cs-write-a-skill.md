---
name: cs-write-a-skill
description: Author a new skill in this repository through the full production pipeline — intake questions, scaffold from templates/skill-template, then run every gate until it ships at POWERFUL tier.
---

# Slash Command: /cs:write-a-skill

Interactively creates a new agent skill adhering to the Matt Pocock 3-Phase Workflow and progressive disclosure standards.

## Execution Workflow

1. **Forcing Interrogation Questions**:
   - **Q1**: What is the kebab-case name and domain of this skill?
   - **Q2**: Under what exact trigger conditions should the agent load this skill? ("Use when...")
   - **Q3**: What are the top 3 critical procedures or manifests?
   - **Q4**: What are the catastrophic failure modes / anti-patterns to avoid?
   - **Q5**: What deep reference material belongs in `references/` vs main `SKILL.md`?
   - **Q6**: Are there standalone validation scripts to bundle in `scripts/`?

2. **Scaffold Folder**:

   ```bash
   cp -R templates/skill-template "skills/<domain>/<name>"
   # scaffolds SKILL.md, evals/evals.json, scripts/, references/, assets/
   ```

   ## Usage

   ```text
   /cs:write-a-skill <skill-name-or-description>
   ```

   ## Arguments

   | Argument | Required | Meaning |
   | --- | --- | --- |
   | `<skill-name-or-description>` | yes | Kebab-case name, or a description to derive one from |

   ## Examples

   ```text
   /cs:write-a-skill aws-network-firewall-patterns
   /cs:write-a-skill "a skill for debugging Kafka consumer lag"
   ```

3. **Generate & Validate**:
   - Write `SKILL.md` with YAML frontmatter.
   - Run:

     ```bash
     python3 skills/productivity/write-a-skill/scripts/skill_review_checklist_runner.py skills/<domain>/<name>/SKILL.md
     ```

## Gates before the PR

```bash
make check          # validate + evals + compliance + workflows + sync + docs + compile
make lint           # markdownlint + prettier + ruff — blocking in CI, so run it too
```

A skill ships only at POWERFUL tier (compliance >= 85, eval pass rate >= 95% — the repository gate
is 95, above the 85 tier floor). Anything lower goes back to iteration — maximum 5 iterations, then
escalate rather than lower the bar.

If a skill is added, changed, or renamed, the `README.md` index row must be updated to match its
frontmatter verbatim; `validate-skills.py --check-sync` fails on drift.
