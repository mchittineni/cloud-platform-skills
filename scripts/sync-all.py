#!/usr/bin/env python3
"""
sync-all.py — regenerate every runtime target from skills/ (Phase 7: packaging).

skills/ is the single source of truth. Everything else in this repository is generated:

  .claude/skills/<name>/        Claude Code native skill discovery (progressive disclosure)
  .agents/skills/<name>/        Antigravity / Gemini CLI / agentic IDE discovery
  .cursor/rules/00-index.mdc    Cursor: one always-applied routing index
  .cursor/rules/skills/*.mdc    Cursor: per-skill rules, agent-requested (alwaysApply: false)
  .github/copilot-instructions.md   Copilot: principles + routing index
  AGENTS.md                     Open AGENTS.md standard (Codex, OpenClaw, Cursor, Amp, Jules)
  CLAUDE.md                     Claude Code project entrypoint
  <domain>/.claude-plugin/plugin.json + marketplace.json   Plugin/marketplace packaging

Design rule: generated context files carry an INDEX (name, description, path), never full skill
bodies. Injecting 38 skills into always-on context defeats progressive disclosure and is the
single most common way a skill library degrades the agent it was meant to help.

Usage:
  python3 scripts/sync-all.py            # regenerate everything
  python3 scripts/sync-all.py --check    # fail if any target is out of date (CI)
  python3 scripts/sync-all.py --only claude,cursor
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
VERSION = "1.0.0"
AUTHOR = "mchittineni"
REPO = "https://github.com/mchittineni/cloud-platform-skills"

DOMAIN_TITLES = {
    "01-devops-core": "DevOps Core Progression",
    "02-devsecops-and-secops": "DevSecOps & SecOps",
    "03-sre-slo-sla-observability": "SRE, SLO/SLA & Observability",
    "04-cloud-aws": "AWS Cloud Architecture",
    "05-cloud-azure": "Azure Cloud Architecture",
    "06-cloud-gcp": "GCP Cloud Architecture",
    "07-platform-engineering": "Platform Engineering",
    "08-finops-cloud-economics": "FinOps & Cloud Economics",
    "productivity": "Productivity & Meta-Skills",
}

PRINCIPLES = [
    "Infrastructure is code: modular, version-pinned, remote state locked and encrypted, no hardcoded account IDs or credentials.",
    "Credentials are short-lived: OIDC federation and workload identity over static keys, everywhere, with a tested revocation path.",
    "Security shifts left and runs at runtime: scan in CI with tuned gates, detect at runtime, and keep an owned exception register with expiry dates.",
    "Reliability is quantified: SLIs as good-events/valid-events, SLOs with error budgets, multi-window burn-rate alerts, and a pre-agreed freeze policy.",
    "Delivery is progressive: metric-gated canary or blue-green with automatic rollback; never an unguarded push to production.",
    "Platforms are products: golden paths and self-service abstractions, measured by adoption, not mandate.",
    "Cost is a design constraint: allocation tags enforced in IaC, unit economics, and waste removed before commitments are bought.",
    "Every recommendation carries its anti-pattern: state what not to do and why it fails in production.",
]


NEEDS_QUOTE = re.compile(r":\s|\s#|^[-?:,\[\]{}#&*!|>'\"%@`]|:$")


def yaml_quote(value: str) -> str:
    """Quote a scalar a strict YAML parser would otherwise misread.

    A plain scalar containing ": " is a mapping to YAML, not a string — the single most common way
    generated frontmatter becomes unloadable for the runtime that consumes it.
    """
    if value.startswith('"') and value.endswith('"'):
        return value
    if NEEDS_QUOTE.search(value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def read_skill(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 4)
    fm = text[4:end]
    body = text[end + 4 :]

    def field(k: str) -> str:
        """Return a frontmatter scalar with its YAML quoting removed.

        Descriptions are double-quoted in source because they contain ': ', which a strict YAML
        parser would otherwise read as a mapping. Those quotes are syntax, not content: leaving
        them in leaked a stray `"` into the end of every generated index row.
        """
        m = re.search(rf"^{k}:\s*(.+)$", fm, re.M)
        if not m:
            return ""
        value = m.group(1).strip()
        for q in ('"', "'"):
            if len(value) >= 2 and value.startswith(q) and value.endswith(q):
                value = value[1:-1]
                if q == '"':
                    value = value.replace('\\"', '"').replace("\\\\", "\\")
                break
        return value

    rel = path.parent.relative_to(ROOT)
    domain = rel.parts[1]
    tags = field("tags").strip("[]")
    return {
        "name": field("name"),
        "description": field("description"),
        "level": field("level"),
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "title": (re.search(r"^#\s+(.+)$", body, re.M) or [None, ""])[1]
        if re.search(r"^#\s+(.+)$", body, re.M)
        else "",
        "dir": path.parent,
        "rel": rel,
        "domain": domain,
        "text": text,
    }


def load_skills() -> list[dict]:
    return sorted((read_skill(p) for p in SKILLS.rglob("SKILL.md")), key=lambda s: (s["domain"], s["name"]))


# --------------------------------------------------------------------------- writers
class Writer:
    def __init__(self, check: bool):
        self.check = check
        self.stale: list[str] = []
        self.written: list[str] = []

    def file(self, path: Path, content: str) -> None:
        rel = str(path.relative_to(ROOT))
        if self.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                self.stale.append(rel)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            self.written.append(rel)

    def tree(self, src: Path, dst: Path) -> None:
        rel = str(dst.relative_to(ROOT))
        if self.check:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    target = dst / f.relative_to(src)
                    if not target.exists() or target.read_bytes() != f.read_bytes():
                        self.stale.append(f"{rel}/{f.relative_to(src)}")
            return
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        self.written.append(rel + "/")


def index_table(skills: list[dict], path_prefix: str = "skills") -> str:
    lines = []
    for domain, title in DOMAIN_TITLES.items():
        group = [s for s in skills if s["domain"] == domain]
        if not group:
            continue
        lines.append(f"\n### {title}\n")
        lines.append("| Skill | Level | Load when |")
        lines.append("| --- | --- | --- |")
        for s in group:
            trigger = s["description"].split("Use when", 1)
            when = ("Use when" + trigger[1]).strip() if len(trigger) > 1 else s["description"]
            when = when.replace("|", "/")
            lines.append(
                f"| [`{s['name']}`]({path_prefix}/{s['rel'].relative_to('skills')}/SKILL.md) | {s['level']} | {when} |"
            )
    return "\n".join(lines)


def gen_claude(w: Writer, skills: list[dict]) -> None:
    dest = ROOT / ".claude" / "skills"
    if not w.check and dest.exists():
        shutil.rmtree(dest)
    for s in skills:
        w.tree(s["dir"], dest / s["name"])
    w.file(
        ROOT / "CLAUDE.md",
        f"""# cloud-platform-skills — Claude Code guide

