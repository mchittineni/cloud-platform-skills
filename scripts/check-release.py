#!/usr/bin/env python3
"""
check-release.py — release consistency gate and evidence builder. Stdlib only.

A release that claims a version the manifests do not agree with is how consumers end up installing
something other than what the changelog describes. This enforces agreement before publishing.

Modes:
  --version X.Y.Z    verify the tag matches every domain plugin.json and has a CHANGELOG entry
  --notes X.Y.Z      extract that version's CHANGELOG section as release notes
  --manifest PATH    write an inventory of every shipped skill (name, level, tier inputs, hash)
  --bump X.Y.Z       rewrite every domain plugin.json to the given version

Usage:
  python3 scripts/check-release.py --version 1.0.0
  python3 scripts/check-release.py --notes 1.0.0 --out release-notes.md
  python3 scripts/check-release.py --manifest skills-manifest.json
  python3 scripts/check-release.py --bump 2.7.1
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CHANGELOG = ROOT / "CHANGELOG.md"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

STRICT_PLUGIN_FIELDS = {
    "name",
    "description",
    "version",
    "author",
    "homepage",
    "repository",
    "license",
    "skills",
}


def plugin_files() -> list[Path]:
    return sorted(SKILLS.glob("*/.claude-plugin/plugin.json"))


def changelog_section(version: str) -> str | None:
    if not CHANGELOG.exists():
        return None
    text = CHANGELOG.read_text(encoding="utf-8")
    m = re.search(rf"^##\s*\[{re.escape(version)}\][^\n]*\n(.*?)(?=^##\s*\[|\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else None


def verify(version: str) -> int:
    errors: list[str] = []
    if not SEMVER.match(version):
        errors.append(f"version '{version}' is not semver X.Y.Z")

    files = plugin_files()
    if not files:
        errors.append("no domain plugin.json found — run scripts/sync-all.py")
    for pf in files:
        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{pf.relative_to(ROOT)}: invalid JSON ({e})")
            continue
        extra = set(data) - STRICT_PLUGIN_FIELDS
        missing = STRICT_PLUGIN_FIELDS - set(data)
        if extra:
            errors.append(f"{pf.relative_to(ROOT)}: non-strict field(s) {', '.join(sorted(extra))}")
        if missing:
            errors.append(f"{pf.relative_to(ROOT)}: missing field(s) {', '.join(sorted(missing))}")
        if data.get("version") != version:
            errors.append(f"{pf.relative_to(ROOT)}: version '{data.get('version')}' != tag '{version}'")

    if MARKETPLACE.exists():
        mk = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        listed = {p["name"] for p in mk.get("plugins", [])}
        on_disk = {pf.parent.parent.name for pf in files}
        for missing in sorted(on_disk - listed):
            errors.append(f"marketplace.json: plugin '{missing}' not listed")
        for stale in sorted(listed - on_disk):
            errors.append(f"marketplace.json: lists '{stale}' which has no plugin.json")
    else:
        errors.append("no .claude-plugin/marketplace.json — run scripts/sync-all.py")

    if changelog_section(version) is None:
        errors.append(f"CHANGELOG.md has no '## [{version}]' section")

    if errors:
        print(f"release {version}: NOT READY")
        for e in errors:
            print(f"  x {e}")
        return 1
    print(
        f"release {version}: consistent across {len(files)} plugin manifest(s), "
        "marketplace.json and CHANGELOG.md"
    )
    return 0


def notes(version: str, out: Path | None) -> int:
    section = changelog_section(version)
    if section is None:
        print(f"error: CHANGELOG.md has no '## [{version}]' section", file=sys.stderr)
        return 1
    body = f"## {version}\n\n{section}\n"
    if out:
        out.write_text(body, encoding="utf-8")
        print(f"release notes written to {out} ({len(section.splitlines())} lines)")
    else:
        print(body)
    return 0


def _field(frontmatter: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def manifest(out: Path) -> int:
    entries = []
    for sf in sorted(SKILLS.rglob("SKILL.md")):
        text = sf.read_text(encoding="utf-8")
        fm = text[4 : text.find("\n---", 4)]
        ev = sf.parent / "evals" / "evals.json"
        entries.append(
            {
                "name": _field(fm, "name"),
                "domain": sf.parent.relative_to(SKILLS).parts[0],
                "level": _field(fm, "level"),
                "path": str(sf.relative_to(ROOT)),
                "lines": len(text.splitlines()),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "eval_cases": len(json.loads(ev.read_text(encoding="utf-8")).get("cases", []))
                if ev.exists()
                else 0,
                "has_references": (sf.parent / "references").is_dir(),
                "has_scripts": (sf.parent / "scripts").is_dir(),
            }
        )
    payload = {
        "skills": len(entries),
        "domains": sorted({e["domain"] for e in entries}),
        "eval_cases_total": sum(e["eval_cases"] for e in entries),
        "entries": entries,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"manifest written to {out}: {len(entries)} skills, {payload['eval_cases_total']} eval cases")
    return 0


def bump(version: str) -> int:
    if not SEMVER.match(version):
        print(f"error: '{version}' is not semver X.Y.Z", file=sys.stderr)
        return 2
    changed = 0
    for pf in plugin_files():
        data = json.loads(pf.read_text(encoding="utf-8"))
        if data.get("version") != version:
            data["version"] = version
            pf.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            changed += 1
    print(f"bumped {changed} plugin manifest(s) to {version}")
    print(
        "next: update VERSION in scripts/sync-all.py so regeneration keeps this value, "
        "then add the CHANGELOG section"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--version", help="verify manifests and CHANGELOG agree with this version")
    g.add_argument("--notes", help="extract release notes for this version")
    g.add_argument("--manifest", help="write a skill inventory to this path")
    g.add_argument("--bump", help="set every domain plugin.json to this version")
    ap.add_argument("--out", help="output path for --notes")
    args = ap.parse_args()

    if args.version:
        return verify(args.version)
    if args.notes:
        return notes(args.notes, Path(args.out) if args.out else None)
    if args.manifest:
        return manifest(Path(args.manifest))
    return bump(args.bump)


if __name__ == "__main__":
    sys.exit(main())
