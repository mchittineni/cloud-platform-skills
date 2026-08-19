# Changelog

All notable changes to this repository. Versioning follows `CONTRIBUTING.md`.

## [1.0.0] - 2026-08-19

First released version. Everything below describes the state of the library at 1.0.0 relative to
the unreleased pre-1.0 working tree: all 43 skills brought onto the mandatory skill production
pipeline, cross-runtime packaging rebuilt around a single source of truth, and the repository's own
CI, security and release machinery built to the same standard the skills teach.

### Added

#### Quality gates (stdlib-only Python 3.10+, offline, no LLM required)

- `scripts/run-evals.py` — offline, deterministic eval harness (pipeline Phase 3/5). Indexes every
  skill's routing document and scores each eval prompt tf-idf against all 43 skills, so a
  should-trigger case passes only when its own skill ranks #1 and a should-not-trigger case passes
  only when it does not. Also gates `must_cover` content anchors. Emits `benchmark.json` with a
  per-skill tier.
- `scripts/compliance-check.py` — the mandatory 8-point compliance inspection as deterministic
  local checks (the documented Tessl-unavailable fallback): destructive-command and credential
  scanning, **agent-directed harm** detection, description-accuracy verification, stdlib-only script
  enforcement, frontmatter validity, reference resolution, line ceiling, and eval completeness.
  Scores 0–100 and assigns the pipeline's quality tier.
- `scripts/audit-workflows.py` — GitHub Actions security gate with a stdlib YAML-subset parser
  (PyYAML is not stdlib). Checks W01–W13: least-privilege `permissions`, no `write-all`, per-job
  `timeout-minutes`, SHA-pinned actions, untrusted-trigger checkout of fork code,
  `${{ github.event.* }}` script injection inside `run:`, `concurrency` groups, secrets reachable
  from fork PRs, `persist-credentials: false`, artifact `retention-days`, expiry and ownership of
  pin exceptions (W11), and **stale** pin exceptions no workflow references any more (W12) — an
  exception nobody re-reviews is how a register rots.
- `scripts/sync-all.py` — single generator for every runtime target, with `--check` for CI.
- `scripts/generate-docs.py` — builds the documentation site sources and `mkdocs.yml` from
  `skills/`, with `--check` freshness verification.
- `scripts/check-release.py` — release gate: verifies the tag matches every domain `plugin.json`,
  that manifests carry only the strict field set, that `marketplace.json` and the plugins on disk
  agree, and that `CHANGELOG.md` has a matching section. Also extracts release notes, writes a
  skill manifest (name, level, sha256, eval count), and bumps versions mechanically.
- Strict frontmatter validation in `scripts/validate-skills.py`: any unquoted plain scalar
  containing `": "` or `" #"` is now an error, implemented stdlib-only so the gate keeps its
  no-dependency contract, plus an optional PyYAML cross-check that runs automatically when the
  library happens to be installed. Regression-tested by reintroducing the bug and confirming the
  gate fails.
- `known_residual` support in the eval harness and schema: a failing case may carry a written
  justification so a defensible near-tie is reported on every run without silently lowering the
  gate — the auditable alternative to overfitting a description.

#### Skill content

- `evals/evals.json` for all 43 skills — 3 should-trigger + 2 should-not-trigger cases in real user
  phrasing, grounded assertions, and `must_cover` anchors. 215 cases total.
- `## When to Use This Skill` routing block in all 43 skills: explicit **Triggers** plus **Route
  elsewhere** pointers that cross-link the library so an agent can tell when _not_ to use a skill.
- 44 new expert sections closing gaps the evals and compliance gate exposed, including: Ansible
  role architecture and CIS control tagging; Flyway versioned migrations and Atlas declarative
  schemas; DORA anti-gaming guardrails; GitLab CI parity for the reference pipeline; matrix and
  lockfile cache strategy; probe separation (startup vs liveness vs readiness) and Helm release
  rollback; percentile interpretation, arrival-rate scenarios and Locust; `flock` single-instance
  enforcement and operational CLI ergonomics; restore-drill protocol; ArgoCD sync waves and the
  Flux v2 equivalent; Flagger with Istio traffic shifting; Terragrunt CI policy gate; CSPM finding
  triage, least-privilege measurement and an expiring exception register; Falco macros/lists/
  exceptions tuning; Snyk gating alongside Trivy; false-positive management; workload-identity
  patterns and credential revocation; Scribe discipline and role handoff; node_exporter deployment
  and I/O-wait alerting; good-events/valid-events SLI definition and the error-budget freeze
  policy; AWS cross-account trust with `ExternalId`, and evidence-driven scope-down of
  `AdministratorAccess`; KEDA event-driven autoscaling; AKS CNI Overlay and private clusters, plus
  Key Vault access with no stored secret; Azure management-group hierarchy, Private DNS zone
  linkage and CAF alignment; GKE namespace tenancy controls; Istio default-deny authorization and
  outlier detection; Gateway API vs Kong selection; graceful-shutdown timing and correlation IDs;
  DLQ redrive, idempotency and FIFO `MessageGroupId` ordering; showback/chargeback and cost-spike
  triage; commitment instrument comparison (Savings Plans, RIs, CUDs); GCP keyless CI via Workload
  Identity Federation and BigQuery cost/governance controls; TechDocs; GitFlow selection criteria.

