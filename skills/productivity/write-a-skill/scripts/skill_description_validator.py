#!/usr/bin/env python3
"""
skill_description_validator.py — validate a SKILL.md frontmatter description.

The description is the only text an agent reads when deciding whether to load a skill, so it is
validated as a routing decision, not as prose:

  * parses as strict YAML — a plain scalar containing ": " is a MAPPING to a real YAML parser,
    which makes the whole skill unloadable (the single highest-impact defect in this class)
  * 120-700 characters, single line
  * third person
  * carries an explicit "Use when ..." trigger clause
  * does not leak seniority ("Mid-level ...") that belongs in the `level` field

Stdlib only. Exit codes: 0 valid, 1 findings, 2 usage error.

Usage:
  python3 skill_description_validator.py path/to/SKILL.md
  python3 skill_description_validator.py skills/ --recursive --json
  python3 skill_description_validator.py --demo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MIN_LEN, MAX_LEN = 120, 700
HARD_MAX = 1024  # runtime truncation point

TRIGGER_RE = re.compile(r"\buse (when|for|while)\b", re.I)
# Pronouns only when they stand alone: the naive \b(i)\b form fires on "I/O wait", and \b(us)\b
# fires on "us-east-1". Both appear legitimately in cloud descriptions.
PERSON_RE = re.compile(r"(?<![\w/-])(i|we|my|our|you|your|us)(?![\w/-])", re.I)
LEVEL_LEAK_RE = re.compile(r"^\s*(junior|mid|senior|staff|principal)[\w\s/-]*?level\b", re.I)
YAML_UNSAFE_PLAIN = re.compile(r":\s|\s#")
YAML_UNSAFE_START = re.compile(r"^[-?:,\[\]{}#&*!|>%@`]")

DEMO = '''---
name: sample-skill
description: "Terraform state locking and VPC module design: remote backends, DynamoDB locks, and drift detection. Use when structuring an IaC repository, configuring a state backend, or investigating unexplained infrastructure drift."
level: mid
tags: [terraform, iac, aws]
compatible_runtimes: [claude, codex, cursor]
---

# Sample
'''


def extract_description(text: str) -> tuple[str | None, list[str]]:
    """Return (description, findings). Findings here are structural, not stylistic."""
    if not text.startswith("---\n"):
        return None, ["frontmatter: file does not open with '---'"]
    end = text.find("\n---", 4)
    if end == -1:
        return None, ["frontmatter: never closed with '---'"]

    raw_value, findings = None, []
    lines = text[4:end].splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^description:\s*(.*)$", line)
        if not m:
            continue
        value = m.group(1).strip()
        if value in (">", ">-", "|", "|-", "|+", ">+", ""):
            folded = []
            for cont in lines[i + 1 :]:
                if cont.strip() and not cont.startswith((" ", "\t")):
                    break
                folded.append(cont.strip())
            raw_value = " ".join(x for x in folded if x).strip()
            findings.append(
                "description: uses a folded/block scalar; a single quoted line is easier for "
                "every runtime to read back identically"
            )
        else:
            raw_value = value
        break

    if raw_value is None:
        return None, ["frontmatter: no `description` field"]

    quoted = len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in "\"'"
    if not quoted and (YAML_UNSAFE_PLAIN.search(raw_value) or YAML_UNSAFE_START.match(raw_value)):
        findings.append(
            "description: unquoted plain scalar containing ': ' or ' #' — a strict YAML parser "
            "reads this as a mapping and fails to load the skill. Wrap the value in double quotes"
        )

    if quoted:
        raw_value = raw_value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw_value, findings


def validate_description(text: str) -> list[str]:
    description, findings = extract_description(text)
    if description is None:
        return findings
    if not description:
        return findings + ["description: empty"]

    n = len(description)
    if n < MIN_LEN:
        findings.append(f"description: {n} chars is too thin (min {MIN_LEN}) — state the capability AND the triggers")
    if n > MAX_LEN:
        findings.append(f"description: {n} chars exceeds the {MAX_LEN}-char budget"
                        + (f" (runtime hard limit {HARD_MAX})" if n > HARD_MAX else ""))
    if not TRIGGER_RE.search(description):
        findings.append("description: no explicit 'Use when ...' trigger clause — nothing will route to this skill")
    pronouns = sorted({p.lower() for p in PERSON_RE.findall(description)})
    if pronouns:
        findings.append(f"description: must be third person; found {', '.join(pronouns)}")
    if LEVEL_LEAK_RE.search(description):
        findings.append("description: leaks seniority into routing text — that belongs in the `level` field")
    return findings


def check_file(path: Path) -> dict:
    findings = validate_description(path.read_text(encoding="utf-8"))
    return {"path": str(path), "valid": not findings, "findings": findings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="SKILL.md, or a directory with --recursive")
    ap.add_argument("-r", "--recursive", action="store_true", help="validate every SKILL.md under a directory")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--demo", action="store_true", help="run against a built-in valid sample")
    args = ap.parse_args()

    if args.demo:
        findings = validate_description(DEMO)
        print(json.dumps({"demo": True, "valid": not findings, "findings": findings}, indent=2)
              if args.json else ("demo sample is valid" if not findings else f"demo findings: {findings}"))
        return 0 if not findings else 1

    if not args.target:
        ap.error("a target is required (or pass --demo)")

    target = Path(args.target)
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2

    if target.is_dir():
        if not args.recursive:
            print(f"error: {target} is a directory; pass --recursive", file=sys.stderr)
            return 2
        files = sorted(target.rglob("SKILL.md"))
        if not files:
            print(f"error: no SKILL.md found under {target}", file=sys.stderr)
            return 2
    else:
        files = [target]

    results = [check_file(f) for f in files]
    failed = [r for r in results if not r["valid"]]

    if args.json:
        print(json.dumps({"checked": len(results), "failed": len(failed), "results": results}, indent=2))
    else:
        for r in results:
            if r["valid"]:
                print(f"PASS  {r['path']}")
            else:
                print(f"FAIL  {r['path']}")
                for f in r["findings"]:
                    print(f"      x {f}")
        print(f"\n{len(results) - len(failed)}/{len(results)} valid")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
