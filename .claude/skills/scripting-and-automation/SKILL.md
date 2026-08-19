---
name: scripting-and-automation
description: "Production Bash and Python automation: `set -euo pipefail` discipline, lockfile-guarded single execution, idempotent design, structured logging, trap-based cleanup, and CLI ergonomics. Use when writing, reviewing, or hardening an operational script, cron job, or internal CLI tool."
level: mid
tags: [bash, python, automation, scripting, cli, devops-core]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Production Scripting & Automation Standards

## When to Use This Skill

**Triggers — load this skill when:**

- An operational script must be safe to re-run and to fail loudly
- A cron/CI job needs locking, cleanup traps, or structured logging
- You are reviewing shell code for silent-failure and quoting defects

**Route elsewhere when:**

- Multi-node OS configuration -> `configuration-management-ansible`
- Declarative cloud resource provisioning -> `terraform-iac-modules`

## 1. Idempotent & Resilient Bash Scripting Template

```bash
#!/usr/bin/env bash
# Strict error handling: exit on error, unset variables, and pipeline failures
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME="$(basename "${0}")"
readonly LOG_FILE="/tmp/${SCRIPT_NAME}.log"

log() {
    local level="${1}"
    shift
    local msg="${*}"
    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "{\"timestamp\":\"${timestamp}\",\"level\":\"${level}\",\"message\":\"${msg}\"}" | tee -a "${LOG_FILE}"
}

cleanup() {
    local exit_code=$?
    log "INFO" "Cleaning up temporary resources (exit code: ${exit_code})..."
    rm -f /tmp/lock.$$ 2>/dev/null || true
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM

# Ensure single execution with lockfile
lock() {
    if ! mkdir /tmp/script.lock 2>/dev/null; then
        log "ERROR" "Another instance of ${SCRIPT_NAME} is already running."
        exit 1
    fi
}
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Always set `set -euo pipefail` at the start of any production Bash script.
- **Do**: Use Python for complex JSON parsing, API interactions, and matrix data structures rather than nesting deep `awk`/`sed`/`jq` chains.
- **Don't**: Never use `eval` with user-supplied parameters to avoid command injection vulnerabilities.
- **Don't**: Avoid parsing `ls` output; use globs or `find ... -print0 | while IFS= read -r -d '' file; do ... done`.

---

## 3. Single-Instance Enforcement with flock

A lockfile you create and delete yourself leaks on `SIGKILL` and blocks every later run. Use
kernel-held locks, which are released automatically when the process dies:

```bash
#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="/var/lock/$(basename "$0").lock"
exec 9>"${LOCK_FILE}"
if ! flock --nonblock 9; then
    echo "$(basename "$0") is already running; exiting." >&2
    exit 0            # exit 0: an overlapping cron tick is not a failure
fi

cleanup() { rm -f "${TMP_DIR:-}/staging" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
```

Or wrap the whole invocation from cron without touching the script:

```bash
*/5 * * * * /usr/bin/flock -n /var/lock/sync.lock /usr/local/bin/sync.sh
```

Use `flock --wait 60` when a delayed run is better than a skipped one, and `--nonblock` when a
skipped run is better than a queue of piled-up jobs.

---

## 4. Operational CLI Ergonomics

An operational script becomes a CLI the moment someone else runs it. The ergonomics that make it
safe under pressure:

```python
#!/usr/bin/env python3
import argparse, logging, sys

def main() -> int:
    p = argparse.ArgumentParser(description="Reconcile orphaned EBS volumes.")
    p.add_argument("--region", required=True)
    p.add_argument("--dry-run", action="store_true", default=True,
                   help="report only (default); pass --no-dry-run to act")
    p.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    p.add_argument("-v", "--verbose", action="count", default=0)
    args = p.parse_args()

    logging.basicConfig(
        level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbose, 2)],
        format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
        stream=sys.stderr,          # logs to stderr, data to stdout
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Rules: **dry-run is the default** for anything destructive; `--help` states the blast radius;
logs go to stderr so stdout stays pipeable; exit codes are meaningful (0 success, 1 failure,
2 usage error, and a distinct code for "nothing to do" if a caller must branch on it).
