"""Skill manager module for Mirascope CLI.

This module provides a manager class for handling skill lifecycle operations,
including loading, tracking, and executing skills efficiently.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from .loader import (
    load_skill, 
    load_all_skills,
    generate_skill_inventory,
    generate_skill_usage_guide,
    generate_skill_writing_guide,
    parse_yaml_frontmatter
)


# Get the current working directory
PROJECT_ROOT = os.getcwd()
SKILLS_DIR = Path(PROJECT_ROOT) / ".claude" / "skills"
SKILL_CACHE_FILE = Path(PROJECT_ROOT) / ".claude" / "skill_cache.json"


class SkillManager:
    """Manager for all skill operations.
    
    Handles loading, caching, and efficient access to skills.
    Provides methods for querying skills, executing skill tasks,
    and managing skill lifecycle.
    """
    
    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize the skill manager.
        
        Args:
            skills_dir: Path to skills directory, defaults to .claude/skills/
        """
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._tool_map: Dict[str, List[str]] = {}  # tool_pattern -> [skill_names]
        self._cache: Optional[Dict] = None
        self._cache_valid = False
        
    def load_skills(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load all skills, using cache if available.
        
        Args:
            force_reload: Skip cache and reload from disk
            
        Returns:
            Dictionary of skill data
        """
        if not force_reload and self._cache_valid and self._cache:
            self._skills = self._cache.get("skills", {})
            self._tool_map = self._cache.get("tool_map", {})
            return self._skills
        
        # Clear existing data
        self._skills = {}
        self._tool_map = {}
        
        # Load skills from disk
        skills = load_all_skills()
        self._skills = skills
        
        # Build tool map for efficient lookup
        for name, skill in skills.items():
            allowed_tools = skill.get("allowed_tools", "")
            if allowed_tools and allowed_tools.startswith("Bash("):
                # Extract pattern like "playwright-cli:*" from "Bash(playwright-cli:*)"
                pattern = allowed_tools[5:-1]  # Remove "Bash(" and ")"
                if pattern not in self._tool_map:
                    self._tool_map[pattern] = []
                self._tool_map[pattern].append(name)
        
        # Cache the skills
        self._cache = {
            "skills": self._skills,
            "tool_map": self._tool_map,
            "loaded_at": str(Path.cwd()),
        }
        self._cache_valid = True
        
        return self._skills
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific skill by name.
        
        Args:
            name: Skill name
            
        Returns:
            Skill data or None if not found
        """
        if not self._skills:
            self.load_skills()
        return self._skills.get(name)
    
    def find_skills_for_tool(self, tool_pattern: str) -> List[str]:
        """Find skills that provide a specific tool pattern.
        
        Args:
            tool_pattern: Tool pattern to match (e.g., "playwright-cli:*")
            
        Returns:
            List of skill names that provide this tool
        """
        if not self._skills:
            self.load_skills()
        return self._tool_map.get(tool_pattern, [])
    
    def find_skills_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Find skills matching a keyword in name or description.
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            List of matching skill data
        """
        if not self._skills:
            self.load_skills()
        
        keyword_lower = keyword.lower()
        results = []
        
        for name, skill in self._skills.items():
            if (keyword_lower in name.lower() or 
                keyword_lower in skill.get("description", "").lower()):
                results.append(skill)
        
        return results
    
    def get_all_tool_patterns(self) -> List[str]:
        """Get all available tool patterns from skills.
        
        Returns:
            List of tool patterns
        """
        if not self._skills:
            self.load_skills()
        return list(self._tool_map.keys())
    
    def execute_skill(self, skill_name: str, task: str, context: str = "") -> str:
        """Execute a skill for a specific task.
        
        Args:
            skill_name: Name of the skill to execute
            task: Description of the task
            context: Additional context for the task
            
        Returns:
            Execution result
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found. Available skills: {', '.join(self._skills.keys())}"
        
        allowed_tools = skill.get("allowed_tools", "None")
        
        result = f"Executing '{task}' using {skill_name} skill.\n\n"
        result += f"Skill Description: {skill.get('description', 'N/A')}\n"
        result += f"Allowed Tools: {allowed_tools}\n"
        
        if context:
            result += f"\nContext: {context}\n"
        
        result += f"\nFull documentation is available in the skill references."
        
        return result
    
    def generate_prompt_context(self) -> str:
        """Generate skill context for the system prompt.
        
        Returns:
            Formatted skill context string
        """
        if not self._skills:
            self.load_skills()
        
        inventory = generate_skill_inventory(self._skills)
        usage = generate_skill_usage_guide(self._skills)
        
        return inventory + "\n\n" + usage
    
    def generate_skill_writer_guide(self) -> str:
        """Generate guide for skill writers.
        
        Returns:
            Complete guide for creating new skills
        """
        return generate_skill_writing_guide()
    
    def list_all_skills(self) -> str:
        """List all skills in a readable format.
        
        Returns:
            Formatted list of skills
        """
        if not self._skills:
            self.load_skills()
        
        if not self._skills:
            return "No skills loaded."
        
        output = "Available Skills:\n\n"
        for name, skill in self._skills.items():
            output += f"  {name}:\n"
            output += f"    Description: {skill.get('description', 'N/A')}\n"
            output += f"    Allowed Tools: {skill.get('allowed_tools', 'N/A')}\n"
            output += f"    References: {len(skill.get('references', {}))} docs\n"
            output += "\n"
        
        return output
    
    def get_skill_references(self, skill_name: str) -> Dict[str, str]:
        """Get all references for a skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Dictionary of reference name -> content
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return {}
        return skill.get("references", {})
    
    def get_reference_content(self, skill_name: str, reference_name: str) -> Optional[str]:
        """Get specific reference content.
        
        Args:
            skill_name: Name of the skill
            reference_name: Name of the reference
            
        Returns:
            Reference content or None if not found
        """
        references = self.get_skill_references(skill_name)
        return references.get(reference_name)
    
    def get_all_skill_names(self) -> List[str]:
        """Get list of all skill names.
        
        Returns:
            List of skill names
        """
        if not self._skills:
            self.load_skills()
        return list(self._skills.keys())
    
    def get_tool_map(self) -> Dict[str, List[str]]:
        """Get mapping of tool patterns to skills.
        
        Returns:
            Dictionary of tool_pattern -> [skill_names]
        """
        if not self._skills:
            self.load_skills()
        return self._tool_map.copy()
    
    def clear_cache(self) -> None:
        """Clear the skill cache."""
        self._cache = None
        self._cache_valid = False
        self._skills = {}
        self._tool_map = {}
    
    def save_cache(self, cache_file: Optional[Path] = None) -> None:
        """Save skill cache to file.
        
        Args:
            cache_file: Path to cache file, defaults to .claude/skill_cache.json
        """
        if not self._cache_valid or not self._cache:
            self.load_skills()
        
        cache_file = cache_file or SKILL_CACHE_FILE
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2)
    
    def load_cache(self, cache_file: Optional[Path] = None) -> bool:
        """Load skill cache from file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            True if cache was loaded successfully
        """
        cache_file = cache_file or SKILL_CACHE_FILE
        
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            
            self._skills = self._cache.get("skills", {})
            self._tool_map = self._cache.get("tool_map", {})
            self._cache_valid = True
            return True
        except (json.JSONDecodeError, IOError):
            self._cache_valid = False
            return False


def get_skill_manager() -> SkillManager:
    """Get or create the global skill manager instance.
    
    Returns:
        SkillManager instance
    """
    if not hasattr(get_skill_manager, "_instance"):
        get_skill_manager._instance = SkillManager()
    return get_skill_manager._instance


def get_skill_info(skill_name: str) -> str:
    """Get detailed information about a specific skill.
    
    This is a convenience wrapper for SkillManager.get_skill() that formats
    the output for tool usage.
    
    Args:
        skill_name: Name of the skill to look up
        
    Returns:
        Detailed skill information including description, allowed tools,
        and preview of available references
    """
    manager = get_skill_manager()
    skill = manager.get_skill(skill_name)
    
    if not skill:
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(manager.get_all_skill_names())}"
    
    output = f"## {skill_name}\n\n"
    output += f"**Description**: {skill.get('description', 'N/A')}\n\n"
    output += f"**Allowed Tools**: {skill.get('allowed_tools', 'N/A')}\n\n"
    
    body = skill.get('body', '')
    if body:
        output += "### Overview\n\n"
        output += body[:2000] + "\n\n"
        if len(body) > 2000:
            output += "*... (content truncated, use references for full details)*\n\n"
    
    references = skill.get('references', {})
    if references:
        output += "### Available References\n\n"
        for ref_name in references.keys():
            output += f"- {ref_name}\n"
    
    return output