#### Cross-runtime packaging

- `AGENTS.md` (root and `.agents/rules/`) — open AGENTS.md standard for Codex, OpenClaw, Cursor,
  Amp, Jules and the Copilot coding agent.
- `CLAUDE.md` — Claude Code entrypoint with routing index and the gate commands.
- `.claude/skills/<name>/` — native Claude Code skill discovery with progressive disclosure.
- Plugin packaging: strict-format `plugin.json` per domain plus `.claude-plugin/marketplace.json`.
- `scripts/gemini-install.sh` — Gemini CLI / Antigravity installer, workspace or global.
- `templates/skill-template/` (SKILL.md, evals, scripts/references/assets guidance) and
  `templates/eval-schema.json`.

#### CI, security and governance

- `.github/workflows/skills-ci.yml` — all gates on a Python 3.10/3.13 matrix, plus shellcheck.
- `.github/workflows/security.yml` — skill content & agent-safety scan, gitleaks (full history on a
  weekly schedule), CodeQL for the Python tooling, and dependency review on PRs.
- `.github/workflows/release.yml` — tag-triggered release: version consistency, all gates, a
  90-day release-evidence artifact, and `gh release create --verify-tag`. `contents: write` is
  scoped to the publish job only.
- `.github/actions-allowlist.txt` — owned, **expiring** exception register for actions that are
  tag-pinned rather than SHA-pinned. An entry without a valid `expires=` and `owner=`, or past its
  expiry, is a blocker. This applies principle 3 of this library to the repository itself.
- Agent-safety detection in `scripts/compliance-check.py` (compliance point 1): prompt-injection
  directives ("ignore previous instructions", concealment from the operator, confirmation bypass,
  safety-check disabling, permission-bypass flags) and exfiltration paths (known collaborator
  sinks, `env | curl`, credential files piped to the network, credential env vars posted to a
  remote endpoint, base64-then-transmit). A `<!-- agent-safety-justified: … -->` marker downgrades
  a hit for the rare skill that must quote an attack string to teach detection.
- `SECURITY.md` — documents the threat model that actually applies to a skills repository: the
  highest-severity risk is a malicious instruction an agent executes with the operator's
  credentials, ranked above dependency CVEs, with the consumer trust boundary spelled out.
- `CONTRIBUTING.md` — the short contributor path, plus two normative companions:
  **`SKILL_PIPELINE.md`** (the 9-phase production pipeline: dependencies and documented fallbacks,
  iteration limits, per-phase commands, the gate suite with its blocking thresholds, quality tiers,
  versioning, rollback, and a copyable per-skill checklist) and **`SKILL-AUTHORING-STANDARD.md`**
  (the content standard: frontmatter contract, how to write a routing description, required body
  structure, agent-safety rules, eval and `must_cover` authoring, bundled-asset rules, and a review
  checklist — with every rule marked as machine-gated or advisory).
- Lint tooling: `.markdownlint-cli2.jsonc`, `.prettierrc.json`, `.prettierignore`, `pyproject.toml`
  (ruff, mypy, and reserved pytest/coverage config; deliberately **no** `[project]` table, since
  this repository is not a distributable package), and `package.json` pinning
  `markdownlint-cli2@0.14.0` and `prettier@3.3.3`. Markdown belongs to markdownlint and JSON/YAML to
  prettier — the two never overlap, and both skip generated trees. A `lint` job was added to
  `skills-ci.yml` and `make lint` / `make lint-md-fix` / `make format` targets to the Makefile.
- `CODE_OF_CONDUCT.md`, `.gitignore`, `.gitattributes` (generated trees marked
  `linguist-generated`), `.editorconfig`, `.github/dependabot.yml` (github-actions + pip),
  `.github/CODEOWNERS`, `.github/pull_request_template.md` with an agent-safety checklist, three
  issue-form templates, `.gitleaks.toml` tuned so documentation placeholders do not drown real
  detections, `.pre-commit-config.yaml` wiring every gate as a hook, `Makefile`, `STORE.md`.

### Changed

