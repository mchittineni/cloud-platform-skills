#!/usr/bin/env python3
"""
skill_structure_validator.py — validate a skill folder against the progressive-disclosure contract.

Checks the structure that makes a skill loadable and cheap to load:

  * SKILL.md exists, opens with frontmatter, and carries exactly one H1
  * `name` in frontmatter matches the directory name (how every runtime addresses a skill)
  * a "When to Use This Skill" routing block with Triggers, and ideally "Route elsewhere"
  * line budget: 200 comfort / 500 ceiling, unless `<!-- line-budget-justified: … -->` is present
  * bundled directories (references/, scripts/, assets/, evals/) exist where referenced
  * every relative link and bundled path in the body resolves
  * bundled Python is stdlib-only and exposes --help

Stdlib only. Exit codes: 0 valid, 1 findings, 2 usage error.

Usage:
  python3 skill_structure_validator.py path/to/skill-folder
  python3 skill_structure_validator.py skills/ --recursive --json
  python3 skill_structure_validator.py --demo
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

COMFORT_LINES, CEILING_LINES = 200, 500
ROUTING_BLOCK = "## When to Use This Skill"
JUSTIFIED = re.compile(r"<!--\s*line-budget-justified:")

STDLIB = {
    "argparse", "ast", "base64", "collections", "csv", "dataclasses", "datetime", "difflib",
    "enum", "functools", "glob", "hashlib", "hmac", "io", "ipaddress", "itertools", "json",
    "logging", "math", "os", "pathlib", "random", "re", "shlex", "shutil", "socket", "sqlite3",
    "statistics", "string", "subprocess", "sys", "tempfile", "textwrap", "time", "tomllib",
    "types", "typing", "unittest", "urllib", "uuid", "warnings", "xml", "zipfile", "__future__",
}

FENCE_RE = re.compile(r"^([ \t]*)(```+|~~~+)")


def strip_fences(body: str) -> str:
    out, fence = [], None
    for line in body.splitlines():
        m = FENCE_RE.match(line)
        if m and fence is None:
            fence = m.group(2)[:3]
            out.append("")
            continue
        if fence is not None:
            if m and m.group(2).startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def validate_structure(folder: Path) -> list[str]:
    issues: list[str] = []
    if not folder.is_dir():
        return [f"{folder} is not a directory"]

    skill_md = folder / "SKILL.md"
    if not skill_md.exists():
        return [f"missing mandatory SKILL.md in {folder}"]

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not text.startswith("---\n"):
        issues.append("SKILL.md does not open with YAML frontmatter")
    else:
        end = text.find("\n---", 4)
        fm = text[4:end] if end != -1 else ""
        m = re.search(r"^name:\s*(.+)$", fm, re.M)
        if not m:
            issues.append("frontmatter: no `name` field")
        elif m.group(1).strip().strip("\"'") != folder.name:
            issues.append(
                f"frontmatter: name '{m.group(1).strip()}' does not match directory '{folder.name}' "
                "— runtimes address skills by directory"
            )
        body = text[end + 4 :] if end != -1 else text
    prose = strip_fences(body if text.startswith("---\n") and end != -1 else text)

    h1s = re.findall(r"^#\s+\S.*$", prose, re.M)
    if len(h1s) != 1:
        issues.append(f"expected exactly one H1 title, found {len(h1s)}")

    if ROUTING_BLOCK not in prose:
        issues.append(f"missing the '{ROUTING_BLOCK}' routing block")
    else:
        block = prose.split(ROUTING_BLOCK, 1)[1].split("\n## ", 1)[0]
        if "Triggers" not in block:
            issues.append(f"'{ROUTING_BLOCK}' block has no **Triggers** list")
        if "Route elsewhere" not in block:
            issues.append(
                f"'{ROUTING_BLOCK}' block has no 'Route elsewhere' list — agents cannot tell "
                "when NOT to use this skill"
            )

    if len(lines) > CEILING_LINES and not JUSTIFIED.search(text):
        issues.append(
            f"SKILL.md is {len(lines)} lines, over the {CEILING_LINES}-line ceiling; move depth "
            "into references/ or add <!-- line-budget-justified: reason -->"
        )
    elif len(lines) > COMFORT_LINES:
        issues.append(
            f"SKILL.md is {len(lines)} lines, past the {COMFORT_LINES}-line comfort budget "
            "(advisory) — consider references/"
        )

    for ref in sorted(set(re.findall(r"(?:\]\(|`)((?:\./)?(?:scripts|references|assets|evals)/[\w./-]+)", prose))):
        if not (folder / ref.lstrip("./")).exists():
            issues.append(f"broken bundled reference: {ref}")

    for py in sorted(folder.rglob("*.py")):
        src = py.read_text(encoding="utf-8")
        rel = py.relative_to(folder)
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            issues.append(f"{rel}: syntax error on line {e.lineno}")
            continue
        local = {p.stem for p in py.parent.glob("*.py")}
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
        external = sorted(m for m in mods if m not in STDLIB and m not in local)
        if external:
            issues.append(f"{rel}: non-stdlib import(s): {', '.join(external)}")
        if "argparse" not in mods:
            issues.append(f"{rel}: no argparse — a bundled tool must expose --help")

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="skill folder, or a parent directory with --recursive")
    ap.add_argument("-r", "--recursive", action="store_true", help="validate every skill folder beneath target")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--demo", action="store_true", help="validate this skill's own folder")
    args = ap.parse_args()

    if args.demo:
        target, recursive = Path(__file__).resolve().parent.parent, False
    elif args.target:
        target, recursive = Path(args.target), args.recursive
    else:
        ap.error("a target is required (or pass --demo)")

    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2

    folders = sorted({p.parent for p in target.rglob("SKILL.md")}) if recursive else [target]
    if not folders:
        print(f"error: no SKILL.md found under {target}", file=sys.stderr)
        return 2

    results = [{"skill": f.name, "path": str(f), "issues": validate_structure(f)} for f in folders]
    failed = [r for r in results if r["issues"]]

    if args.json:
        print(json.dumps({"checked": len(results), "failed": len(failed), "results": results}, indent=2))
    else:
        for r in results:
            if not r["issues"]:
                print(f"PASS  {r['path']}")
            else:
                print(f"FAIL  {r['path']}")
                for i in r["issues"]:
                    print(f"      x {i}")
        print(f"\n{len(results) - len(failed)}/{len(results)} valid")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
