# Agent Memory

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

## Key Behaviors
- Always read AGENT.md at conversation start