- Rewrote all 43 descriptions as routing decisions: third person, concrete tooling named, explicit
  `Use when …` triggers in the words users actually type (symptoms such as "No space left on
  device", "playbook reports changed every run", "the bill jumped 40%"), and seniority moved out of
  the description into `level`. Routing pass rate: **41.6% → 100%**.
- `scripts/validate-skills.py` rewritten from a frontmatter presence check into real quality gates:
  name/directory agreement, description length and trigger enforcement, seniority-leak and
  second-person detection, tag and runtime vocabulary, single-H1 and routing-block structure, line
  budget, cross-skill reference resolution, duplicate-name detection, `--check-sync`, `--strict`,
  `--json`.
- `.cursor/rules/` restructured from nine always-applied files containing full skill bodies
  (~940 lines each) into one compact always-applied routing index plus 43 per-skill rules with
  `alwaysApply: false`, so Cursor fetches a skill on request instead of injecting the library.
- `.github/copilot-instructions.md` rebuilt as principles plus routing index.
- `export-to-claude.sh`, `export-to-cursor.sh`, `export-to-antigravity.sh` are now thin wrappers
  over `scripts/sync-all.py`, keeping the documented entrypoints working.
- `.github/workflows/deploy-skills.yml`: added a `gates` job so documentation never publishes for a
  library failing its own checks, plus `timeout-minutes`, `persist-credentials: false`, and a
  pinned `pip install -r requirements-dev.txt` instead of an unpinned install.
- `agents/cs-skill-author.md` and `commands/cs-write-a-skill.md` now carry the required frontmatter
  and the pipeline's agent/command section structure.
- **Numeric prefixes dropped from the skill domain directories and plugin names.**
  `skills/01-devops-core/` … `skills/08-finops-cloud-economics/` became `skills/devops-core/` …
  `skills/finops-cloud-economics/`; `productivity` was already unprefixed. The prefixes were not
  load-bearing: both `scripts/sync-all.py` and `scripts/generate-docs.py` render domains by
  iterating `DOMAIN_TITLES` in insertion order, never by sorting directory names, so the curated
  DevOps → Security → SRE → Cloud → Platform → FinOps sequence in the README index, the docs nav
  and `marketplace.json` is unchanged. The plugin name is what a user types, so anyone who
  installed from the pre-1.0 tree reinstalls under the flat name:

  ```bash
  /plugin uninstall 04-cloud-aws     # pre-1.0 name
  /plugin install cloud-aws@cloud-platform-skills
  ```

- `INSTALLATION.md` and `STORE.md` per-plugin skill counts corrected — both still carried the
  pre-1.0 totals for `devsecops-and-secops` (5, actually 9) and `sre-slo-sla-observability`
  (4, actually 5).

### Removed

- `.claude/project-instructions.md` — a generated monolith concatenating all 38 skill bodies into
  always-on context, superseded by `.claude/skills/` plus `CLAUDE.md`. Claude Code never read the
  file, and bulk-loading defeats progressive disclosure.

### Fixed

- **36 of 38 skills shipped frontmatter that a real YAML parser rejects.** Descriptions written as
  `description: Enterprise AWS EKS architecture: VPC CNI prefix delegation…` are invalid YAML — an
  unquoted plain scalar containing `": "` is a _mapping_, not a string, so `yaml.safe_load` raises
  and any runtime using a real YAML library cannot load the skill at all. Every gate passed anyway
  because all four in-repo parsers are hand-rolled and tolerant of it: the artifact was broken while
  the gates read green. Surfaced by cross-checking with an external validator. All descriptions are
  now double-quoted, `scripts/sync-all.py` quotes generated `.mdc` frontmatter through a new
  `yaml_quote()` helper, and **153/153 frontmatter blocks** across `skills/`, both mirrors and the
  Cursor rules now parse under strict YAML.
- 15 skills contained unlabelled code fences (directory trees, ASCII diagrams, formulas); all are
  now tagged `text`, satisfying the `MD040` rule configured for markdownlint.
- 4 skills had no anti-pattern content at all (`cloud-security-posture-cspm-cis`,
  `prometheus-grafana-otel-tracing`, `sli-slo-error-budget-design`,
  `internal-developer-portal-backstage`), violating the repository's own authoring standard. Each
  gained a substantive anti-pattern table — metric gaming, cardinality blowups, unreachable SLO
  targets, catalog rot, and the failure each causes in production.
- `write-a-skill`'s three bundled scripts were rewritten. They had no `argparse` and therefore no
  `--help`, exited `0` on a usage error, and — worst — `skill_review_checklist_runner.py` imported
  its sibling module with no path handling, so it **crashed whenever it was run from the repository
  root**, which is exactly how the documentation says to run it. All three now use argparse, support
  `--json`, `--recursive` and `--demo`, return 0/1/2, resolve sibling imports independent of the
  working directory, and check the current standard (strict-YAML safety, routing block, evals
  presence) rather than a stale one.
- Two false positives found in the rewritten tooling during its own regression tests: `\b(i)\b`
  matched the "I" in "I/O wait" (and `\b(us)\b` would match `us-east-1`), and the fence-language
  check counted closing ``` markers as unlabelled. Both fixed and covered by round-trip tests.
- Descriptions advertising tooling the body never covered (Locust, Flux v2, GitLab CI, ScoutSuite,
  Snyk, Atlas, OpenTofu, Flagger/Istio, Kong, TechDocs, CUDs, BigQuery, keyless GitHub Actions to
  GCP, Key Vault, CAF, CIS, GitFlow, `AdministratorAccess` scope-down) — each is now genuinely
  covered rather than trimmed from the description. Compliance average: 98.2 → 100.0.
- **GitHub Pages published the wrong directory.** `deploy-skills.yml` uploaded `path: docs`, but
  `mkdocs build` renders into `site/` — the deploy would have published raw markdown sources
  instead of the built site. Now uploads `site`.
- **Broken Pages pipeline.** `deploy-skills.yml` referenced `scripts/generate-docs.py`,
  `mkdocs.yml` and `requirements-dev.txt`; none existed, so documentation deployment could never
  have succeeded. All three now exist and are freshness-checked in CI.
- `enterprise-iac-governance-terragrunt` had no best-practice/anti-pattern section; added a CI
  policy gate and a governance do/don't matrix.
- Code-fence bug in the rewritten validator that read `#` shell comments as markdown H1 headings.
- `audit-workflows.py` initially read SHA pins carrying a trailing `# v7.0.1` version comment as
  mutable tags; comments are now stripped before pin matching.

### Gate results

| Gate | Result |
| --- | --- |
| `validate-skills.py --check-sync --strict` | 43 passed, 0 failed, 0 warnings |
| `compliance-check.py` | 43/43 POWERFUL, average **100.0**, 0 blockers |
| `run-evals.py --min-pass-rate 95` | overall **100.0%** (POWERFUL), 2 documented residuals |
| `audit-workflows.py` | 0 blocker, 0 major, 0 minor across 4 workflows |
| `sync-all.py --check` | all generated targets in sync |
| `generate-docs.py --check` | documentation site in sync |
| `check-release.py --version 1.0.0` | tag, 9 plugin manifests, marketplace.json and CHANGELOG agree |

### Reviewed and rejected

An external skill validator (`engineering-advanced-skills:skill-tester`) was run over all 38 skills.
Its structural findings were assessed and deliberately **not** adopted, because they encode a
different skill template:

| Finding | Why rejected |
| --- | --- |
| `README.md missing` (38×) | A per-skill README duplicating `SKILL.md` is drift waiting to happen; the human-facing view is the generated docs site |
| `SKILL.md < 100 lines` (25×) | Directly contradicts progressive disclosure — and the tester's own scope note says not to pad a skill to hit a tier minimum |
| Missing `Name`/`Tier`/`Category`/`Author` frontmatter (38×) | This library's schema is `name`/`description`/`level`/`tags`/`compatible_runtimes`, and it is gated |
| Missing `Features`/`Usage`/`Examples` sections (38×) | This library's structure is a routing block, numbered artifact sections, and anti-patterns |
| `scripts/ directory missing` (37×) | Most skills teach a decision, not a tool; an empty `scripts/` directory is noise |
| `external imports` in the checklist runner | Local sibling modules, not third-party packages — the tester's import analysis does not distinguish them |

Its **frontmatter and script findings were real and are fixed above** — which is the reason to run a
foreign validator at all: it does not share your blind spots.

### Lint and static analysis — executed and green

All three linters were installed and run for the first time, every finding was fixed, and the CI
`lint` job was flipped from `continue-on-error: true` to **blocking**:

| Tool | Findings | Result |
| --- | --- | --- |
| `ruff check` (0.16.3) | 14 → 0 | 10 auto-fixed, 3 hand-fixed, 1 suppressed with a recorded reason |
| `ruff format` | 7 files reformatted | clean |
| `markdownlint-cli2` (0.23.2) | 195 → 0 over 57 files | clean |
| `prettier` (3.9.6) | 6 files reformatted | clean |
| `detect-secrets` (1.5.0, 27 plugins) | 0 candidate secrets | `.secrets.baseline` committed |

Real defects the linters found, as opposed to formatting:

- **`B023` in `scripts/check-release.py`** — a closure defined inside a loop captured the loop
  variable `fm` by late binding. It happened to work because the closure was invoked in the same
  iteration, but it is a bug waiting for the first refactor that defers the call. Hoisted to a
  module-level `_field(frontmatter, key)`.
- **`F841` in `scripts/run-evals.py`** — dead local `by_name`, left over from an earlier revision.
- **`B033` in `scripts/compliance-check.py`** — `"Use"` appeared twice in the description-noise set.
- Two configuration errors of my own making, both of which silenced or inverted a rule:
  `MD048` was set to `"fenced"`, which is not a valid value (`backtick`/`tilde`/`consistent` are) —
  so the rule fired on all 163 fences in the repository; and `MD049` was set to `asterisk` while the
  authored content consistently uses `_italic_` (32 vs 6), so the config was fighting the content
  rather than describing it.
- Genuine markdown defects: 9 unlabelled fences outside `skills/`, 7 emphasis-as-heading paragraphs
  promoted to real headings, 7 angle-bracket placeholders in the skill template that markdown parsed
  as HTML tags (now backticked), a heading-level jump, and a numbered list interrupted by a fence in
  `gcp-gke-autopilot-multi-tenant` that silently restarted at 1 in the rendered output.
- `MD041` is disabled **in-file** for the PR template with the reason stated, rather than by adding
  the file to a global ignore list — a PR template is a body fragment, and every other rule stays
  enforced on it.

`package-lock.json` is now committed, pinning the lint toolchain, and is excluded from prettier
(npm owns its formatting).

**Table column style (`MD060`).** markdownlint-cli2 0.23.2 (markdownlint 0.41.1) adds
`MD060/table-column-style`, which 0.14.0 did not have. Our tables satisfied _no_ supported style:
content rows were `compact` (single-space padding) while delimiter rows were `tight` (`|---|---|`),
so the rule reported 19 violations that `--fix` could not resolve. Fixed by normalising 41 delimiter
rows to the compact form (`| --- | --- |`) and setting `"MD060": { "style": "compact" }` explicitly.
`aligned` was rejected: the skill index tables carry 300-character "Load when" cells, so alignment
would pad every row of every table to that width — enormous diffs that re-break on each edit.
`scripts/sync-all.py` and `scripts/generate-docs.py` now emit compact delimiters too, so regenerated
tables match the linted style.

**Lint tool versions now have a single source of truth.** `package.json` pinned
markdownlint-cli2 0.23.2 / prettier 3.9.6 while the Makefile and CI workflow hardcoded
`npx --yes markdownlint-cli2@0.14.0` / `prettier@3.3.3` — so a locally green run proved nothing
about CI, and the newer version ships rules the older one lacks. Both runners now do `npm ci` and
call the `package.json` scripts (`lint:check`, `format:check`, `fix`), which makes drift
structurally impossible. A `make fix` target was added to match `npm run fix`.

**Every third-party and tool version is pinned to the current release, and each pin is verified.**
Every `uses:` SHA in every workflow was resolved against the tag its comment claims. Two
inconsistencies surfaced:

- **`github/codeql-action` was pinned to a retired major.** The comment claimed `v2.26.3`, but the
  SHA (`c16c0f3f`) did not match that tag at all — so the pin documented one version and ran
  another. CodeQL Action v2 no longer receives updates. Repinned to **v4.37.7**
  (`ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd`), the current release, for both `init` and `analyze`.
- **`koalaman/shellcheck-precommit` was pinned to `v0.11.0`, which does not exist upstream** — the
  newest tag is `v0.9.0`. `pre-commit run` cannot resolve a non-existent rev, so that hook could
  never have run. Corrected to `v0.9.0`.

The other nine actions, the npm lint toolchain, and the docs toolchain were each confirmed to be at
the latest published release with a SHA matching its tag comment.

**`ruff` now has one pin, and the CI lint job actually installs its toolchain.** The workflow's
`RUFF_VERSION` said `0.16.3` while the Makefile said `0.6.9` — the same drift class as the
markdownlint one above, one release later. Worse, the `lint` job called `npm run lint:check` with no
preceding `npm ci` (so markdownlint was not installed) and had silently lost the prettier
`format:check` step. Both are fixed structurally: the job now runs **`make lint`**, so the Makefile
is the single source of the `ruff` pin, `package.json` the single source of the node pins, `npm ci`
always runs, and a laptop and a CI runner lint with byte-identical versions. `scripts/audit-workflows.py`
gained **W13**, which fails any workflow that hardcodes a tool version that already has a canonical
pin elsewhere — regression-tested by reintroducing both old pins (2 findings, correct lines and
tools) and removing them again.

**`make lint-py` installs into a repo-local `.venv-lint`, not the system interpreter.** On
Homebrew and Debian Pythons, PEP 668 refuses a bare `pip install`, and `--break-system-packages` is
not something a lint target should do to a developer's machine — so `make lint` was unrunnable
locally, which is how the ruff pin drifted unnoticed in the first place. The venv is gitignored and
excluded from prettier and markdownlint. `make fix` now also runs `ruff check --fix` + `ruff format`,
and a `make format-py` target was added.

**Upgrading to ruff 0.16.3 changed real output, not just the version string.** It reports `SIM905`
on the stopword block string in `run-evals.py` (suppressed with `# noqa: SIM905` and a reason — a
list literal of ~140 quoted words is strictly worse to maintain), and its formatter rewrites nested
f-string quotes in three scripts. Because the gates must run on Python 3.10, every `.py` in the
repository was re-parsed with `ast.parse(..., feature_version=(3, 10))` after formatting: all pass,
so the rewritten quotes are inside triple-quoted f-strings where they are legal pre-3.12.

**Two gaps in keeping versions current, now closed.** `.github/dependabot.yml` covered
github-actions and pip but **not npm**, so the lint toolchain — the one dependency tree with a
lockfile — was the only thing Dependabot could not bump; an `npm` ecosystem entry was added, grouped
as `lint-toolchain`. And `.github/actions-allowlist.txt` was referenced by `audit-workflows.py`
(W11/W12), `CONTRIBUTING.md` and `SKILL_PIPELINE.md` but was absent from disk; it is restored as a
documented, deliberately **empty** register stating the required four-field format.

**`requirements-dev.txt` no longer pins `mkdocs-redirects`.** `mkdocs.yml` loads only the `search`
plugin, so the pin was dead weight in the docs build that Dependabot would keep raising PRs against.

**The generated agent entrypoints carried a stray quote on 36 of 38 index rows.** `CLAUDE.md`,
`AGENTS.md`, `.agents/rules/AGENTS.md` and `.github/copilot-instructions.md` each rendered
`... found afterwards." |` — the closing quote of the source YAML scalar, leaked into the prose of
the table every agent runtime reads on startup. Cause: `read_skill()` in `sync-all.py` returned the
raw frontmatter scalar, so quoting that is _syntax_ became _content_ once descriptions were
double-quoted. Fixed centrally by unquoting in the one place scalars are read (the `.mdc` generator
re-quotes correctly via `yaml_quote()`, so the round-trip is intact).

`sync-all.py --check` could never have caught this: it byte-compares a file against what the
generator produces, which proves the output is _fresh_, not that it is _correct_. `validate-skills.py
--check-sync` now inspects the rendered result of all six index surfaces and fails a row ending in a
stray YAML quote — regression-tested by disabling the unquoting (144 findings across 4 files, then
clean).

**`README.md`'s index can no longer drift from the skills it describes.** The README index is
authored, not generated, so a description or level change could leave the repository's front door
misrouting humans while every gate stayed green. `validate-skills.py --check-sync` now checks each
README row against the frontmatter it describes — name resolves to a real skill, level matches, and
the "Load when" cell is the trigger clause verbatim — plus fails on a skill with no row at all.
Regression-tested by perturbing one row (2 findings: level and text).

**`INSTALLATION.md` existed as a zero-byte file.** It is now the per-runtime install reference:
requirements, Claude Code via marketplace _and_ clone, Gemini/Antigravity, Codex/OpenClaw/Amp/Jules,
Cursor's always-on-index plus on-request-skills split, Copilot, three verification prompts with the
skill each should load, correct use of progressive disclosure, contributor setup, and uninstall. Every
command was checked against the script it invokes — the first draft claimed a `--global` flag on
`export-to-claude.sh` that does not exist, and put the Gemini global install in `~/.agents` when
`gemini-install.sh` uses `~/.gemini/skills`.

### Documentation brought up to date with the tooling

- **`README.md`** — `make lint` in the gate block, a linter row in the results table, a **Toolchain**
  table naming every pinned version and its single home, the supply-chain paragraph (verified SHA
  pins, expiring exceptions, W13), and `INSTALLATION.md` linked from both the runtime table and the
  document index.
- **`CONTRIBUTING.md`** — a **Linters and pinned tooling** section (`make lint` / `fix` / `lint-md` /
  `format` / `lint-py`, why `.venv-lint` exists rather than a system `pip install`, the one-pin-per-tool
  table, why this is correctness and not tidiness, and the instruction to verify a SHA against its tag
  comment when bumping a pin), plus a **Documentation that must be updated with a change** table that
  names which docs a given change obliges you to touch and which files are generated.
- **`SECURITY.md`** — threat 4 expanded to the controls actually enforced (verified SHA pins,
  `persist-credentials: false`, expiring exceptions); **toolchain substitution added as threat 5**,
  since CI running a different scanner version than the reviewer is a real control failure; Dependabot
  now correctly listed as covering npm; and a paragraph on why an unverified pin comment is worse than
  no comment.
- **`SKILL-AUTHORING-STANDARD.md`** — the enforcement table had markdownlint as `npx markdownlint-cli2`
  _(advisory)_, which is doubly wrong: it is `make lint` and it is blocking. Added rows for the strict-YAML
  frontmatter gate and the index-agreement gate, and a note on one-pin-per-tool.
- **`SKILL_PIPELINE.md`** — W01–W13, and the one-pin-per-tool rule stated normatively.
- **`.github/pull_request_template.md`** — gate block collapsed to `make check` + `make lint`, a README
  index-row checkbox, and a new **tooling or CI change** section (verified SHA, no hardcoded tool
  version, both entrypoints pass).
- **`commands/cs-write-a-skill.md`** — eval bar corrected from 85% to the repository's 95% gate (85 is
  the tier floor, not the gate), `make lint` added, README-row obligation stated.
