# Mirascope CLI

A minimal, hackable CLI assistant built with [Mirascope](https://github.com/mirascope/mirascope).

## ⚠️ Important Warning

This CLI is a **sandbox environment without security measures or failsafes**. It executes:
- Arbitrary bash commands with system access
- Python code via tool execution
- File system operations (create/read/edit)

**Security implications:**
- No sandboxing or containerization
- No input validation or sanitization
- No permission checks
- Commands execute with your user privileges

**Use responsibly:**
- Never run against untrusted models or inputs
- Be cautious with file operations
- Understand that bash commands have full system access

---

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
- **Planning tool** (task breakdown)

## Available Tools

**File**: `file_create`, `file_read`, `file_edit`  
**Bash**: `execute_bash`  
**Planning**: `plan`

## Configuration

- **System prompt**: Edit `prompts/cli.md`
- **Model config**: Adjust in `mirascope_cli.py` (`model = llm.Model(...)`)

## Adding Tools

The CLI can create its own tools dynamically:

1. Use the `file_create` tool to create `src/tools/my_tool.py` with `@llm.tool` decorator
2. Import the tool in `mirascope_cli.py`
3. Add to `tools=[...]` list in `model.stream()`

### Example Tool Structure

```python
from mirascope import llm

@llm.tool
def my_new_tool(param: str) -> str:
    """Description of what this tool does."""
    # Tool implementation
    return f"Result for {param}"
```

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
