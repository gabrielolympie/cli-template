# Agent Memory

This file stores important information that should be kept in state across conversations and when the project context changes.

## Purpose

This file serves as persistent memory for the agent. It stores:
- Project-specific context that should persist across sessions
- Team guidelines and preferences
- Project structure updates
- System configuration changes
- Any important information that shouldn't be lost between conversations

## Contents

*Information will be added here over time as the agent learns and remembers important details.*

### System Updates

**2025-02-11**: Added `/compact` command for conversation history management
- Type `/compact` to summarize conversation, clear history, and preserve context
- Automatically generates an LLM summary of all conversation history
- Resets messages with system prompt plus summary as first user message
- Allows coming back to initial state with key decisions and progress preserved
- Reduces token usage while maintaining important context
- Summary includes: key facts, user preferences, progress, important context, pending actions

**2025-02-11**: Added `/reset` command for conversation history management
- Type `/reset` to clear all conversation messages except the initial system prompt
- Restores the assistant to its initialization state while preserving skill context
- Useful for starting fresh conversations or troubleshooting context issues

**2024-02-11**: Added clarify tool for asking clarifying questions
- Added `clarify(question)` tool as a dedicated capability
- Updated system prompt to emphasize asking questions before important decisions
- CLI loop handles clarify tool by prompting user for input via multiline_input
- Tool execution pauses until user provides response

**2024-02-11**: Added skill management system
- Skill loading from `.claude/skills/` directory
- Automatic skill inventory in system prompt
- Skill management tools (list_skills, get_skill_info, skill_search)
- Documentation skill with writing guides

### Recent Updates

*Add new entries at the top for the most recent information.*

### Project Notes

*Add any project-specific information here.*