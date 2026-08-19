# Installation

Install this library into whichever agent runtime you use. `skills/` is the source of truth; every
runtime target (`.claude/skills/`, `.agents/skills/`, `.cursor/rules/`, `AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md`) is generated from it by `scripts/sync-all.py` and verified fresh
in CI, so all runtimes always see identical skill content.

Nothing here needs network access at runtime, and no gate needs a model or an API key.

## Requirements

| Requirement | Version | Needed for |
| --- | --- | --- |
| Python | 3.10 or newer | every quality gate (standard library only — no pip install) |
| Node.js | 24 or newer | markdown/JSON/YAML linting only (`make lint`), never to use a skill |
| `git` | any | cloning; not required if you install via the Claude Code marketplace |

Using the skills requires **only your agent**. Python and Node are for contributing.

## Claude Code and Claude Desktop

Skills are discovered automatically from `.claude/skills/<name>/SKILL.md`.

### Option A — marketplace (recommended)

Each domain is a separate plugin, so you install only what you need. A Kubernetes team should not
carry the FinOps or Azure catalogue in context.

```text
/plugin marketplace add mchittineni/cloud-platform-skills
/plugin install 04-cloud-aws@cloud-platform-skills
/plugin list
```

| Plugin | Skills |
| --- | --- |
| `01-devops-core` | 15 |
| `02-devsecops-and-secops` | 5 |
| `03-sre-slo-sla-observability` | 4 |
| `04-cloud-aws` | 4 |
| `05-cloud-azure` | 2 |
| `06-cloud-gcp` | 2 |
| `07-platform-engineering` | 4 |
| `08-finops-cloud-economics` | 1 |
| `productivity` | 1 |

After changing a skill locally, reload without restarting the session:

```text
/plugin reload
```

### Option B — clone

```bash
git clone https://github.com/mchittineni/cloud-platform-skills
cd cloud-platform-skills
```

`.claude/skills/` is already committed and current, so the clone is ready to use as a project.
Claude Code also reads `~/.claude/skills`, so for a machine-wide install copy or symlink the
generated tree there:

```bash
python3 scripts/sync-all.py --only claude    # or: bash scripts/export-to-claude.sh
ln -s "$PWD/.claude/skills" ~/.claude/skills # machine-wide; symlink tracks later edits
```

## Google Antigravity and Gemini CLI

```bash
bash scripts/gemini-install.sh                    # workspace only: ./.agents/skills
bash scripts/gemini-install.sh --global           # also installs to ~/.gemini/skills
bash scripts/gemini-install.sh --global --link    # symlink instead of copy, so edits track
```

This regenerates `.agents/skills/<name>/SKILL.md` and the `.agents/rules/` routing index
(`GEMINI.md` and `AGENTS.md`) that Gemini reads on startup. `scripts/export-to-antigravity.sh` is a
thin wrapper over `python3 scripts/sync-all.py --only agents` for the same targets.

## OpenAI Codex CLI, OpenClaw, Amp, Jules

These read the [Open AGENTS.md standard](https://agents.md). Clone the repository — `AGENTS.md` at
the root carries the engineering principles and the full routing table, and is picked up
automatically with no configuration.

```bash
git clone https://github.com/mchittineni/cloud-platform-skills
cd cloud-platform-skills
```

## Cursor

Clone the repository. `.cursor/rules/` is read automatically:

- `00-index.mdc` — `alwaysApply: true`, the routing index and engineering principles only
- `skills/<name>.mdc` — `alwaysApply: false`, fetched on request when its description matches

That split is deliberate: the index is small enough to stay resident, and individual skills load
only when relevant, which is what keeps routing accurate.

```bash
bash scripts/export-to-cursor.sh   # wrapper for: python3 scripts/sync-all.py --only cursor,copilot
```

## GitHub Copilot

Clone the repository. `.github/copilot-instructions.md` carries the principles and routing index and
is picked up automatically for the repository.

## Verify the installation

Local gates cannot prove installation works, so check it in the agent itself. Ask a question that
should trigger exactly one skill and confirm the right one loads:

| Prompt | Should load |
| --- | --- |
| "Our EKS pods are failing to get IPs" | `aws-eks-enterprise-patterns` |
| "Set an SLO for our checkout API" | `sli-slo-error-budget-design` |
| "A leaked access key was already used" | `secops-incident-triage-forensics` |

If the wrong skill loads, that is a routing defect worth an issue — the offline routing eval
(`python3 scripts/run-evals.py`) is a proxy for this behaviour, not a substitute for it.

## Using the library correctly

Read the index, load **one** skill whose triggers match, read its `## When to Use This Skill` block
first, and follow the "Route elsewhere" pointers. **Never bulk-load the library.** These skills are
written for progressive disclosure and lose accuracy when concatenated into always-on context —
depth beyond a skill body lives in its `references/` and `scripts/`, loaded on demand.

## Contributing setup

Only needed if you are changing skills. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full pipeline.

```bash
make check     # every quality gate — stdlib Python only, no install step
make lint      # markdownlint + prettier + ruff (installs its own pinned toolchain)
make hooks     # install the same gates as pre-commit hooks
```

`make lint` installs Node tools from `package.json` via `npm ci` and `ruff` into a repo-local
`.venv-lint`, both at pinned versions. Nothing is installed into your system Python.

## Uninstall

| Runtime | Remove |
| --- | --- |
| Claude Code (marketplace) | `/plugin uninstall <domain>@cloud-platform-skills` |
| Claude Code (clone) | remove the `~/.claude/skills` symlink, then delete the clone |
| Gemini / Antigravity | delete `~/.gemini/skills/` (and the clone for `.agents/`) |
| Cursor | delete `.cursor/rules/00-index.mdc` and `.cursor/rules/skills/` |
| Codex / Copilot | delete the cloned repository |
