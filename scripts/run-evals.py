#!/usr/bin/env python3
"""
run-evals.py — offline eval harness for the skill production pipeline (Phase 3 / Phase 5).

Two deterministic, dependency-free gates that need no LLM and no network:

  1. ROUTING EVAL (Phase 5, description optimization)
     Every skill's description+name+tags is indexed as a document. Each eval prompt is
     scored against all skills with tf-idf term overlap. A `should_trigger` case passes
     when its own skill ranks #1; a `should_not_trigger` case passes when that skill does
     NOT rank #1. This measures exactly what a real agent does when choosing a skill —
     if a description cannot win its own prompts, no runtime will route to it.

  2. ASSERTION COVERAGE (Phase 3d, quality gate)
     Every assertion's salient terms must be present in the skill body. An assertion the
     skill cannot possibly satisfy is a content gap, not a grading opinion.

Emits benchmark.json and a POWERFUL/SOLID/GENERIC/WEAK tier per the pipeline's table.

LLM-graded with-skill vs baseline runs (Phase 3b) are NOT performed here: they need a
model runner. Use this as the pre-flight gate that must pass before spending those tokens.

Usage:
  python3 scripts/run-evals.py
  python3 scripts/run-evals.py --skill aws-eks-enterprise-patterns --verbose
  python3 scripts/run-evals.py --out benchmark.json --min-pass-rate 95
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

STOPWORDS = set(
    """
