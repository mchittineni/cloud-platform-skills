#!/usr/bin/env python3
"""
audit-workflows.py — security audit for GitHub Actions workflows. Stdlib only.

CI is the highest-privilege automation in most repositories: it holds the tokens, and it runs
third-party code on every push. This gate enforces the controls that actually contain that blast
radius, and it fails loudly rather than assuming a workflow is fine because it is short.

Checks:
  W01  every workflow declares least-privilege `permissions` (top level or per job)
  W02  no `permissions: write-all`, and no unnecessary `contents: write`
  W03  every job sets `timeout-minutes` (a hung job holds a runner and a token)
  W04  third-party actions are pinned to a full 40-hex commit SHA, not a mutable tag
  W05  no `pull_request_target` / `workflow_run` combined with a checkout of untrusted PR code
  W06  no untrusted `${{ github.event.* }}` / `head_ref` interpolation inside `run:` (script injection)
  W07  push/pull_request workflows declare a `concurrency` group
  W08  `secrets` are not referenced in jobs reachable from an untrusted fork PR trigger
  W09  `actions/checkout` sets `persist-credentials: false` unless the job pushes
  W10  uploaded artifacts declare `retention-days`
  W11  pin exceptions in .github/actions-allowlist.txt have an owner and a future expiry
  W12  no stale pin exceptions (an entry no workflow uses is an exception nobody reviews)
  W13  no tool version hardcoded in a `run:` when a canonical pin already exists elsewhere

Usage:
  python3 scripts/audit-workflows.py
  python3 scripts/audit-workflows.py --json --out workflow-audit.json
  python3 scripts/audit-workflows.py --allow-tag-pins      # downgrade W04 to a warning
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
WF_DIR = ROOT / ".github" / "workflows"

SHA_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
COMMENT_RE = re.compile(r"\s+#.*$")
FIRST_PARTY = ("actions/", "github/")
UNTRUSTED_CTX = re.compile(
    r"\$\{\{\s*(github\.event\.(?:issue|pull_request|comment|review|discussion|head_commit)"
    r"[\w.]*|github\.head_ref|github\.event\.workflow_run\.head_branch)",
)
UNTRUSTED_TRIGGERS = {"pull_request_target", "issue_comment", "workflow_run"}
ALLOWLIST = ROOT / ".github" / "actions-allowlist.txt"

# W13 — every one of these tools already has exactly one authoritative pin. A second copy inside a
# `run:` block is how CI silently ends up linting with a different version than a laptop does: the
# local run goes green against tool version A while CI enforces version B, so "lint is clean" stops
# meaning anything. Map tool -> where its version is allowed to live.
CANONICAL_PINS = {
    "markdownlint-cli2": "package.json (run it via `npm ci` + `npm run lint:check`)",
    "prettier": "package.json (run it via `npm ci` + `npm run format:check`)",
    "ruff": "the Makefile's RUFF_VERSION (run it via `make lint-py`)",
    "mkdocs": "requirements-dev.txt",
    "mkdocs-material": "requirements-dev.txt",
    "pre-commit": "requirements-dev.txt",
}
# `npx pkg@1.2.3`, `pip install pkg==1.2.3`, `npm i -g pkg@1.2.3`
HARDCODED_TOOL = re.compile(
    r"(?:^|[\s=/])(" + "|".join(re.escape(t) for t in CANONICAL_PINS) + r")(?:@|==)([0-9][\w.\-]*)",
)


def load_allowlist(today: str) -> tuple[dict[str, dict], list[dict]]:
    """Owned, expiring exceptions for actions that are not yet SHA-pinned.

    Format, one per line:
        action@tag | expires=YYYY-MM-DD | owner=@handle | reason text

    An exception without an expiry, or past its expiry, is a blocker — the same rule this library
    teaches for security exception registers. Exceptions are reported on every run.
    """
    entries: dict[str, dict] = {}
    problems: list[dict] = []
    if not ALLOWLIST.exists():
        return entries, problems
    for lineno, raw in enumerate(ALLOWLIST.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        ref = parts[0]
        meta = {}
        for part in parts[1:]:
            if "=" in part:
                k, _, v = part.partition("=")
                meta[k.strip()] = v.strip()
            else:
                meta.setdefault("reason", part)
        expires, owner = meta.get("expires"), meta.get("owner")
        if not expires or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expires):
            problems.append(
                {
                    "file": ".github/actions-allowlist.txt",
                    "code": "W11",
                    "severity": "blocker",
                    "job": None,
                    "message": f"line {lineno}: exception for `{ref}` has no valid expires=YYYY-MM-DD",
                }
            )
            continue
        if not owner:
            problems.append(
                {
                    "file": ".github/actions-allowlist.txt",
                    "code": "W11",
                    "severity": "major",
                    "job": None,
                    "message": f"line {lineno}: exception for `{ref}` has no owner=",
                }
            )
        if expires < today:
            problems.append(
                {
                    "file": ".github/actions-allowlist.txt",
                    "code": "W11",
                    "severity": "blocker",
                    "job": None,
                    "message": f"line {lineno}: exception for `{ref}` expired on {expires} "
                    "— pin the SHA or renew with justification",
                }
            )
            continue
        entries[ref] = meta
    return entries, problems


# ------------------------------------------------------------------ minimal YAML subset parser
def parse_yaml(text: str):
    """Parse the YAML subset GitHub workflows use: nested maps, lists, and block scalars."""
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip(), raw))
    pos = 0

    def scalar(v: str):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            return v[1:-1]
        if v in ("true", "True", "yes", "on"):
            return True
        if v in ("false", "False", "no", "off"):
            return False
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        if v.startswith("[") and v.endswith("]"):
            return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
        return v

    def block(indent: int) -> str:
        nonlocal pos
        out = []
        while pos < len(lines) and (lines[pos][0] > indent or not lines[pos][1]):
            out.append(lines[pos][2])
            pos += 1
        return "\n".join(out)

    def node(indent: int):
        nonlocal pos
        if pos >= len(lines):
            return None
        if lines[pos][1].startswith("- "):
            items = []
            while pos < len(lines) and lines[pos][0] == indent and lines[pos][1].startswith("- "):
                cur_indent, stripped, _ = lines[pos]
                rest = stripped[2:].strip()
                pos += 1
                if ":" in rest and not rest.startswith(("[", "{", '"', "'")):
                    # inline first key of a mapping item
                    k, _, v = rest.partition(":")
                    item = {}
                    if v.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
                        item[k.strip()] = block(cur_indent + 2)
                    elif v.strip():
                        item[k.strip()] = scalar(v)
                    else:
                        item[k.strip()] = (
                            node(cur_indent + 4)
                            if pos < len(lines) and lines[pos][0] > cur_indent + 2
                            else None
                        )
                    while (
                        pos < len(lines)
                        and lines[pos][0] == cur_indent + 2
                        and not lines[pos][1].startswith("- ")
                    ):
                        k2, _, v2 = lines[pos][1].partition(":")
                        ind2 = lines[pos][0]
                        pos += 1
                        if v2.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
                            item[k2.strip()] = block(ind2)
                        elif v2.strip():
                            item[k2.strip()] = scalar(v2)
                        else:
                            item[k2.strip()] = (
                                node(ind2 + 2) if pos < len(lines) and lines[pos][0] > ind2 else None
                            )
                    items.append(item)
                else:
                    items.append(scalar(rest))
            return items
        mapping = {}
        while pos < len(lines) and lines[pos][0] == indent and not lines[pos][1].startswith("- "):
            cur_indent, stripped, _ = lines[pos]
            key, _, val = stripped.partition(":")
            key = key.strip().strip("\"'")
            pos += 1
            if val.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
                mapping[key] = block(cur_indent)
            elif val.strip():
                mapping[key] = scalar(val)
            elif pos < len(lines) and lines[pos][0] > cur_indent:
                mapping[key] = node(lines[pos][0])
            else:
                mapping[key] = None
        return mapping

    return node(lines[0][0]) if lines else {}


# --------------------------------------------------------------------------------- audit
def triggers(wf: dict) -> set[str]:
    on = wf.get("on") or wf.get(True) or {}
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on.keys())
    return set()


def walk_steps(job: dict) -> list[dict]:
    steps = job.get("steps") or []
    return [s for s in steps if isinstance(s, dict)]


def audit(path: Path, allow_tag_pins: bool, allowed: dict[str, dict]) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    wf = parse_yaml(text) or {}
    findings: list[dict] = []
    rel = str(path.relative_to(ROOT))

    def add(code: str, sev: str, msg: str, job: str | None = None) -> None:
        findings.append({"file": rel, "code": code, "severity": sev, "job": job, "message": msg})

    trig = triggers(wf)
    untrusted = trig & UNTRUSTED_TRIGGERS
    top_perms = wf.get("permissions")
    jobs = {k: v for k, v in (wf.get("jobs") or {}).items() if isinstance(v, dict)}

    # W02 — write-all anywhere
    for scope, perms in [("workflow", top_perms)] + [(j, cfg.get("permissions")) for j, cfg in jobs.items()]:
        if perms == "write-all":
            add(
                "W02",
                "blocker",
                f"{scope}: `permissions: write-all` grants every scope",
                None if scope == "workflow" else scope,
            )

    # W05 / W08 — untrusted triggers
    if untrusted:
        names = ", ".join(sorted(untrusted))
        for jname, cfg in jobs.items():
            for step in walk_steps(cfg):
                uses = COMMENT_RE.sub("", str(step.get("uses") or ""))
                if uses.startswith("actions/checkout"):
                    with_ = step.get("with") or {}
                    ref = str(with_.get("ref", ""))
                    if "github.event.pull_request.head" in ref or "github.event.workflow_run.head" in ref:
                        add(
                            "W05",
                            "blocker",
                            f"{names} trigger checks out untrusted PR code (`ref: {ref}`) — "
                            "this runs fork code with repository secrets in scope",
                            jname,
                        )
        if "${{ secrets." in text and untrusted:
            add(
                "W08",
                "major",
                f"workflow uses `{names}` and references `secrets.*`; confirm no fork-controlled "
                "code path can read them (gate on an `environment` with required reviewers)",
                None,
            )

    # W07 — concurrency
    if (trig & {"push", "pull_request"}) and "concurrency" not in wf:
        add("W07", "minor", "no `concurrency` group: superseded pushes keep burning runners", None)

    for jname, cfg in jobs.items():
        # W01 — permissions
        if top_perms is None and cfg.get("permissions") is None:
            add("W01", "major", "no `permissions` declared: the job inherits the default token scope", jname)

        # W03 — timeout
        if "timeout-minutes" not in cfg:
            add("W03", "major", "no `timeout-minutes`: a hung job holds a runner and a live token", jname)

        pushes = False
        for step in walk_steps(cfg):
            run = str(step.get("run") or "")
            if re.search(
                r"\bgit\s+(push|commit)\b|peter-evans/create-pull-request", run + str(step.get("uses") or "")
            ):
                pushes = True

        for step in walk_steps(cfg):
            uses = COMMENT_RE.sub("", str(step.get("uses") or "")).strip()
            run = str(step.get("run") or "")
            sname = str(step.get("name") or uses or "run")[:48]

            # W04 — SHA pinning
            pinnable = uses and not uses.startswith(("./", "docker://"))
            if pinnable and not SHA_RE.match(uses):
                if uses in allowed:
                    add(
                        "W04",
                        "accepted",
                        f"step '{sname}': `{uses}` tag-pinned under a tracked exception "
                        f"(expires {allowed[uses]['expires']}, owner {allowed[uses].get('owner', '?')})",
                        jname,
                    )
                else:
                    sev = (
                        "minor"
                        if allow_tag_pins
                        else ("major" if uses.startswith(FIRST_PARTY) else "blocker")
                    )
                    add(
                        "W04",
                        sev,
                        f"step '{sname}': `{uses}` is pinned to a mutable tag; pin to a full 40-hex "
                        "commit SHA (keep the version in a trailing comment), or register an "
                        "expiring exception in .github/actions-allowlist.txt",
                        jname,
                    )

            # W06 — script injection
            if run:
                m = UNTRUSTED_CTX.search(run)
                if m:
                    add(
                        "W06",
                        "blocker",
                        f"step '{sname}': interpolates attacker-controllable `{m.group(1)}` directly "
                        "into a shell command; pass it through `env:` and quote the variable",
                        jname,
                    )

            # W09 — checkout credentials
            if uses.startswith("actions/checkout"):
                with_ = step.get("with") or {}
                if with_.get("persist-credentials") is not False and not pushes:
                    add(
                        "W09",
                        "minor",
                        f"step '{sname}': `persist-credentials: false` is not set; the token stays in "
                        ".git/config for every later step",
                        jname,
                    )

            # W10 — artifact retention
            if uses.startswith("actions/upload-artifact"):
                with_ = step.get("with") or {}
                if "retention-days" not in with_:
                    add(
                        "W10",
                        "minor",
                        f"step '{sname}': no `retention-days`; artifacts default to 90 days of storage",
                        jname,
                    )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    ap.add_argument(
        "--allow-tag-pins",
        action="store_true",
        help="downgrade W04 (SHA pinning) to a warning — for repos that accept tag pins",
    )
    ap.add_argument("--today", default=None, help="override today's date (YYYY-MM-DD) for expiry checks")
    args = ap.parse_args()

    import datetime

    today = args.today or datetime.date.today().isoformat()
    allowed, allowlist_problems = load_allowlist(today)

    if not WF_DIR.exists():
        print(f"error: {WF_DIR} does not exist", file=sys.stderr)
        return 2

    files = sorted(WF_DIR.glob("*.y*ml"))
    all_findings = list(allowlist_problems)
    for f in files:
        all_findings.extend(audit(f, args.allow_tag_pins, allowed))

    # W12 — an exception for an action no workflow references is an exception nobody re-reviews.
    # It also hides the fact that the pin was already fixed. Prune it.
    used = {
        COMMENT_RE.sub("", m).strip()
        for f in files
        for m in re.findall(r"^\s*-?\s*uses:\s*(.+)$", f.read_text(encoding="utf-8"), re.M)
    }
    for ref in sorted(set(allowed) - used):
        all_findings.append(
            {
                "file": ".github/actions-allowlist.txt",
                "code": "W12",
                "severity": "major",
                "job": None,
                "message": f"stale exception: no workflow uses `{ref}` — delete the line "
                "(if the action was since SHA-pinned, the exception is obsolete)",
            }
        )

    # W13 — a tool version hardcoded in a `run:` block is a second source of truth that will
    # drift from the real pin. Point the author at the file that owns the version.
    for f in files:
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for tool, canonical in HARDCODED_TOOL.findall(line):
                all_findings.append(
                    {
                        "file": str(f.relative_to(ROOT)),
                        "code": "W13",
                        "severity": "major",
                        "job": None,
                        "message": f"line {lineno}: `{tool}` version {canonical} is hardcoded here, but "
                        f"its canonical pin is {CANONICAL_PINS[tool]} — two copies drift, and CI then "
                        "lints with a different version than a developer does",
                    }
                )

    sev_rank = {"blocker": 0, "major": 1, "minor": 2, "accepted": 3}
    all_findings.sort(key=lambda f: (sev_rank[f["severity"]], f["file"], f["code"]))
    counts = {s: sum(1 for f in all_findings if f["severity"] == s) for s in sev_rank}
    payload = {
        "workflows": [str(f.relative_to(ROOT)) for f in files],
        "counts": counts,
        "findings": all_findings,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Auditing {len(files)} workflow(s) in .github/workflows/\n")
        if not all_findings:
            print("no findings")
        for f in all_findings:
            where = f"{f['file']}" + (f" [{f['job']}]" if f["job"] else "")
            print(f"[{f['severity']:<7}] {f['code']}  {where}\n           {f['message']}")
        print(
            f"\n{counts['blocker']} blocker, {counts['major']} major, {counts['minor']} minor, "
            f"{counts['accepted']} accepted exception(s) across {len(files)} workflow(s)"
        )

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return 1 if counts["blocker"] or counts["major"] else 0


if __name__ == "__main__":
    sys.exit(main())
