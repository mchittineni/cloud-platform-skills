#!/usr/bin/env python3
"""
next-version.py — derive the next semver from Conventional Commits. Stdlib only.

A version chosen by hand drifts from what the commits actually said, and the drift is only
visible to consumers after they have installed the wrong thing. This makes the version a
function of the change set: the commit subjects since the last tag decide the bump.

Bump rules (Conventional Commits):
  `type!:` subject or `BREAKING CHANGE:` in the body -> major
  `feat`                                             -> minor
  `fix`, `perf`                                      -> patch
  anything else (chore, docs, ci, refactor, test)    -> no release

Modes:
  --current         print the version recorded in the domain plugin.json manifests
  --next            print the next version, or "none" when nothing is releasable
  --notes VERSION   print a CHANGELOG section for VERSION built from those commits

Usage:
  python3 scripts/next-version.py --next
  python3 scripts/next-version.py --notes 1.1.0
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# type(optional scope)optional !: subject
SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")

MINOR_TYPES = {"feat"}
PATCH_TYPES = {"fix", "perf"}

# Section heading each releasable type is filed under in the CHANGELOG.
SECTIONS = [("feat", "Added"), ("fix", "Fixed"), ("perf", "Changed")]

RECORD, UNIT = "\x1e", "\x1f"


def git(*args: str) -> str:
    # S603/S607: every argument here is an internal literal from this module, never user
    # input, and `git` is resolved from PATH the same way every other repo gate resolves it.
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def last_tag() -> str | None:
    tag = git("describe", "--tags", "--abbrev=0", "--match", "v*.*.*")
    return tag or None


def current_version() -> str | None:
    """The version every domain manifest agrees on, or None if they disagree."""
    versions = {
        json.loads(p.read_text(encoding="utf-8")).get("version")
        for p in sorted(SKILLS.glob("*/.claude-plugin/plugin.json"))
    }
    return versions.pop() if len(versions) == 1 else None


def commits_since(tag: str | None) -> list[tuple[str, str]]:
    """(subject, body) for each commit after `tag`, oldest first."""
    rng = f"{tag}..HEAD" if tag else "HEAD"
    raw = git("log", rng, f"--format=%s{UNIT}%b{RECORD}", "--reverse")
    out = []
    for rec in raw.split(RECORD):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        subject, _, body = rec.partition(UNIT)
        out.append((subject.strip(), body.strip()))
    return out


def bump_of(subject: str, body: str) -> str | None:
    m = SUBJECT.match(subject)
    if not m:
        return None
    if m.group("bang") or re.search(r"^BREAKING[ -]CHANGE:", body, re.M):
        return "major"
    ctype = m.group("type")
    if ctype in MINOR_TYPES:
        return "minor"
    if ctype in PATCH_TYPES:
        return "patch"
    return None


def apply_bump(version: str, level: str) -> str:
    major, minor, patch = (int(x) for x in SEMVER.match(version).groups())
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def decide() -> tuple[str, str | None]:
    """(current_version, next_version-or-None)."""
    current = current_version()
    if current is None or not SEMVER.match(current or ""):
        print("error: domain manifests do not agree on one semver version", file=sys.stderr)
        raise SystemExit(2)
    levels = {b for s, b in ((c, bump_of(*c)) for c in commits_since(last_tag())) if b}
    for level in ("major", "minor", "patch"):
        if level in levels:
            return current, apply_bump(current, level)
    return current, None


def notes(version: str) -> str:
    buckets: dict[str, list[str]] = {}
    breaking: list[str] = []
    for subject, body in commits_since(last_tag()):
        level = bump_of(subject, body)
        if not level:
            continue
        m = SUBJECT.match(subject)
        scope, desc = m.group("scope"), m.group("desc")
        entry = f"- {'**' + scope + '**: ' if scope else ''}{desc}"
        if level == "major":
            breaking.append(entry)
        buckets.setdefault(m.group("type"), []).append(entry)

    today = dt.date.today().isoformat()
    lines = [f"## [{version}] - {today}", ""]
    if breaking:
        lines += ["### Breaking changes", "", *breaking, ""]
    for ctype, heading in SECTIONS:
        if buckets.get(ctype):
            lines += [f"### {heading}", "", *buckets[ctype], ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--current", action="store_true")
    g.add_argument("--next", action="store_true")
    g.add_argument("--notes", metavar="VERSION")
    args = ap.parse_args()

    if args.current:
        print(current_version() or "")
        return 0
    if args.next:
        _, nxt = decide()
        print(nxt or "none")
        return 0
    print(notes(args.notes), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
