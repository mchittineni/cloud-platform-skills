# Quality Gates for Production Agent Skills

To maintain high reasoning fidelity and avoid degradation across long chat conversations, every skill in the repository must pass 6 quality gates:

## Gate 1: Description Gate

- [x] ≤ 1024 characters total length.
- [x] Written in 3rd person (no "I", "you", "we", "my").
- [x] Contains explicit scenario triggers: `"Use when [condition]..."`.

## Gate 2: The 100-150 Line Ceiling

- [x] Main `SKILL.md` is tightly focused on immediate triage and SOP execution.
- [x] Heavy architectural manuals, lengthy specifications, or raw reference data are split into `references/<topic>.md`.

## Gate 3: Executable Code & Manifests

- [x] Every YAML, HCL, bash, or python snippet is valid syntax and directly executable.
- [x] Placeholders are clearly annotated as `<variable-name>` or parameter substitutions.

## Gate 4: Explicit Anti-Patterns & Safety Directives

- [x] Every skill lists explicit failure modes, dangers, and "Don'ts" (e.g. `kill -9` avoidance, mutable `:latest` tags).

## Gate 5: Universal Portability

- [x] Valid frontmatter supported by Antigravity, Claude Code, Cursor, and Codex.

## Gate 6: Automated Schema Passing

- [x] Passes `python3 scripts/validate-skills.py`.
- [x] Passes `python3 skills/productivity/write-a-skill/scripts/skill_review_checklist_runner.py`.
