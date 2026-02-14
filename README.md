# Mirascope CLI

A minimal, hackable CLI assistant built with [Mirascope](https://github.com/mirascope/mirascope).

---

## ⚠️ Warning: Sandbox Environment

This CLI executes arbitrary commands with full system access. Use responsibly.

---

## Quick Start

```bash
git clone git@github.com-personal:gabrielolympie/cli-template.git
cd cli-template
./install.sh
python mirascope_cli.py
```

Edit `mirascope_cli.py` to configure your LLM:

```python
os.environ['OPENAI_API_KEY'] = "sk-..."
os.environ['OPENAI_API_BASE'] = "http://localhost:5000/v1"
```

---

## Capabilities

| Feature | Description |
|---------|-------------|
| **File Operations** | Create, read, edit files with line-level precision |
| **Bash Execution** | Execute commands with 60s timeout |
| **Planning** | Break down complex tasks into structured step-by-step plans |
| **Web Browsing** | Browse and extract structured content from webpages |
| **Internet Search** | Fetch and parse webpage content |
| **Browser Automation** | Playwright-based web interaction (via skills) |
| **Skills System** | Extend capabilities via modular YAML-configured skills |
| **Screenshot Capture** | Cross-platform screenshot capture with image resizing |
| **Conversation Management** | Auto-compaction when approaching context limits |
| **Token Estimation** | Accurate token counting for context management |
| **Image Support** | Screenshot display and image handling |
| **Multiline Input** | Support for multi-line user input with Alt+Enter |

## Advanced Features

### Context Management

The CLI automatically manages conversation length with configurable auto-compaction:

```yaml
# config.yaml
context_limit_percentage: 0.8  # 80% of context window before auto-compaction
```

- **Auto-compaction**: Conversations are automatically summarized when reaching the configured limit
- **Token estimation**: Accurate counting using tiktoken encoding
- **Context window**: 262,144 tokens (configurable via `llm.context_size`)

### Skill System

Skills are self-contained extensions in `.claude/skills/` with YAML configuration:

```yaml
---
name: skill-name
description: What it does
allowed-tools: Bash(cli:*)
---
```

**Available Skills:**
- `playwright-cli` - Browser automation (disabled by default)
- `skill-doc` - System documentation and skill writing guide
- `tool-dev` - Complete guide for creating and managing tools

### Special Commands

- `/quit`, `/exit`, `/q` - Exit the CLI
- `/reset` - Clear conversation history and restart
- `/compact` - Manually summarize and compact conversation

---

## Configuration

### LLM Providers

The CLI supports multiple LLM providers out of the box:

```yaml
# Native Mirascope providers
provider: "anthropic"     # uses ANTHROPIC_API_KEY
provider: "openai"        # uses OPENAI_API_KEY
provider: "google"        # uses GOOGLE_API_KEY
provider: "together"      # uses TOGETHER_API_KEY
provider: "ollama"        # uses OLLAMA_BASE_URL
provider: "mlx"           # no API key needed

# OpenAI-compatible providers
provider: "mistral"       # Mistral AI (OpenAI-compatible)
provider: "vllm"          # vLLM local server
provider: "zai"           # Z.AI GLM models
```

### Tool Enable/Disable

Individual tools can be enabled or disabled in `config.yaml`:

```yaml
tools:
  file_create: true
  file_read: true
  file_edit: true
  execute_bash: true
  screenshot: true
  plan: true
  browse_internet: true
  clarify: true
  summarize_conversation: true
```

### Skill Enable/Disable

Skills can be individually enabled or disabled:

```yaml
skills:
  skill-doc: true
  playwright-cli: false
```

---

## Key Files

```
mirascope_cli.py        # Main entry point
prompts/
  SYSTEM.md             # System prompt and workflow
  PERSONA.md            # Agent personality
  PLAN.md               # Planning template
  AGENT.md              # Persistent context
src/tools/              # Tool definitions
src/utils/              # Utility functions
.claude/skills/         # User-created skills
config.yaml             # Configuration
requirements.txt        # Dependencies
```

---

## Development

### Creating New Tools

1. Create a Python file in `src/tools/`
2. Define a tool using Mirascope's `@llm.tool` decorator
3. Add to `config.yaml` under `tools` section
4. Import and register in `mirascope_cli.py`

### Creating New Skills

1. Create a directory in `.claude/skills/`
2. Add `SKILL.md` with YAML frontmatter
3. Document usage and examples
4. (Optional) Add `references/` for detailed documentation

---

## License

MIT
## License

MIT