{len(skills)} production-grade Cloud, Platform, SRE, Security and FinOps skills. `skills/` is the
source of truth; every other directory is generated by `scripts/sync-all.py`.

## How to use this repository

- **Load one skill, not the library.** Each `SKILL.md` opens with a `## When to Use This Skill`
  block listing its triggers and, critically, when to route elsewhere. Follow that routing.
- Skills are discovered automatically from `.claude/skills/`. Nothing needs to be pasted into
  context, and no skill should be bulk-loaded "just in case".
- Depth beyond a skill's body lives in its `references/` and `scripts/`; load those on demand.

## Non-negotiable engineering principles

{chr(10).join(f"{i}. {p}" for i, p in enumerate(PRINCIPLES, 1))}

## Skill index
{index_table(skills)}

## Working in this repository

```bash
python3 scripts/validate-skills.py --check-sync --strict   # structure + frontmatter + mirrors
python3 scripts/run-evals.py --min-pass-rate 95            # routing + content-coverage evals
python3 scripts/compliance-check.py                        # 8-point compliance gate
python3 scripts/sync-all.py                                # regenerate every runtime target
```

All four must pass before a PR. See `CONTRIBUTING.md` for the full production pipeline and
`skills/productivity/write-a-skill/SKILL.md` for the authoring standard.
""",
    )


def gen_agents(w: Writer, skills: list[dict]) -> None:
    for s in skills:
        w.tree(s["dir"], ROOT / ".agents" / "skills" / s["name"])
    body = f"""# AGENTS.md — cloud-platform-skills

Instructions for any coding agent working in or consuming this repository (Codex, OpenClaw,
Cursor, Gemini CLI / Antigravity, Amp, Jules, Copilot coding agent).

## What this repository is

{len(skills)} eval-gated, production-grade engineering skills covering DevOps, DevSecOps, SRE,
AWS, Azure, GCP, Platform Engineering and FinOps. `skills/<domain>/<skill-name>/SKILL.md` is the
source of truth. `.claude/`, `.agents/`, `.cursor/`, `.github/copilot-instructions.md` and this
file are generated by `scripts/sync-all.py` — never edit them by hand.

## How an agent should use it

1. Read the skill index below and pick **one** skill whose triggers match the task.
2. Open that `SKILL.md`, read its `## When to Use This Skill` block first, and follow the
   "Route elsewhere" pointers if the task belongs to a sibling skill.
3. Load `references/` and `scripts/` from the skill only when the task needs that depth.
4. Do not concatenate multiple skills into context speculatively; these skills are written for
   progressive disclosure and lose accuracy when bulk-loaded.

## Engineering principles that apply to all output

{chr(10).join(f"{i}. {p}" for i, p in enumerate(PRINCIPLES, 1))}

## Skill index
{index_table(skills)}

## Repository gates

```bash
python3 scripts/validate-skills.py --check-sync --strict
python3 scripts/run-evals.py --min-pass-rate 95
python3 scripts/compliance-check.py
python3 scripts/sync-all.py --check
```

Every gate must pass before a change is merged. Scripts are stdlib-only Python 3.10+ and take
no network access.
"""
    w.file(ROOT / "AGENTS.md", body)
    w.file(ROOT / ".agents" / "rules" / "AGENTS.md", body)
    w.file(
        ROOT / ".agents" / "rules" / "GEMINI.md",
        f"""# Antigravity / Gemini CLI project rules

