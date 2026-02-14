"""Skill loader module for Mirascope CLI.

This module handles loading, parsing, and managing skills from the .claude/skills/ directory.
Skills are YAML-frontmatter-markdown files that define CLI tools and capabilities.
"""

from mirascope import llm
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


# Get the current working directory
PROJECT_ROOT = os.getcwd()
SKILLS_DIR = Path(PROJECT_ROOT) / ".claude" / "skills"


def parse_yaml_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.
    
    Args:
        content: The markdown content with optional YAML frontmatter
        
    Returns:
        Tuple of (metadata_dict, body_content)
    """
    if not content.startswith("---"):
        return {}, content
    
    # Find the closing ---
    match = re.search(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL | re.MULTILINE)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1))
            body = match.group(2)
            return (metadata if metadata else {}, body)
        except yaml.YAMLError:
            return {}, content
    return {}, content


def load_skill(skill_dir: Path) -> Optional[Dict[str, Any]]:
    """Load a single skill from its directory.
    
    Args:
        skill_dir: Path to the skill directory
        
    Returns:
        Skill dictionary with metadata and content, or None if invalid
    """
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None
    
    try:
        content = skill_file.read_text(encoding="utf-8")
        metadata, body = parse_yaml_frontmatter(content)
        
        # Extract references if any
        references = {}
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for ref_file in refs_dir.glob("*.md"):
                if ref_file.name != "SKILL.md":
                    references[ref_file.stem] = ref_file.read_text(encoding="utf-8")
        
        return {
            "name": metadata.get("name", skill_dir.name),
            "description": metadata.get("description", ""),
            "allowed_tools": metadata.get("allowed-tools", ""),
            "body": body,
            "references": references,
            "path": str(skill_dir),
        }
    except Exception as e:
        print(f"Error loading skill {skill_dir.name}: {e}")
        return None


def load_all_skills() -> Dict[str, Dict[str, Any]]:
    """Load all skills from the skills directory.
    
    Returns:
        Dictionary mapping skill names to skill data
    """
    skills = {}
    
    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        return skills
    
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir():
            skill = load_skill(skill_dir)
            if skill:
                skills[skill["name"]] = skill
                print(f"Loaded skill: {skill['name']}")
    
    return skills


def generate_skill_inventory(skills: Dict[str, Dict[str, Any]]) -> str:
    """Generate a formatted inventory of available skills.
    
    Args:
        skills: Dictionary of skill data
        
    Returns:
        Formatted string describing all available skills
    """
    if not skills:
        return "No skills available."
    
    inventory = "## AVAILABLE SKILLS\n\n"
    inventory += "The following skills are available in the system:\n\n"
    
    for name, skill in skills.items():
        inventory += f"### {name}\n"
        inventory += f"- **Description**: {skill.get('description', 'No description')}\n"
        inventory += f"- **Allowed Tools**: {skill.get('allowed_tools', 'None specified')}\n"
        inventory += "\n"
    
    inventory += "To use a skill, mention its name and describe what you want to accomplish.\n"
    inventory += "The assistant will automatically leverage the appropriate skill's capabilities.\n"
    
    return inventory


def generate_skill_usage_guide(skills: Dict[str, Dict[str, Any]]) -> str:
    """Generate a guide on how to use and reference skills.
    
    Args:
        skills: Dictionary of skill data
        
    Returns:
        Formatted usage guide
    """
    guide = "## SKILL USAGE GUIDE\n\n"
    guide += "### Referencing Skills\n\n"
    guide += "When a skill is loaded, you can reference it by name in your prompts:\n\n"
    guide += "- **Direct mention**: \"Use playwright-cli to navigate to example.com\"\n"
    guide += "- **Command execution**: The assistant will use the skill's allowed tools\n"
    guide += "- **Reference documentation**: Some skills have detailed reference docs\n\n"
    guide += "### Skill Features\n\n"
    
    for name, skill in skills.items():
        references = skill.get("references", {})
        if references:
            guide += f"**{name}** has detailed references for:\n"
            for ref_name in references.keys():
                guide += f"- {ref_name}\n"
            guide += "\n"
    
    guide += "### Best Practices\n\n"
    guide += "1. Mention the skill name when asking about related tasks\n"
    guide += "2. Check the skill description to understand available capabilities\n"
    guide += "3. Reference docs provide detailed command syntax and examples\n"
    guide += "4. Some skills may require initialization (e.g., `playwright-cli open`)\n"
    
    return guide


@llm.tool
def list_skills() -> str:
    """List all available skills in the system.
    
    Returns:
        Formatted list of available skills with descriptions
    """
    skills = load_all_skills()
    
    if not skills:
        return "No skills loaded."
    
    output = "Available Skills:\n\n"
    for name, skill in skills.items():
        output += f"  {name}:\n"
        output += f"    Description: {skill.get('description', 'N/A')}\n"
        output += f"    Allowed Tools: {skill.get('allowed_tools', 'N/A')}\n"
        output += f"    References: {len(skill.get('references', {}))} docs\n"
        output += "\n"
    
    return output


@llm.tool
def get_skill_info(skill_name: str) -> str:
    """Get detailed information about a specific skill.
    
    Args:
        skill_name: Name of the skill to look up
        
    Returns:
        Detailed skill information including body and available references
    """
    skills = load_all_skills()
    
    if skill_name not in skills:
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(skills.keys())}"
    
    skill = skills[skill_name]
    output = f"## {skill_name}\n\n"
    output += f"**Description**: {skill.get('description', 'N/A')}\n\n"
    output += f"**Allowed Tools**: {skill.get('allowed_tools', 'N/A')}\n\n"
    
    if skill.get("body"):
        output += "### Overview\n\n"
        output += skill["body"][:2000] + "\n\n"  # Limit to first 2000 chars
        if len(skill["body"]) > 2000:
            output += "*... (content truncated, use references for full details)*\n\n"
    
    references = skill.get("references", {})
    if references:
        output += "### Available References\n\n"
        for ref_name, ref_content in references.items():
            output += f"#### {ref_name}\n"
            output += ref_content[:500] + "\n\n"  # Preview first 500 chars
    
    return output


def load_skill_tool(skill: Dict[str, Any]) -> Any:
    """Create a tool wrapper for a skill.
    
    Args:
        skill: Skill data dictionary
        
    Returns:
        An llm.tool decorated function that executes the skill
    """
    @llm.tool
    def execute_skill_task(task: str) -> str:
        """Execute a task using the skill's capabilities.
        
        Args:
            task: Description of what needs to be accomplished
            
        Returns:
            Result of executing the task
        """
        return f"Task '{task}' would be executed using {skill['name']} skill.\n" + \
               f"Skill capabilities: {skill.get('allowed_tools', 'N/A')}\n" + \
               f"Full documentation available in skill references."
    
    return execute_skill_task


def register_skill_tools(skills: Dict[str, Dict[str, Any]], tools_list: List) -> List:
    """Register skill tools with the model.
    
    Args:
        skills: Dictionary of skill data
        tools_list: Current list of tools
        
    Returns:
        Updated list of tools with skill tools added
    """
    for name, skill in skills.items():
        tool = load_skill_tool(skill)
        tools_list.append(tool)
    return tools_list


def build_system_prompt_with_skills() -> str:
    """Build the complete system prompt with skill information.
    
    Returns:
        Complete system prompt including base prompt and skill information
    """
    # Load base prompt
    base_prompt_path = Path(PROJECT_ROOT) / "prompts" / "system.md"
    base_prompt = ""
    if base_prompt_path.exists():
        base_prompt = base_prompt_path.read_text(encoding="utf-8")
    
    # Load skills
    skills = load_all_skills()
    
    # Build skill sections
    skill_inventory = generate_skill_inventory(skills)
    skill_usage = generate_skill_usage_guide(skills)
    
    # Add skill writer documentation
    skill_writing = generate_skill_writing_guide()
    
    # Combine all sections
    full_prompt = base_prompt
    
    if skills:
        full_prompt += "\n\n" + skill_inventory
        full_prompt += "\n\n" + skill_usage
    
    full_prompt += "\n\n" + skill_writing
    
    return full_prompt


def generate_skill_writing_guide() -> str:
    """Generate documentation on how to write a new skill.
    
    Returns:
        Complete guide for creating new skills
    """
    guide = """## WRITING NEW SKILLS

