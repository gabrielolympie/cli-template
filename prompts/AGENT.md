# Agent Memory

Persistent context that survives across conversations. Read on startup, update as you learn.

## Configuration Updates
- **2024-02-14**: Made `context_limit_percentage` configurable via `config.yaml` (default: 0.8)
- Changed from hardcoded value in `mirascope_cli.py` to configurable parameter

## Conventions

Persistent context that survives across conversations. Read on startup, update as you learn.

## Conventions
- New entries go at the top of each section
- Keep entries concise — one line per fact when possible
- Remove outdated info proactively

## Project Structure
```
mirascope_cli.py        # Entry point
prompts/
  SYSTEM.md             # CLI/tool reference
  PERSONA.md            # Agent personality
  PLAN.md               # Planning template
  AGENT.md              # This file (persistent context)
src/tools/              # Tool definitions
src/skills/             # Skill management system
.claude/skills/         # User-created skills
```