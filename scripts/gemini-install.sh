#!/usr/bin/env bash
# gemini-install.sh — install the skill library for Gemini CLI / Google Antigravity.
#
# Regenerates .agents/skills/ from skills/ (the source of truth), then links or copies it into
# the user's global configuration so `activate_skill(name="<skill-name>")` can find each skill.
#
# Usage:
#   bash scripts/gemini-install.sh              # workspace only (.agents/skills)
#   bash scripts/gemini-install.sh --global     # also install to ~/.gemini/skills
#   bash scripts/gemini-install.sh --global --link   # symlink instead of copy (tracks edits)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_SKILLS="${ROOT_DIR}/.agents/skills"
GLOBAL_SKILLS="${HOME}/.gemini/skills"

DO_GLOBAL=0
USE_LINK=0
for arg in "$@"; do
    case "${arg}" in
        --global) DO_GLOBAL=1 ;;
        --link)   USE_LINK=1 ;;
        -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "unknown option: ${arg}" >&2; exit 2 ;;
    esac
done

echo "==> Regenerating .agents/skills from skills/"
python3 "${SCRIPT_DIR}/sync-all.py" --only agents

COUNT="$(find "${WORKSPACE_SKILLS}" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
echo "==> ${COUNT} skills available at ${WORKSPACE_SKILLS}"
echo "    Project rules: .agents/rules/GEMINI.md and .agents/rules/AGENTS.md"

if [ "${DO_GLOBAL}" -eq 1 ]; then
    mkdir -p "${GLOBAL_SKILLS}"
    for skill_dir in "${WORKSPACE_SKILLS}"/*/; do
        name="$(basename "${skill_dir}")"
        target="${GLOBAL_SKILLS}/${name}"
        rm -rf "${target}"
        if [ "${USE_LINK}" -eq 1 ]; then
            ln -s "${skill_dir%/}" "${target}"
        else
            cp -R "${skill_dir%/}" "${target}"
        fi
    done
    echo "==> Installed ${COUNT} skills to ${GLOBAL_SKILLS} ($([ "${USE_LINK}" -eq 1 ] && echo symlinked || echo copied))"
fi

echo "==> Verify inside Gemini CLI / Antigravity:"
echo "    activate_skill(name=\"sli-slo-error-budget-design\")"
