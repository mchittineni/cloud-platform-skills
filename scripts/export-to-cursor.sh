#!/usr/bin/env bash
# export-to-cursor.sh — compatibility wrapper.
#
# Generation now lives in scripts/sync-all.py, which regenerates every runtime target from
# skills/ (the single source of truth). This wrapper keeps the documented entrypoint working
# and exports only the Cursor + GitHub Copilot target(s).
#
# Prefer: python3 scripts/sync-all.py

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" = "--all" ]; then
    exec python3 "${SCRIPT_DIR}/sync-all.py"
fi
if [ "${1:-}" = "--domain" ]; then
    echo "note: per-domain export is no longer supported — skills are discovered individually" >&2
    echo "      by each runtime, so the whole library is generated at once." >&2
fi
exec python3 "${SCRIPT_DIR}/sync-all.py" --only cursor,copilot
