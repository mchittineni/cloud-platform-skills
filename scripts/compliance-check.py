#!/usr/bin/env python3
"""
compliance-check.py — Phase 6 compliance gate, run locally with no network and no LLM.

Implements the pipeline's mandatory 8-point inspection as deterministic checks, so it is the
documented fallback when Tessl CLI is unavailable (and a cheap pre-filter when it is not):

  1. No malware, exploit payloads, or destructive commands presented as routine
  2. No hardcoded secrets or credentials
  3. Description accurate and non-surprising (matches what the body actually teaches)
  4. Bundled scripts are stdlib-only with no undeclared dependencies
  5. YAML frontmatter valid (name + description present and well-formed)
  6. File references all resolve
  7. SKILL.md under the 500-line ceiling (or carries a justification marker)
  8. Evals present with test cases and assertions

Scores each skill 0-100 and assigns the pipeline's tier (POWERFUL >=85, SOLID 70-84,
GENERIC 55-69, WEAK <55). Only POWERFUL ships.

Usage:
  python3 scripts/compliance-check.py
  python3 scripts/compliance-check.py --skill aws-eks-enterprise-patterns --verbose
  python3 scripts/compliance-check.py --json --out compliance.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

LINE_CEILING = 500
STDLIB_OK = {
    "argparse",
    "ast",
    "base64",
    "collections",
    "configparser",
    "csv",
    "dataclasses",
    "datetime",
    "decimal",
    "difflib",
    "enum",
    "functools",
    "glob",
    "gzip",
    "hashlib",
    "hmac",
    "html",
    "http",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "pprint",
    "random",
    "re",
    "shlex",
    "shutil",
    "socket",
    "sqlite3",
    "statistics",
    "string",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "time",
    "tomllib",
    "types",
    "typing",
    "unittest",
    "urllib",
    "uuid",
    "warnings",
    "xml",
    "zipfile",
    "zoneinfo",
    "__future__",
}

# Point 1: destructive or offensive patterns that must never appear as unguarded instruction.
DANGEROUS = [
    (r"\brm\s+-rf\s+/(?:\s|$|\*)", "unguarded `rm -rf /`"),
    (r":\(\)\{.*\|:&\s*\};:", "fork bomb"),
    (r"\bmkfs(\.\w+)?\s+/dev/", "filesystem overwrite of a raw device"),
    (r"\bdd\s+if=/dev/(zero|random|urandom)\s+of=/dev/[sh]d", "raw disk destruction via dd"),
    (r"\bcurl\b[^|\n]*\|\s*(sudo\s+)?(ba)?sh\b", "pipe-remote-script-to-shell"),
    (r"\bwget\b[^|\n]*\|\s*(sudo\s+)?(ba)?sh\b", "pipe-remote-script-to-shell"),
    (r"\bchmod\s+(-R\s+)?777\s+/", "world-writable permissions on a system path"),
    (r"\bnc\s+-l.*-e\s*/bin/(ba)?sh", "reverse/bind shell payload"),
    (r"\biptables\s+-F\b.*\n.*-P\s+INPUT\s+ACCEPT", "firewall teardown"),
]

# Point 1b: agent-directed harm. A skill is an instruction an agent executes with the operator's
# credentials, so an injected directive is a higher-severity defect here than any dependency CVE.
AGENT_HIJACK = [
    (
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules|directives)",
        "prompt injection: overrides prior instructions",
    ),
    (
        r"(?i)disregard\s+(the\s+)?(above|previous|prior|system)\s+(instructions|prompt|rules)",
        "prompt injection: disregards prior instructions",
    ),
    (
        r"(?i)(do\s+not|don'?t|never)\s+(tell|inform|mention\s+(this\s+)?to|reveal\s+(this\s+)?to)\s+the\s+(user|operator|human)",
        "instructs the agent to conceal actions from the operator",
    ),
    (
        r"(?i)(without|skip|bypass|suppress)\s+(asking|confirming|the\s+)?(user\s+)?(confirmation|approval|permission|review)",
        "instructs the agent to skip human confirmation",
    ),
    (
        r"(?i)(disable|turn\s+off|ignore)\s+(your\s+)?(safety|guardrail|security)\s+(checks?|rules?|filters?)",
        "instructs the agent to disable safety checks",
    ),
    (r"(?i)--dangerously-skip-permissions|--yolo\b", "invokes an agent permission-bypass flag"),
    (r"(?i)reveal\s+(your\s+)?(system\s+prompt|instructions)", "attempts system-prompt disclosure"),
]

# Exfiltration sinks that no legitimate engineering skill needs to name.
EXFIL_SINKS = r"(webhook\.site|requestbin|pipedream\.net|ngrok\.io|burpcollaborator|oast\.(?:fun|live|site)|interact\.sh|\bbit\.ly/)"
CREDENTIAL_PATHS = (
    r"(~/\.aws/credentials|~/\.ssh/id_[a-z0-9]+|~/\.kube/config|\.git-credentials|~/\.netrc|\.env\b)"
)
NETWORK_SEND = r"(curl\s|wget\s|nc\s|http\.client|requests\.(post|put)|urllib\.request)"

EXFIL = [
    (rf"(?i){EXFIL_SINKS}", "traffic directed to a known exfiltration/collaborator sink"),
    (
        rf"(?i)\b(env|printenv|set)\b[^\n|]*\|[^\n]*{NETWORK_SEND}",
        "pipes the environment (secrets included) to the network",
    ),
    (
        rf"(?i)cat\s+{CREDENTIAL_PATHS}[^\n|]*\|[^\n]*{NETWORK_SEND}",
        "pipes credential material to the network",
    ),
    (
        rf"(?i){NETWORK_SEND}[^\n]*(-d|--data|--data-binary|json=)[^\n]*\$\{{?(AWS_SECRET|AWS_SESSION|GITHUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|VAULT_TOKEN)",
        "posts a credential environment variable to a remote endpoint",
    ),
    (
        rf"(?i)base64[^\n|]*{CREDENTIAL_PATHS}[^\n]*\|[^\n]*{NETWORK_SEND}",
        "encodes then transmits credential material",
    ),
]

JUSTIFIED = re.compile(r"<!--\s*agent-safety-justified:\s*(.+?)\s*-->")

# Point 2: credential shapes. Placeholders and documented examples are excluded below.
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"ASIA[0-9A-Z]{16}", "AWS temporary access key id"),
    (r"(?i)aws_secret_access_key\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{40}", "AWS secret access key"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "GitHub token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"sk-[A-Za-z0-9]{32,}", "API secret key"),
    (r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "private key material"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT with payload"),
    (r"(?i)(password|passwd|secret|token)\s*[:=]\s*[\"'][^\"'{}$<>\s]{12,}[\"']", "literal credential"),
]
PLACEHOLDER = re.compile(
    r"(?i)(example|sample|placeholder|redacted|changeme|xxx+|\.\.\.|your[-_]|<[^>]+>|\$\{|\{\{|"
    r"AKIAIOSFODNN7EXAMPLE|test-token|dummy|fake|REPLACE)"
)


def parse(path: Path) -> tuple[dict, str, str]:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 4)
    fm = text[4:end] if text.startswith("---\n") and end != -1 else ""
    body = text[end + 4 :] if end != -1 else text
    meta = {}
    for line in fm.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body, text


def code_blocks(body: str) -> list[tuple[str, str]]:
    return re.findall(r"```(\w*)\n(.*?)```", body, re.S)


def check_skill(path: Path) -> dict:
    meta, body, text = parse(path)
    skill_dir = path.parent
    findings: list[dict] = []

    def add(point: int, severity: str, msg: str) -> None:
        findings.append({"point": point, "severity": severity, "message": msg})

    # 1 — malware / destructive content
    for pattern, label in DANGEROUS:
        for m in re.finditer(pattern, text, re.M):
            line = text[: m.start()].count("\n") + 1
            add(1, "blocker", f"line {line}: {label}")

    # 1b — agent-directed harm: hijacking directives and exfiltration paths.
    # A `<!-- agent-safety-justified: reason -->` marker downgrades a hit to a reviewed note,
    # for the rare skill that must quote an attack string to teach detection.
    justification = JUSTIFIED.search(text)
    for pattern, label in AGENT_HIJACK + EXFIL:
        for m in re.finditer(pattern, text):
            line = text[: m.start()].count("\n") + 1
            if justification:
                add(1, "minor", f"line {line}: {label} — justified: {justification.group(1)[:80]}")
            else:
                add(1, "blocker", f"line {line}: agent safety — {label}")

    # 2 — hardcoded secrets
    for pattern, label in SECRET_PATTERNS:
        for m in re.finditer(pattern, text):
            snippet = m.group(0)
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            full_line = text[line_start : line_end if line_end != -1 else len(text)]
            if PLACEHOLDER.search(full_line):
                continue
            line = text[: m.start()].count("\n") + 1
            add(2, "blocker", f"line {line}: possible {label} ({snippet[:12]}...)")

    # 3 — description accuracy: the tools it advertises must appear in the body
    desc = meta.get("description", "")
    if not desc:
        add(3, "blocker", "no description to verify")
    else:
        advertised = re.findall(r"\b(?:[A-Z][a-zA-Z0-9]+(?:CD|DB)?|k6|eBPF|OIDC|SBOM|mTLS)\b", desc)
        noise = {
            "Use",
            "When",
            "Cloud",
            "The",
            "This",
            "Skill",
            "Kubernetes",
            "Service",
            "Services",
            "Design",
            "Platform",
            "Engineering",
            "Security",
            "Management",
            "Policy",
            "Policies",
            "Git",
            "CI",
            "IAM",
            "API",
            "APIs",
            "SLO",
            "SLA",
            "SLI",
            "DR",
            "RPO",
            "RTO",
            "HA",
            "AWS",
            "Azure",
            "GCP",
            "Google",
            "Microsoft",
            "Linux",
            "Ubuntu",
            "RHEL",
            "Postgres",
            "MySQL",
            "Oracle",
            "SQL",
            "Server",
            "Black",
            "Friday",
            "Framework",
            "Terraform",
            "Fleet",
            "Secret",
            "Secrets",
            "Actions",
            "Developer",
            "Developers",
        }
        hay = body.lower()
        unbacked = [t for t in dict.fromkeys(advertised) if t not in noise and t.lower() not in hay]
        if len(unbacked) > 2:
            add(3, "major", f"description advertises what the body never covers: {', '.join(unbacked[:6])}")
        elif unbacked:
            add(3, "minor", f"description mentions {', '.join(unbacked)} but the body does not")

    # 4 — bundled scripts stdlib-only
    for py in sorted(skill_dir.rglob("*.py")):
        src = py.read_text(encoding="utf-8")
        mods = set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w]*)", src, re.M))
        local = {p.stem for p in py.parent.rglob("*.py")}
        external = sorted(m for m in mods if m not in STDLIB_OK and m not in local)
        if external:
            add(4, "blocker", f"{py.relative_to(skill_dir)} imports non-stdlib: {', '.join(external)}")

    # 5 — frontmatter validity
    if not text.startswith("---\n"):
        add(5, "blocker", "missing YAML frontmatter")
    for required in ("name", "description"):
        if required not in meta:
            add(5, "blocker", f"frontmatter missing '{required}'")
    if meta.get("name") and meta["name"] != skill_dir.name:
        add(5, "blocker", f"frontmatter name '{meta['name']}' != directory '{skill_dir.name}'")

    # 6 — file references resolve
    for ref in set(
        re.findall(r"(?:\]\(|`)((?:\./)?(?:scripts|references|assets|evals|agents|commands)/[\w./-]+)", body)
    ):
        if not (skill_dir / ref.lstrip("./")).exists():
            add(6, "major", f"broken bundled reference: {ref}")
    for link in set(re.findall(r"\]\((?!https?://|#)([^)]+)\)", body)):
        target = (skill_dir / link).resolve()
        if not target.exists() and not link.startswith("mailto:"):
            add(6, "minor", f"broken relative link: {link}")

    # 7 — line ceiling
    lines = len(text.splitlines())
    if lines > LINE_CEILING and "<!-- line-budget-justified:" not in text:
        add(7, "major", f"{lines} lines exceeds the {LINE_CEILING}-line ceiling without justification")

    # 8 — evals present and meaningful
    ev = skill_dir / "evals" / "evals.json"
    if not ev.exists():
        add(8, "blocker", "no evals/evals.json")
    else:
        try:
            data = json.loads(ev.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            add(8, "blocker", f"evals.json is not valid JSON: {e}")
            data = {}
        cases = data.get("cases", [])
        pos = [c for c in cases if c.get("should_trigger", True)]
        neg = [c for c in cases if not c.get("should_trigger", True)]
        if len(pos) < 2:
            add(8, "blocker", f"only {len(pos)} should-trigger case(s); pipeline requires 2-3+")
        if not neg:
            add(8, "major", "no should-not-trigger cases; trigger precision is untested")
        if not any(c.get("assertions") for c in pos):
            add(8, "blocker", "no assertions on any should-trigger case")
        if not data.get("must_cover"):
            add(8, "minor", "no must_cover anchors; content coverage cannot be gated")

    weights = {"blocker": 25, "major": 8, "minor": 3}
    score = max(0, 100 - sum(weights[f["severity"]] for f in findings))
    tier = "POWERFUL" if score >= 85 else "SOLID" if score >= 70 else "GENERIC" if score >= 55 else "WEAK"
    return {
        "skill": skill_dir.name,
        "path": str(path.relative_to(ROOT)),
        "score": score,
        "tier": tier,
        "findings": findings,
        "points_failed": sorted({f["point"] for f in findings}),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", help="check a single skill by directory name")
    ap.add_argument("--min-score", type=float, default=85.0, help="gate threshold (default 85 = POWERFUL)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--out", help="write the JSON report to this path")
    ap.add_argument("--verbose", action="store_true", help="list minor findings too")
    args = ap.parse_args()

    paths = sorted(SKILLS.rglob("SKILL.md"))
    if args.skill:
        paths = [p for p in paths if p.parent.name == args.skill]
        if not paths:
            print(f"error: no skill named '{args.skill}'", file=sys.stderr)
            return 2

    reports = [check_skill(p) for p in paths]
    failing = [r for r in reports if r["score"] < args.min_score]
    blockers = sum(1 for r in reports for f in r["findings"] if f["severity"] == "blocker")
    payload = {
        "gate": "8-point compliance (Tessl-unavailable fallback)",
        "min_score": args.min_score,
        "skills": len(reports),
        "passing": len(reports) - len(failing),
        "blockers": blockers,
        "average_score": round(sum(r["score"] for r in reports) / len(reports), 1) if reports else 0,
        "reports": reports,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for r in reports:
            flag = "PASS" if r["score"] >= args.min_score else "FAIL"
            print(f"{flag}  {r['skill']:<45} {r['score']:>3}  {r['tier']}")
            for f in r["findings"]:
                if f["severity"] == "minor" and not args.verbose:
                    continue
                print(f"      [{f['severity']}] point {f['point']}: {f['message']}")
        print(
            f"\n{payload['passing']}/{payload['skills']} at or above {args.min_score} "
            f"(avg {payload['average_score']}); {blockers} blocker finding(s)"
        )

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
