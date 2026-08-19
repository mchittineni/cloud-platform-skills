# Progressive Disclosure Principles for Agent Skills

Progressive disclosure is an interaction design technique that delays advanced or rarely needed information until the user (or AI agent) specifically requests it.

## 1. Why Progressive Disclosure Matters for AI Agents

- **Context Window Economy**: AI models perform best when their active context is focused on the immediate task.
- **Signal-to-Noise Ratio**: Inundating an agent with 100 pages of unused documentation induces hallucination and instruction degradation.
- **Hierarchical Loading Model**:
  1. **Level 1 (Discovery)**: Only `name` and `description` frontmatter are injected into the agent system index.
  2. **Level 2 (Activation)**: When a trigger matches ("Use when..."), the agent reads `SKILL.md` (< 150 lines).
  3. **Level 3 (Deep Dive)**: If edge cases or complex schemas are needed, the agent reads specific files inside `references/` or executes tools in `scripts/`.

## 2. Directory Layout Standard

```text
skills/<category>/<skill-name>/
├── SKILL.md                 # Level 2: Core SOP, quick commands, decision tree
├── scripts/                 # Executable Python/Bash tools
└── references/              # Level 3: Deep architecture notes, RFCs, full schemas
    ├── architecture.md
    └── troubleshooting.md
```