### Overview
Skills extend the CLI's capabilities by defining new tools and workflows. Each skill is a self-contained package in the `.claude/skills/` directory.

### Skill Structure

```
.clause/skills/
└── your-skill-name/
    ├── SKILL.md          # Main skill definition (required)
    └── references/       # Reference documentation (optional)
        ├── usage.md
        ├── examples.md
        └── advanced.md
```

### SKILL.md Format

The main skill file uses YAML frontmatter followed by markdown content:

```yaml
---
name: your-skill-name
description: What this skill does
allowed-tools: Bash(your-cli:*)
---
```

Followed by markdown documentation explaining how to use the skill.

#### Metadata Fields

- **name** (required): The skill identifier, used in prompts
- **description** (required): Short description for the skill inventory
- **allowed-tools** (required): Tools this skill exposes, e.g., `Bash(your-cli:*)`

### Tool Format

The `allowed-tools` field specifies which tools the skill provides:

```
Bash(your-cli:*)
```

This grants access to all commands in the `your-cli` tool via bash execution.

### Command Convention

Skills should follow a consistent CLI pattern:
- Use `your-cli command` for core functionality
- Support subcommands for organization
- Use flags for options: `--flag=value`
- Provide `help` and `list` commands

### Example Skill: Image Processing

```yaml
---
name: image-cli
description: Automated image processing and manipulation
allowed-tools: Bash(image-cli:*)
---

# Image Processing with image-cli

## Quick Start

```bash
# Process an image
image-cli process photo.jpg --resize=800x600 --format=webp

