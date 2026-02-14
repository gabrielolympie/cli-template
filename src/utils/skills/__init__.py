"""Skill management module for Mirascope CLI.

This module provides skill loading, management, and execution capabilities.
Skills are self-contained packages in the .claude/skills/ directory that
extend the CLI's functionality.
"""

from .loader import (
    load_skill,
    load_all_skills,
    generate_skill_inventory,
    generate_skill_usage_guide,
    generate_skill_writing_guide,
    parse_yaml_frontmatter,
)

from .manager import (
    SkillManager,
    get_skill_manager,
)

__all__ = [
    "load_skill",
    "load_all_skills",
    "generate_skill_inventory",
    "generate_skill_usage_guide",
    "generate_skill_writing_guide",
    "parse_yaml_frontmatter",
    "SkillManager",
    "get_skill_manager",
]