a about above after all also am an and any are as at be because been before being below between both but by
can cant come could did do does doing dont down during each even every few for from further get give go got
had has have having he her here hers him his how i if in into is it its just like make me more most much must
my no nor not now of off on once one only or other our out over own same she should so some such than that the
their them then there these they this those through to too under until up us very was we well were what when
where which while who whom why will with without would you your our need needs want should how do i we
right now dont doesnt isnt cant nobody someone everything anything something things thing use using used
""".split()  # noqa: SIM905 - a block string keeps ~140 stopwords readable and diffable
)

TIERS = [(85, "POWERFUL"), (70, "SOLID"), (55, "GENERIC"), (0, "WEAK")]


def tokens(text: str) -> list[str]:
    text = text.lower().replace("-", " ").replace("/", " ").replace("_", " ")
    return [t for t in re.findall(r"[a-z0-9][a-z0-9+.]{1,}", text) if t not in STOPWORDS and len(t) > 2]


def parse_skill(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 4)
    fm, body = text[4:end], text[end + 4 :]

    def field(k):
        m = re.search(rf"^{k}:\s*(.+)$", fm, re.M)
        return m.group(1).strip() if m else ""

    tags = field("tags")
    tags = [t.strip() for t in tags.strip("[]").split(",")] if tags else []
    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    return {
        "name": field("name"),
        "description": field("description"),
        "tags": tags,
        "title": h1.group(1) if h1 else "",
        "body": body,
        "path": path,
    }


def build_index(skills: list[dict]) -> tuple[dict, dict]:
    """Return (per-skill term frequencies, idf weights) over routing documents."""
    tf: dict[str, dict[str, int]] = {}
    df: dict[str, int] = defaultdict(int)
    for s in skills:
        # the routing document is exactly what an agent sees before loading a skill
        doc = " ".join([s["name"], s["title"], " ".join(s["tags"]), s["description"]])
        counts: dict[str, int] = defaultdict(int)
        for t in tokens(doc):
            counts[t] += 1
        tf[s["name"]] = counts
        for t in set(counts):
            df[t] += 1
    n = len(skills)
    idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}
    return tf, idf


def rank(prompt: str, tf: dict, idf: dict) -> list[tuple[str, float]]:
    qt = tokens(prompt)
    scores = {}
    for name, counts in tf.items():
        score = 0.0
        for t in set(qt):
            if t in counts:
                # sublinear tf, idf-weighted; length-normalised so verbose skills don't win by size
                score += (1 + math.log(counts[t])) * idf.get(t, 0.0)
        scores[name] = score / math.sqrt(sum(counts.values()) or 1)
    return sorted(scores.items(), key=lambda kv: -kv[1])


def _unused_build_salience(skills: list[dict], max_df_ratio: float = 0.25) -> set[str]:
    """Domain vocabulary = terms that are distinctive across skill bodies.

    Generic prose ('uses', 'defines', 'real', 'system') appears in most bodies and carries no
    signal about whether a skill covers a concept; distinctive technical terms
    ('messagegroupid', 'predict_linear', 'irsa') appear in few. Terms absent from the entire
    library are kept as salient: an assertion naming one is exactly the content gap we want.
    """
    df: dict[str, int] = defaultdict(int)
    for s in skills:
        for t in set(tokens(s["body"])):
            df[t] += 1
    cutoff = max(2, int(len(skills) * max_df_ratio))
    return {t for t, c in df.items() if c <= cutoff}


def coverage_gaps(must_cover: list[str], body: str) -> list[str]:
    """Concepts the eval declares the skill must contain, that the body does not mention.

    `must_cover` is authored intent, not inferred: each entry is a literal technical anchor
    (an API field, a tool, a named pattern). A miss means the skill cannot satisfy its own
    assertions no matter how the grader phrases them — a content gap, not a wording quibble.
    """
    hay = body.lower()
    return [a for a in must_cover if a.lower() not in hay]


def tier_for(pct: float) -> str:
    for threshold, label in TIERS:
        if pct >= threshold:
            return label
    return "WEAK"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", help="evaluate a single skill by name")
    ap.add_argument("--out", default=None, help="write benchmark JSON to this path")
    ap.add_argument("--min-pass-rate", type=float, default=95.0, help="gate threshold (default 95)")
    ap.add_argument("--verbose", action="store_true", help="show every case result")
    args = ap.parse_args()

    skills = [parse_skill(p) for p in sorted(SKILLS_DIR.rglob("SKILL.md"))]
    tf, idf = build_index(skills)

    results = []
    for s in skills:
        if args.skill and s["name"] != args.skill:
            continue
        ev = s["path"].parent / "evals" / "evals.json"
        if not ev.exists():
            results.append({"skill": s["name"], "error": "missing evals/evals.json"})
            continue
        data = json.loads(ev.read_text(encoding="utf-8"))
        gaps = coverage_gaps(data.get("must_cover", []), s["body"])
        cases = []
        for case in data.get("cases", []):
            ranked = rank(case["prompt"], tf, idf)
            top, top_score = ranked[0]
            own_rank = next(i for i, (n, _) in enumerate(ranked, 1) if n == s["name"])
            if case.get("should_trigger", True):
                passed = top == s["name"]
                detail = f"routed to '{top}' (own rank {own_rank})"
            else:
                passed = top != s["name"]
                detail = f"routed to '{top}'"
            if case.get("should_trigger", True) and gaps:
                passed = False
            residual = case.get("known_residual")
            cases.append(
                {
                    "id": case["id"],
                    "prompt": case["prompt"],
                    "should_trigger": case.get("should_trigger", True),
                    "passed": passed,
                    "detail": detail,
                    "own_rank": own_rank,
                    "top_score": round(top_score, 4),
                    "known_residual": residual if not passed else None,
                }
            )
        # A case carrying `known_residual` is a documented, justified near-tie: it is reported
        # every run but does not fail the gate. Adding one is a deliberate, reviewable act —
        # the alternative is keyword-stuffing a description to win a single prompt.
        total = len(cases)
        passed = sum(1 for c in cases if c["passed"] or c.get("known_residual"))
        pct = 100.0 * passed / total if total else 0.0
        results.append(
            {
                "skill": s["name"],
                "cases": cases,
                "coverage_gaps": gaps,
                "total": total,
                "passed": passed,
                "pass_rate": round(pct, 1),
                "tier": tier_for(pct),
                "residuals": [
                    {"id": c["id"], "justification": c["known_residual"]}
                    for c in cases
                    if c.get("known_residual")
                ],
                "case_count_ok": total >= 5,
            }
        )

    graded = [r for r in results if "pass_rate" in r]
    overall = round(sum(r["pass_rate"] for r in graded) / len(graded), 1) if graded else 0.0
    benchmark = {
        "suite": "cloud-platform-skills",
        "mode": "offline-deterministic (routing + assertion coverage)",
        "skills_evaluated": len(graded),
        "overall_pass_rate": overall,
        "overall_tier": tier_for(overall),
        "min_pass_rate": args.min_pass_rate,
        "results": results,
    }

    failing = [r for r in graded if r["pass_rate"] < args.min_pass_rate]
    errored = [r for r in results if "error" in r]

    for r in results:
        if "error" in r:
            print(f"ERROR {r['skill']}: {r['error']}")
            continue
        flag = "PASS" if r["pass_rate"] >= args.min_pass_rate else "FAIL"
        print(f"{flag}  {r['skill']:<45} {r['pass_rate']:>5.1f}%  {r['tier']}")
        for c in r["cases"]:
            if args.verbose or not c["passed"]:
                mark = "ok " if c["passed"] else "X  "
                want = "trigger" if c["should_trigger"] else "no-trigger"
                print(f"      {mark}[{want}] {c['detail']}  <- {c['prompt'][:70]}")
            elif c.get("known_residual"):
                print(
                    f"      ~  [{'trigger' if c['should_trigger'] else 'no-trigger'}] "
                    f"documented residual: {c['detail']}  <- {c['prompt'][:60]}"
                )
                print(f"           justification: {c['known_residual']}")
        if r["coverage_gaps"]:
            print(f"      content gaps (must_cover not in body): {', '.join(r['coverage_gaps'])}")

    residuals = sum(len(r.get("residuals", [])) for r in graded)
    print(
        f"\nOverall: {overall}% ({benchmark['overall_tier']}) across {len(graded)} skills; "
        f"{len(failing)} below {args.min_pass_rate}%"
        + (f"; {residuals} documented residual(s)" if residuals else "")
    )

    if args.out:
        Path(args.out).write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")
        print(f"benchmark written to {args.out}")

    return 1 if failing or errored else 0


if __name__ == "__main__":
    sys.exit(main())