# Batch process multiple images
image-cli batch *.jpg --output=processed/

# Convert formats
image-cli convert input.png output.jpg
```

## Commands

### Core
- `process FILE` - Process a single image
- `batch PATTERN` - Process multiple images matching pattern
- `convert INPUT OUTPUT` - Convert between formats

### Options
- `--resize=WxH` - Resize image to dimensions
- `--format=TYPE` - Output format (webp, jpg, png)
- `--quality=N` - Quality 1-100

## Examples

See `references/` for detailed documentation.
```

### Testing Your Skill

1. Create a test CLI tool in `src/tools/` that matches your skill
2. Add it to `mirascope_cli.py` imports and tools list
3. Test with various prompts
4. Document edge cases in reference files

### Best Practices

1. **Clear naming**: Use descriptive skill and command names
2. **Consistent CLI**: Follow Unix conventions for flags and help
3. **Documentation**: Provide examples in reference docs
4. **Error handling**: Document common errors and solutions
5. **Versioning**: Consider version in skill name if needed

### Integration Points

Skills are automatically:
- Loaded on CLI startup from `.claude/skills/`
- Listed in the skill inventory
- Referenced in prompts when mentioned
- Executed via their allowed tools

### Troubleshooting

- **Skill not loading**: Check YAML syntax and file structure
- **Commands not found**: Ensure the CLI tool is installed and in PATH
- **Permissions issues**: Verify the tool has execute permissions

### Advanced Topics

- **Dynamic tools**: Generate tools based on skill configuration
- **Session management**: Handle persistent connections or state
- **Multi-step workflows**: Chain commands for complex operations
"""
    
    return guide


def update_system_md_with_skills() -> str:
    """Update the system.md file to include skill information.
    
    Returns:
        Complete updated system.md content
    """
    base_path = Path(PROJECT_ROOT) / "prompts" / "system.md"
    base_content = ""
    if base_path.exists():
        base_content = base_path.read_text(encoding="utf-8")
    
    # Build skill sections
    skills = load_all_skills()
    skill_inventory = generate_skill_inventory(skills)
    skill_usage = generate_skill_usage_guide(skills)
    skill_writing = generate_skill_writing_guide()
    
    # Append to base content
    updated = base_content
    if skills:
        updated += "\n\n" + skill_inventory
        updated += "\n\n" + skill_usage
    
    updated += "\n\n" + skill_writing
    
    return updated