- **`agents/cs-skill-author.md`** — gate list completed with `audit-workflows.py` and `make check`/`make lint`.
- **`templates/skill-template/SKILL.md`** — the template's own `description` is now double-quoted, with
  a comment explaining that a description containing ': ' is a YAML mapping when left unquoted. The
  template previously modelled the exact defect that made 36 skills unloadable.

**Renamed from `devops-skills-curated` to `cloud-platform-skills`.** The old name had four
problems: `curated` is unfalsifiable self-praise that in the GitHub ecosystem signals _a list of
links_ rather than 43 executable, eval-gated skills; the adjective-last word order read as a sorting
key, not a name; `devops` undersold the scope, since only 15 of 43 skills live in `01-devops-core`
against 8 cloud, 9 security, 5 SRE, 4 platform, 1 FinOps and 1 productivity; and `devops-skills`
is a crowded namespace of roadmap and interview-prep repositories.

The slug changed in 105 places, but only 15 are authored — the rest are generated by `sync-all.py`
and `generate-docs.py` from `REPO`, so the rename was one constant plus a regeneration. The display
title dropped the same word for the same reason: **Cloud & Platform Engineering Skills**. Filler uses
of "curated" in the generated agent entrypoints were replaced with the claim that is actually
checkable ("eval-gated"), and the `LICENSE` copyright line was updated.

