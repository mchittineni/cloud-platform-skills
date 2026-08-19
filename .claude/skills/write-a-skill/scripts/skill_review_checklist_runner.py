#!/usr/bin/env python3
"""
skill_review_checklist_runner.py — run the 6-gate authoring review on a SKILL.md.

Combines the description and structure validators into the review a human would otherwise do from
memory, and reports a per-gate verdict:

  Gate 1  Description  — strict-YAML-safe, length, third person, explicit "Use when" triggers
  Gate 2  Structure    — one H1, routing block with Triggers + Route elsewhere, name/dir agreement
  Gate 3  Line budget  — 200 comfort / 500 ceiling, progressive disclosure into references/
  Gate 4  Anti-patterns— states what NOT to do, not only what to do
  Gate 5  Artifacts    — carries runnable, language-tagged code
  Gate 6  Portability  — declares compatible_runtimes, and ships evals

Stdlib only, and importable from any working directory. Exit codes: 0 pass, 1 findings, 2 usage.

Usage:
  python3 skill_review_checklist_runner.py path/to/SKILL.md
  python3 skill_review_checklist_runner.py skills/ --recursive --json
  python3 skill_review_checklist_runner.py --demo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Import the sibling validators regardless of the caller's working directory. The previous version
# used a bare `from skill_description_validator import ...`, which only resolved when the process
# happened to start inside this folder — it crashed when run from the repository root, which is
# exactly how the documentation says to run it.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_description_validator import validate_description  # noqa: E402
from skill_structure_validator import strip_fences, validate_structure  # noqa: E402

ANTIPATTERN_RE = re.compile(r"anti-pattern|don't|do not|never|avoid|instead of|fails? in production", re.I)
FENCE_RE = re.compile(r"^([ \t]*)(```+|~~~+)([a-zA-Z0-9_+-]*)")


def opening_fences(text: str) -> list[str]:
    """Languages declared on OPENING fences only.

    A closing fence carries no language by definition, so matching every ``` line reports one
    bogus finding per code block — the fences must be paired.
    """
    langs, marker = [], None
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if not m:
            continue
        if marker is None:
            marker = m.group(2)[:3]
            langs.append(m.group(3))
        elif m.group(2).startswith(marker) and not m.group(3):
            marker = None
    return langs


def run_checklist(skill_md: Path) -> dict:
    folder = skill_md.parent
    text = skill_md.read_text(encoding="utf-8")
    prose = strip_fences(text)
    lines = text.splitlines()
    gates = []

    desc_issues = validate_description(text)
    gates.append({"gate": 1, "name": "Description", "passed": not desc_issues, "findings": desc_issues})

    struct = validate_structure(folder)
    structural = [i for i in struct if "comfort budget" not in i and "ceiling" not in i]
    budget = [i for i in struct if "comfort budget" in i or "ceiling" in i]
    gates.append({"gate": 2, "name": "Structure", "passed": not structural, "findings": structural})

    over_ceiling = [i for i in budget if "ceiling" in i]
    gates.append({
        "gate": 3, "name": "Line budget", "passed": not over_ceiling,
        "findings": budget or [f"{len(lines)} lines — within budget"],
    })

    has_anti = bool(ANTIPATTERN_RE.search(prose))
    gates.append({
        "gate": 4, "name": "Anti-patterns", "passed": has_anti,
        "findings": [] if has_anti else ["no anti-patterns, failure modes, or explicit don'ts found"],
    })

    langs = opening_fences(text)
    unlabelled = sum(1 for x in langs if not x)
    gates.append({
        "gate": 5, "name": "Artifacts", "passed": bool(langs) and unlabelled == 0,
        "findings": ([] if langs else ["no fenced code blocks — the skill carries no runnable artifact"])
                    + ([f"{unlabelled} code fence(s) declare no language"] if unlabelled else []),
    })

    portability = []
    if "compatible_runtimes" not in text:
        portability.append("frontmatter: no compatible_runtimes declaration")
    if not (folder / "evals" / "evals.json").exists():
        portability.append("no evals/evals.json — trigger behaviour is untested")
    gates.append({"gate": 6, "name": "Portability", "passed": not portability, "findings": portability})

    return {
        "skill": folder.name,
        "path": str(skill_md),
        "lines": len(lines),
        "passed": all(g["passed"] for g in gates),
        "gates": gates,
    }


def print_report(r: dict) -> None:
    status = "PASS" if r["passed"] else "FAIL"
    print(f"{status}  {r['skill']}  ({r['lines']} lines)")
    for g in r["gates"]:
        mark = "ok " if g["passed"] else "X  "
        print(f"      {mark}Gate {g['gate']} [{g['name']}]")
        for f in g["findings"]:
            if not g["passed"] or "within budget" not in f:
                print(f"           - {f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="SKILL.md, a skill folder, or a parent with --recursive")
    ap.add_argument("-r", "--recursive", action="store_true", help="review every SKILL.md beneath target")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--demo", action="store_true", help="review this skill itself")
    args = ap.parse_args()

    if args.demo:
        targets = [Path(__file__).resolve().parent.parent / "SKILL.md"]
    elif not args.target:
        ap.error("a target is required (or pass --demo)")
    else:
        target = Path(args.target)
        if not target.exists():
            print(f"error: {target} does not exist", file=sys.stderr)
            return 2
        if target.is_dir():
            targets = sorted(target.rglob("SKILL.md")) if args.recursive else [target / "SKILL.md"]
        else:
            targets = [target]
        targets = [t for t in targets if t.exists()]
        if not targets:
            print(f"error: no SKILL.md found under {args.target}", file=sys.stderr)
            return 2

    results = [run_checklist(t) for t in targets]
    failed = [r for r in results if not r["passed"]]

    if args.json:
        print(json.dumps({"reviewed": len(results), "failed": len(failed), "results": results}, indent=2))
    else:
        for r in results:
            print_report(r)
        print(f"\n{len(results) - len(failed)}/{len(results)} skills pass all six gates")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
