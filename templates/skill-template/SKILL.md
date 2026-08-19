---
name: skill-name-in-kebab-case
description: "What this skill covers, naming the concrete tools, APIs and named patterns it actually teaches. Use when `<the symptoms and requests a real user would type>`, when `<second trigger>`, or when `<third trigger>`. Third person, 120-700 characters, no seniority prefix."
level: junior | mid | senior | staff | principal | all
tags: [three-to-eight, kebab-case, tags, domain]
compatible_runtimes: [antigravity, claude, codex, copilot, cursor, gemini]
---

<!-- Keep `description` DOUBLE-QUOTED. A description almost always contains ': ' (as in
     "Enterprise EKS: VPC CNI ..."), and an unquoted YAML plain scalar containing ': ' parses as a
     mapping, not a string — a strict parser then fails to load the skill at all while a lenient
     one silently truncates it. `validate-skills.py` gates this; `sync-all.py` re-quotes generated
     frontmatter with `yaml_quote()`. -->

# Human-Readable Skill Title

## When to Use This Skill

**Triggers — load this skill when:**

- `<A concrete situation, in the user's words, not a topic label>`
- `<A second situation, ideally a symptom rather than a subject>`
- `<A third situation>`

**Route elsewhere when:**

- `<Adjacent concern>` -> `sibling-skill-name`
- `<Adjacent concern>` -> `other-sibling-skill-name`

## 1. `<The primary artifact or decision>`

Lead with the thing a practitioner needs to copy or decide. Prefer a working, production-shaped
artifact over prose; annotate the lines that carry the risk.

```yaml
# runnable, correct, and safe to paste
```

## 2. `<The reasoning that generalises>`

Explain WHY, not just WHAT — a table of trade-offs, a decision tree, or the failure mode each
setting prevents. This is what lets the agent handle a case the examples do not cover.

## 3. Best Practices & Anti-Patterns

| Do | Don't |
| --- | --- |
| `<practice>` | `<the specific way teams get this wrong>` |

### Anti-patterns that reliably cause incidents

- `<what breaks, and why it breaks>`

<!-- Keep this file under 500 lines (ideally under 200). Push depth into: -->
<!--   references/  expert knowledge loaded on demand -->
<!--   scripts/     stdlib-only Python CLI tools -->
<!--   assets/      templates, sample data, expected output -->
<!--   evals/       evals.json (see templates/eval-schema.json) -->