You are an expert principal DevOps, DevSecOps, SRE, FinOps, multi-cloud (AWS/Azure/GCP) and
platform engineer working in the cloud-platform-skills repository.

## Skill activation

{len(skills)} skills are discoverable under `.agents/skills/<skill-name>/SKILL.md`. Activate a
single skill whose triggers match the request — each file opens with a `## When to Use This
Skill` block that states both its triggers and when to route to a sibling skill. Use
`activate_skill(name="<skill-name>")` where the runtime provides it. Never load the whole
library into context.

## Core directives

{chr(10).join(f"{i}. {p}" for i, p in enumerate(PRINCIPLES, 1))}

## Full index

See `AGENTS.md` at the repository root for the complete routing table.
""",
    )


def gen_cursor(w: Writer, skills: list[dict]) -> None:
    rules = ROOT / ".cursor" / "rules"
    if not w.check and rules.exists():
        shutil.rmtree(rules)
    w.file(
        rules / "00-index.mdc",
        f"""---
description: Routing index and engineering principles for the cloud and platform engineering skill library
alwaysApply: true
---

# Engineering standards & skill routing

{chr(10).join(f"- {p}" for p in PRINCIPLES)}

## Skill routing

{len(skills)} skills live in `skills/<domain>/<skill-name>/SKILL.md`, each with per-skill Cursor
rules in `.cursor/rules/skills/<skill-name>.mdc` (agent-requested, not always applied). Pick one
skill matching the task and read its `## When to Use This Skill` block before answering.
{index_table(skills)}
""",
    )
    for s in skills:
        w.file(
            rules / "skills" / f"{s['name']}.mdc",
            f"""---
description: {yaml_quote(s["description"])}
globs:
alwaysApply: false
---

{s["text"].split(chr(10) + "---" + chr(10), 1)[-1].lstrip()}""",
        )


def gen_copilot(w: Writer, skills: list[dict]) -> None:
    w.file(
        ROOT / ".github" / "copilot-instructions.md",
        f"""# Copilot workspace instructions

You are an expert DevOps, DevSecOps, SRE, FinOps, cloud and platform engineer.

## Engineering standards

{chr(10).join(f"- {p}" for p in PRINCIPLES)}

## Skill library

This workspace carries {len(skills)} eval-gated skills under `skills/<domain>/<skill-name>/SKILL.md`.
For any non-trivial task, open the one skill whose triggers match and follow it — including its
"Route elsewhere" pointers. Do not answer from the index alone, and do not load the library
wholesale.
{index_table(skills)}
""",
    )


def gen_plugins(w: Writer, skills: list[dict]) -> None:
    entries = []
    for domain, title in DOMAIN_TITLES.items():
        group = [s for s in skills if s["domain"] == domain]
        if not group:
            continue
        desc = f"{title}: {len(group)} production-grade skills ({', '.join(s['name'] for s in group[:3])}{'...' if len(group) > 3 else ''})"
        w.file(
            SKILLS / domain / ".claude-plugin" / "plugin.json",
            json.dumps(
                {
                    "name": domain,
                    "description": desc[:300],
                    "version": VERSION,
                    "author": AUTHOR,
                    "homepage": REPO,
                    "repository": REPO,
                    "license": "MIT",
                    "skills": "./",
                },
                indent=2,
            )
            + "\n",
        )
        entries.append({"name": domain, "source": f"./skills/{domain}", "description": desc[:300]})
    w.file(
        ROOT / ".claude-plugin" / "marketplace.json",
        json.dumps(
            {
                "name": "cloud-platform-skills",
                "owner": {"name": AUTHOR, "url": REPO},
                "plugins": entries,
            },
            indent=2,
        )
        + "\n",
    )


TARGETS = {
    "claude": gen_claude,
    "agents": gen_agents,
    "cursor": gen_cursor,
    "copilot": gen_copilot,
    "plugins": gen_plugins,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report stale targets and exit non-zero")
    ap.add_argument("--only", help=f"comma-separated subset of: {', '.join(TARGETS)}")
    args = ap.parse_args()

    skills = load_skills()
    if not skills:
        print("error: no skills found", file=sys.stderr)
        return 2

    selected = args.only.split(",") if args.only else list(TARGETS)
    unknown = [t for t in selected if t not in TARGETS]
    if unknown:
        print(f"error: unknown target(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    w = Writer(args.check)
    for t in selected:
        TARGETS[t](w, skills)

    if args.check:
        if w.stale:
            print(f"{len(w.stale)} generated file(s) out of date — run scripts/sync-all.py:")
            for s in w.stale[:25]:
                print(f"  - {s}")
            if len(w.stale) > 25:
                print(f"  ... and {len(w.stale) - 25} more")
            return 1
        print(f"all generated targets up to date ({len(skills)} skills)")
        return 0

    print(f"synced {len(skills)} skills -> {', '.join(selected)}")
    for f in w.written[:12]:
        print(f"  wrote {f}")
    if len(w.written) > 12:
        print(f"  ... and {len(w.written) - 12} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