The plugin domain names lost their numeric prefixes too (`04-cloud-aws` → `cloud-aws`,
`08-finops-cloud-economics` → `finops-cloud-economics`, …). Those are what a user types in
`/plugin install`, and the prefix bought nothing: ordering comes from `DOMAIN_TITLES`, not from
the directory names.

**One breaking change for anyone who already installed it.** GitHub permanently redirects the old
repository URL, so `git clone` and existing remotes keep working. The Claude Code **marketplace name**
is the namespace in `plugin@marketplace`, so an existing install needs:

```text
/plugin marketplace remove devops-skills-curated
/plugin marketplace add mchittineni/cloud-platform-skills
/plugin install <domain>@cloud-platform-skills
```

Verified after the rename: zero occurrences of the old slug anywhere outside `node_modules`,
`package.json`/`package-lock.json` names agree and `npm ci` succeeds, and every gate and linter is
green.

**Five skills added, closing every verified reliability and security gap (38 -> 43).** The gap list
came from diffing this catalogue against `alirezarezvani/claude-skills` (24.6k stars, 346 distinct
skills, and the origin of `SKILL_PIPELINE.md`). Its topic list was mined; none of its content was
copied — its descriptions are keyword lists ("Triggers on 'chaos experiment', 'fault injection',
'gameday' ..."), 16 skill names are duplicated across two directory layouts, and its frontmatter
schema differs. All five were authored to this repository's standard and passed every gate.

| Skill | Domain | Closes |
| --- | --- | --- |
| `supply-chain-security-slsa-sigstore` | DevSecOps | keyless cosign signing, SLSA levels, provenance and SBOM attestation, verified admission |
| `policy-as-code-opa-kyverno` | DevSecOps | Kyverno/Rego/Conftest authoring, Pod Security Standards, policy unit tests, expiring exceptions |
| `ai-agent-security-llm-threats` | DevSecOps | indirect prompt injection, OWASP LLM Top 10, MITRE ATLAS, excessive agency, egress containment |
| `detection-engineering-threat-hunting` | DevSecOps | Sigma detection-as-code, ATT&CK coverage honesty, alert precision, Atomic Red Team validation |
| `chaos-engineering-resilience-testing` | SRE | steady-state hypotheses, blast-radius bounds, abort criteria, AWS FIS and Chaos Mesh, GameDays |

**A live defect surfaced first: two skills advertised provenance and never covered it.** Both
`cicd-pipeline-design` and `shift-left-security-sast-sca` listed artifact provenance, signing or
attestation as a **trigger**, and `cicd-pipeline-design` also named "artifact provenance and
attestation" in its routing **description** — while `cosign`, `sigstore`, `SLSA` and `attestation`
appeared **zero** times across both bodies. An agent asked to sign a release artifact loaded one of
them and found nothing. Compliance point 3 missed it because it compares description to body
loosely rather than trigger by trigger.

Worse, that skill's `must_cover` anchor was the single word `provenance`, which the coverage gate
satisfied from one incidental sentence ("provenance requires a clean build"). A one-word anchor can
certify a topic the skill does not teach. The description now claims only concurrency control, the
anchor was replaced with `concurrency`, and both skills route the trigger to the new supply-chain
skill.

**Two territory collisions the new skills created, resolved by dividing scope rather than tuning
prompts.** `policy-as-code-opa-kyverno` initially claimed "untagged or unencrypted S3 buckets blocked
in CI", which `enterprise-iac-governance-terragrunt` already owned — the overlap pushed the
Terragrunt skill's own trigger to `configuration-management-ansible` and its pass rate to 80%. The
boundary is now explicit: Terragrunt owns multi-account IaC gating, and this skill owns policy
authoring, admission enforcement and policy testing. Separately, an SBOM-attestation prompt routed
to `shift-left-security-sast-sca` (rank 2), fixed by tagging the new skill `sbom-attestation` — the
distinction between _generating_ an SBOM and _binding_ one to a digest is real, not keyword padding.
Eval loop: 4 failures across 2 iterations, ending at 43/43 and 100.0%.

**The AI-security skill needed the `agent-safety-justified` marker**, and finding out why was useful.
A skill that teaches detection of agent-directed harm must name the attack shapes — confirmation
bypass, redirection, concealment — so `compliance-check.py` correctly flagged it as a blocker. The
one-line marker downgrades it to a reviewed minor. Two details worth recording: the `JUSTIFIED`
regex is not `DOTALL`, so a multi-line marker silently fails to match; and a reference to
`scripts/compliance-check.py` was read as a path bundled with the skill, so it is now named without
a path.

**`README.md` index rows for the five new skills were generated, not hand-written**, by importing
`sync-all.py`'s own derivation — and the index-agreement gate added earlier is what caught their
absence in the first place, exactly as designed. Section counts moved to DevSecOps (9) and SRE (5),
and the nine plugin manifests plus `marketplace.json` picked up the new skill lists automatically.

Gaps identified and deliberately **not** filled: feature-flag progressive delivery (worth adding
later; `zero-downtime-release-strategies` covers traffic shifting but not flag lifecycle or stale-flag
debt), runbooks and operational readiness (belongs inside `incident-management-and-postmortem`, not a
separate skill), and SOC 2 / ISO 27001 evidence automation (pulls a cloud-engineering library toward
audit consulting). Confirmed _not_ gaps despite appearing in the source catalogue: dependency
auditing, secrets managers, SLO design, observability design, incident command, and cloud posture —
all already covered here at equal or greater depth.

### Notable decisions

- **Eval gate raised from 85% to 95%** across every call site — Makefile default, all four
  workflows, the pre-commit hook, the `run-evals.py` default, and the docs. Every skill currently
  scores 100%, so the higher bar has real headroom rather than being aspirational.
- **`MD013` (line length) is disabled deliberately, with the reasoning recorded in the config.**
  `must_cover` anchors are substring-matched against skill bodies, so a hard reflow can split an
  anchor across a newline and silently break the content-coverage gate: a lint rule must never be
  able to defeat a correctness gate. 98 authored prose lines currently exceed 120 characters;
  enabling the rule requires a dedicated reflow pass verified by `make check`, not a config flip.
  It is switched off rather than suppressed behind an unreachable limit, so the debt stays visible.
- **Prettier does not own markdown**, for the same reason; `.prettierignore` excludes `*.md` and
  every generated tree, including the JSON that `sync-all.py --check` byte-compares.

### Verified

- Agent-safety detection self-tested against a planted prompt-injection + exfiltration probe:
  **4/4 detected, 0 false positives** across all 43 skills.
- Audit self-check: every `uses:` in every workflow is accounted for — no step is silently skipped
  by the YAML-subset parser, and W12 correctly flagged two exceptions that became obsolete once
  `actions/upload-artifact` was SHA-pinned. Both were pruned.
- All skill bodies are under 200 lines (ceiling 500), keeping progressive disclosure intact.

### Known residuals

- Two eval cases are recorded as **documented residuals** (`known_residual` in the eval file):
  "scan the repo for committed secrets in CI" (`secrets-management-vault-kms`) and "a customer is
  asking for an SBOM" (`shift-left-security-sast-sca`). Both are genuine near-ties between sibling
  security skills under bag-of-words routing, left after 4 of the allowed 5 iterations rather than
  keyword-stuffing a description to win a single prompt. Each carries its justification in
  `evals.json`, is reported on every run, and is resolved in practice by the **Route elsewhere**
  cross-links in both bodies.

### Not verified (requires credentials, network, or an interactive session)

- LLM-graded with-skill vs baseline benchmarking (pipeline Phase 3b–3c: pass rate, ≥ +30% delta,
  variance < 20%) — needs a model runner. The offline gates are the documented pre-flight, not a
  substitute.
- `tessl skill review` scores — Tessl CLI unavailable; the deterministic 8-point check was run as
  the documented fallback.
- Phase 9 real-world verification: `/plugin marketplace add`, `/plugin install`, `/plugin reload`,
  live trigger tests, ClawHub publish, and Codex/Gemini/OpenClaw load checks. This includes the
  unprefixed plugin names — no install has been run against `cloud-aws`, `devops-core`, … Every
  offline gate in `make check` passes.
- No workflow has been executed on GitHub Actions — CI correctness is verified statically only.
- The 4 remaining tag-pinned actions need their digests resolved by a maintainer with network
  access before 2026-11-17 (`gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq .object.sha`).
  `gitleaks/gitleaks-action` is the only third-party one and should be pinned first.
- The trailing version comment on the `actions/upload-artifact` SHA pin reads `# v7.0.1`, which
  matches `actions/checkout`'s version rather than any published upload-artifact release. The
  digest is what GitHub resolves, so this is cosmetic — but the comment should be corrected when
  someone verifies the digest.
- No git operations were performed: this directory is not currently a git working tree, so no
  branch, commit, tag or PR was created.
