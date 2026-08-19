# scripts/

Python 3.10+ CLI tools, **standard library only** — no pip installs, no network calls, no LLM
calls. `scripts/compliance-check.py` fails a skill whose bundled scripts import anything outside
the standard library.

Conventions:

- `--help` states the blast radius; destructive operations default to `--dry-run`.
- Logs to stderr, data to stdout, so output stays pipeable.
- Meaningful exit codes: `0` success, `1` findings/failure, `2` usage error.
- Embed a small sample so the tool can be demonstrated with no external input.
