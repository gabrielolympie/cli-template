# Mirascope CLI

A minimal, hackable CLI assistant built with [Mirascope](https://github.com/mirascope/mirascope).

## Quick Start

```bash
git clone git@github.com-personal:gabrielolympie/cli-template.git
cd cli-template
pip install mirascope
python mirascope_cli.py
```

Edit `mirascope_cli.py` to set your LLM endpoint:

```python
os.environ['OPENAI_API_KEY'] = "sk-..."
os.environ['OPENAI_API_BASE'] = "http://localhost:5000/v1"
```

## Features

- **File operations** (create/read/edit)
- **Bash execution** (60s timeout)
- **Session persistence** (save/restore state)
- **Context compaction** (for long sessions)
- **Planning tool** (task breakdown)

## Available Tools

**File**: `file_create`, `file_read`, `file_edit`  
**Bash**: `execute_bash`  
**State**: `set_restart_state`, `get_restart_state`, `clear_restart_state`, `restart_cli`  
**Context**: `compact_state`, `get_compact_state`, `clear_compact_state`  
**Planning**: `plan`

## Configuration

- **System prompt**: Edit `prompts/cli.md`
- **Model config**: Adjust in `mirascope_cli.py` (`model = llm.Model(...)`)

## Adding Tools

1. Create `src/tools/my_tool.py` with `@llm.tool` decorator
2. Import in `mirascope_cli.py`
3. Add to `tools=[...]` list in `model.stream()`

## Project Structure

```
mirascope_cli.py        # Main entry point
prompts/
  cli.md               # System prompt
  plan.md              # Planning template
src/tools/             # Tool definitions
```

## License

MIT
